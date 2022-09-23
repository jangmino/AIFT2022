import exchange_calendars as xcals
import pandas as pd

class TimeManager:

  @staticmethod
  def get_now():
    '''
    현재 시간 (서울시)
    '''
    return pd.Timestamp.now(tz='Asia/Seoul')

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
    if self.fast_debug: return pd.Timestamp('2021-09-23 09:00:00', tz='Asia/Seoul')
    if not self.is_today_open():
      raise '휴장일입니다.'
    return self.__calendar.schedule.loc[pd.to_datetime(self.__date), 'open'].tz_convert(self.__calendar.tz)

  def when_to_close(self):
    '''
    장 닫히는 시간 (서울시)
    '''
    if self.fast_debug: return pd.Timestamp('2021-09-23 15:30:00', tz='Asia/Seoul')
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

if __name__ == '__main__':
  # TODO: 장중에 확인할 것
  tm = TimeManager(fast_debug=True)
  print(tm.is_today_open())
  print(tm.is_now_open())
  print(tm.when_to_open())
  print(tm.when_to_close())
  print(tm.less_than_minutes_before_open(30))