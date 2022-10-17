import exchange_calendars as xcals
import pandas as pd

class TimeManager:
  # 디버그 용도로 사용할 날짜 지정: 이유 (VS에서 디버깅시 exchange_calendars 초기화에서 너무 많은 시간이 소요되기에 편의성 목적으로 추가)
  start_dt_for_debug = pd.Timestamp('2022-10-17 09:00:00', tz='Asia/Seoul')
  end_dt_for_debug = pd.Timestamp('2022-10-17 15:30:00', tz='Asia/Seoul')

  @staticmethod
  def get_now():
    '''
    현재 시간 (서울시)
    '''
    return pd.Timestamp.now(tz='Asia/Seoul')

  @staticmethod
  def ts_floor_time(ts:pd.Timestamp, freq='T'):
    '''
    시간 내림
    '''
    return ts.floor(freq)

  @staticmethod
  def ts_ceil_time(ts:pd.Timestamp, freq='T'):
    '''
    시간 올림
    '''
    return ts.ceil(freq)

  @staticmethod
  def ts_min_shift(ts:pd.Timestamp, minutes=1, floor=False):
    '''
    ts에서 minutes 분 이동(+ 미래, - 과거)
    '''
    ret = ts + pd.Timedelta(minutes=minutes)
    return TimeManager.ts_floor_time(ret, freq='T') if floor else ret

  @staticmethod
  def ts_day_shift(ts:pd.Timestamp, days=1, floor=False):
    '''
    ts에서 day 일 이동(+ 미래, - 과거)
    '''
    ret = ts + pd.Timedelta(days=days)
    return TimeManager.ts_floor_time(ret, freq='D') if floor else ret

  @staticmethod
  def ts_to_str(ts:pd.Timestamp, format='%Y%m%d%H%M00'):
    '''
    시간을 문자열로 변환
    '''
    return ts.strftime(format)

  @staticmethod
  def str_to_ts(str, format='%Y%m%d%H%M00'):
    '''
    문자열을 시간으로 변환
    '''
    return pd.Timestamp(str, tz='Asia/Seoul')

  @staticmethod
  def hhmmss_to_ts(hhmmss:str):
    '''
    hhmmss 문자열을 시간으로 변환
    '''
    return pd.Timestamp(TimeManager.get_now().strftime('%Y%m%d') + hhmmss, tz='Asia/Seoul')

  def __init__(self, market='XKRX', date=None, fast_debug=False):
    self.fast_debug=fast_debug
    if fast_debug:
      self.__calendar = False
    else:
      self.__calendar = xcals.get_calendar('XKRX')
    self.__date = pd.Timestamp.today().date() if date==None else date
    self.ts_dic = {}

  def is_today_open(self, date=None):
    '''
    오늘 장 열렸는지 (열리는지)
    '''
    if self.fast_debug: return True
    return self.__calendar.is_session(self.__date)

  def is_now_open(self):
    '''
    현재 장 열렸는지
    '''
    if self.fast_debug: return True
    return self.__calendar.is_open_on_minute(pd.Timestamp.now(tz=self.__calendar.tz))

  def less_than_minutes_before_open(self, minutes=30):
    '''
    장 열리는 시간 몇분 미만 남았는지
    '''
    if self.fast_debug: return True
    return self.when_to_open() - pd.Timedelta(minutes=minutes) < self.get_now()

  def when_to_open(self):
    '''
    장 열리는 시간 (서울시)
    '''
    if self.fast_debug: return TimeManager.start_dt_for_debug
    if not self.is_today_open():
      raise '휴장일입니다.'
    return self.__calendar.schedule.loc[pd.to_datetime(self.__date), 'open'].tz_convert(self.__calendar.tz)

  def when_to_close(self):
    '''
    장 닫히는 시간 (서울시)
    '''
    if self.fast_debug: return TimeManager.end_dt_for_debug
    if not self.is_today_open():
      raise '휴장일입니다.'    
    return self.__calendar.schedule.loc[pd.to_datetime(self.__date), 'close'].tz_convert(self.__calendar.tz)

  def set_timestamp(self, tag):
    '''
    진입 시점 기록
    '''
    self.ts_dic[tag] = self.get_now()

  def get_timestamp(self, tag):
    '''
    진입 시점 조회
    '''
    return self.ts_dic[tag]

  def sprintf_timestamp(self, tag, format='%Y%m%d%H%M00'):
    '''
    진입 시점 출력 (문자열)
    '''
    return self.ts_dic[tag].strftime(format)

  def set_ts_pivot(self, ts):
    """
    피봇 시간 설정: 분 단위로 floor 하여 저장함
    """
    self.ts_dic['PIVOT'] = TimeManager.ts_floor_time(ts, freq='T')

  def get_ts_pivot(self):
    """
    피봇 설정되어 있지 않으면 None
    """
    if 'PIVOT' not in self.ts_dic:
      return None
    return self.ts_dic['PIVOT']
       
if __name__ == '__main__':
  # TODO: 장중에 확인할 것
  tm = TimeManager(fast_debug=True)
  print(tm.is_today_open())
  print(tm.is_now_open())
  print(tm.when_to_open())
  print(tm.when_to_close())
  print(tm.less_than_minutes_before_open(30))