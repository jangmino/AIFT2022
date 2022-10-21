from __future__ import annotations
from abc import *
from numbers import Real
from realtime_kiwoom.rt_kiwoom import *
import pandas as pd
import time
from enum import IntEnum
from miscs.time_manager import TimeManager, ToggledMinutesChecker
from miscs.config_manager import ConfigManager
from realtime_kiwoom.data_provider import *
from PyQt5.QtCore import *
from queue import Queue
from config.log_class import *
from realtime_kiwoom.kiwoom_type import *
from realtime_kiwoom.action import ActionManager
from grpc_python.request import RequestBuilder


class MarketState(IntEnum):
  NOT_OPERATIONAL = 0     # 비영업일
  BEFORE_OPEN = 1             # 영업일: 장 시작 전
  OPEN = 2   # 영업일: 개장
  AFTER_SIMULTANEOUS_QUOTE = 3    # 동시호가 시작 (15시 20분 이후)
  AFTER_CLOSE = 4                 # 15시 30분 이후
  AFTER_CLOSE_COMPLETELY = 5      # 16시 00분 이후

class LaunchedTimingState(IntEnum):
  LAUNCHED_BEFORE_OPEN = 0   # 장전 론칭  (정상)
  LAUNCHED_AFTER_OPEN = 1    # 장중 론칭  (비정상)


class RecoveryState(IntEnum):
  STANBY_TO_RECOVER = 0  # 복구 대기
  START_WARMUP_RT_EXECUTION = 1 # 실시간 주식 체결 요청 (00분 xx초)
  END_WARMUP_RT_EXECUTION = 2 # 실시간 주식 체결 싱크된 수신 단계 시작 (01분 00초)
  START_WARMUP_TR_MINUTE_DATA = 3 # 오늘 분봉 데이터 요청 (01분 10초)
  END_WARMUP_TR_MINUTE_DATA = 4 # 오늘 분봉 데이터 수신 완료 (01분 20초)
  RECOVERED = 5 # 복구 완료 (02분부터 정상 루프 시작)

# class MarketStateCallBackManager():
#   def __init__(self, agent: RTAgent = None):
#     self.__agent = agent
#     self.__after_state_entered = {
#       MarketState.OPEN: None,
#       MarketState.AFTER_CLOSE: None,
#     }
#     pass

class RecoveryManager():
  def __init__(self, agent: RTAgent = None):
    self.__agent = agent
    self.state = RecoveryState.STANBY_TO_RECOVER
    self.requests_to_timer_callback = []
    self.__today_minute_data = {}
    self.__ts_pivot = None

    self.__when_state_entered = {
      RecoveryState.STANBY_TO_RECOVER: None,
      RecoveryState.START_WARMUP_RT_EXECUTION: None,
      RecoveryState.END_WARMUP_RT_EXECUTION: None,
      RecoveryState.START_WARMUP_TR_MINUTE_DATA: self.__retrieve_today_minute_data,
      RecoveryState.END_WARMUP_TR_MINUTE_DATA: self.__insert_today_minute_data_to_db,
      RecoveryState.RECOVERED: self.__finalize_recovery,
    }

    self.__after_state_entered = {
      RecoveryState.START_WARMUP_RT_EXECUTION: {
      'ts_tag':RecoveryState.START_WARMUP_RT_EXECUTION, 
      'after_seconds': lambda: self.__seconds_to_finalize(RecoveryState.START_WARMUP_RT_EXECUTION),
      'func': []
      },
      RecoveryState.END_WARMUP_RT_EXECUTION: {
      'ts_tag':RecoveryState.END_WARMUP_RT_EXECUTION, 
      'after_seconds': lambda: 10,
      'func': []
      },
      RecoveryState.START_WARMUP_TR_MINUTE_DATA: {
      'ts_tag':RecoveryState.START_WARMUP_TR_MINUTE_DATA, 
      'after_seconds': lambda: 10, 
      'func': []
      },
      RecoveryState.END_WARMUP_TR_MINUTE_DATA: {
      'ts_tag':RecoveryState.END_WARMUP_TR_MINUTE_DATA, 
      'after_seconds': lambda: self.__seconds_to_finalize(RecoveryState.END_WARMUP_TR_MINUTE_DATA),
      'func': []
      },
      RecoveryState.RECOVERED: {
      'ts_tag':RecoveryState.RECOVERED, 
      'after_seconds': lambda: 0,
      'func': []
      }
    }

  def get_time_manager(self):
    return self.__agent.time_manager

  def set_state(self, new_state):
    if self.state != new_state:
      self.__agent.time_manager.set_timestamp(RecoveryState(new_state))
      self.__agent.get_logger().info(f"RecoveryManager state changed from {str(self.state)} into {str(new_state)}")
      self.__agent.get_logger().info(self.__agent.time_manager.ts_dic)
      self.state = new_state
      if self.__when_state_entered[new_state]:
        self.__when_state_entered[new_state]()
      self.requests_to_timer_callback.append(self.__after_state_entered[new_state])

  def move_next_state(self):
    """
    다음 상태로 이동
    """
    if self.state < RecoveryState.RECOVERED:
      self.set_state(RecoveryState(self.state + 1))

  def __retrieve_today_minute_data(self):
    for code in map(lambda x: x[0], self.__agent.config_manager.retrieve_candidate_ETFs()):
      raw_df = self.__agent.get_today_etf_minute_data(code)
      self.__today_minute_data[code] = raw_df
      raw_df.to_csv(f"today_{code}_minute.csv", index=False)

  def __insert_today_minute_data_to_db(self):
    self.get_time_manager().set_ts_pivot(self.get_time_manager().get_timestamp(RecoveryState.END_WARMUP_TR_MINUTE_DATA))
    self.__agent.get_logger().info(f"Recovery Pivot TS (floored to the minute) {self.get_time_manager().get_ts_pivot()=}")
    for code, df in self.__today_minute_data.items():
      self.__agent.minute_data_manager.today_minute_provider.insert_raw_dataframe_data(df, code, ts_end=self.get_time_manager().get_ts_pivot())
    self.__agent.minute_data_manager.set_static_today_minute_data()
    self.__agent.minute_data_manager.finalize_pre_pivot_data()
    # self.__agent.combined_minute_data.hhmmssdic['static_minute_end'] = TimeManager.ts_to_str(self.get_time_manager().get_ts_pivot(), format="%H%M%S")

  def get_effective_real_minutes_str(self):
    """
    dt = YmdHM00 형식의 문자열
    A): 어제까지 수신한 TR 분봉 데이터
    B): 금일 수신한 TR 분봉 데이터는 [Ymd090000, dt) 까지
    C): A + B 
    D): 리얼 데이터로 만든 분봉은 [dt, ) 전부

    최종 (매분): C + D
    """
    return self.get_time_manager().sprintf_timestamp(RecoveryState.END_WARMUP_TR_MINUTE_DATA)  

  def __finalize_recovery(self):
    self.__agent.get_logger().info(f"Recover is done!!!")
    
  def __seconds_to_finalize(self, state):
    return 60 - self.__agent.time_manager.get_timestamp(RecoveryState(state)).second

  def dispatch_request(self):
    if len(self.requests_to_timer_callback) > 0:
      request = self.requests_to_timer_callback[0]
      target_ts = self.__agent.time_manager.get_timestamp(request['ts_tag']) + pd.Timedelta(seconds=request['after_seconds']())
      current_ts = self.__agent.time_manager.get_now()
      if target_ts <= current_ts:
        self.__agent.get_logger().info(f"RecoveryManager (dispatch_request) state {str(RecoveryState(self.state))}: {target_ts} ==> {current_ts}")
        self.requests_to_timer_callback.pop(0)
        for func in request['func']:
          func()
        self.move_next_state()
        return True
    return False

class CallBackBase(metaclass=ABCMeta):
  def __init__(self, name, agent):
    self.name = name
    self.agent = agent

  @abstractmethod
  def apply(self, data):
    pass

class CallBackConnect(CallBackBase):
  def __init__(self, agent):
    super().__init__("connect", agent)

  def apply(self, data):
    self.agent.connected = data['connected']

class CallBackDepositInfo(CallBackBase):
  """
  예수금 반영 콜백
  """
  def __init__(self, agent):
    super().__init__("deposit_info", agent)

  def apply(self, data):
    self.agent.account.set_deposit_from_tr(data)

class CallBackGrossAssetInfo(CallBackBase):
  """
  계좌평가 그로스 잔고내역 반영 콜백 (싱글데이터)
  """
  def __init__(self, agent):
    super().__init__("gross_asset_info", agent)

  def apply(self, data):
    self.agent.account.set_gross_asset_from_tr(data)

class CallBackIndividualAssetInfo(CallBackBase):
  """
  계좌평가 개별종목 잔고내역 반영 콜백 (멀티데이터)
  """
  def __init__(self, agent):
    super().__init__("individual_asset_info", agent)

  def apply(self, data):
    self.agent.account.set_individual_asset_from_tr(data)

class CallBackUnexecutedOrderInfo(CallBackBase):
  """
  미체결 주문 반영 콜백 (멀티데이터)
  """
  def __init__(self, agent):
    super().__init__("unexecuted_order_info", agent)

  def apply(self, data):
    self.agent.account.set_unexecuted_order_from_tr(data)

class CallBackRealTimeMarketStatus(CallBackBase):
  """
  실시간 '장시작시간' 콜백
  """
  def __init__(self, agent):
    super().__init__("real_time_market_status", agent)

  def apply(self, data):
    self.agent.apply_real_time_market_status(data)

class CallBackRealTimeStockPrice(CallBackBase):
  """
  실시간 '주식체결' 콜백
  """
  def __init__(self, agent):
    super().__init__("realtime stock price (주식체결)", agent)

  def apply(self, data):
    self.agent.apply_real_time_stock_price(data)

class CallBackRealTimeIndexPrice(CallBackBase):
  """
  실시간 '업종지수' 콜백
  """
  def __init__(self, agent):
    super().__init__("realtime index price (지수체결)", agent)

  def apply(self, data):
    self.agent.apply_real_time_index_price(data)

class CallBackChejanExecution(CallBackBase):
  """
  실시간 체잔 '주문체결' 콜백
  """
  def __init__(self, agent):
    super().__init__("chejan excecution (체잔: 주문체결)", agent)

  def apply(self, data):
    self.agent.apply_chejan_execution(data)

class CallBackChejanAccountBalance(CallBackBase):
  """
  실시간 체잔 '잔고' 콜백
  """
  def __init__(self, agent):
    super().__init__("chejan account bank balance (체잔: 잔고)", agent)

  def apply(self, data):
    self.agent.apply_chejan_account_balance(data)

class Account:
  def __init__(self, acc_no, user_name, is_real):
    self.acc_no = acc_no
    self.user_name = user_name
    self.is_real  = is_real
    self.__d2deposit = 0
    self.__gross_asset_dict = {}
    self.__individual_asset_dict = {}
    self.__unexecuted_order_dict = {}
    self.__bid_ask_dict = {}

  def __str__(self):
    return '\n'.join([f"Account(acc_no={self.acc_no}, user_name={self.user_name}, is_real={self.is_real})",
    f"deposit={self.__d2deposit}",
    f"__gross_asset_dict={self.__gross_asset_dict}",
    f"__individual_asset_dict={self.__individual_asset_dict}",
    f"__unexecuted_order_dict={self.__unexecuted_order_dict}"])

  @property
  def d2deposit(self):
    return self.__d2deposit

  @property
  def individual_asset_dict(self):
    return self.__individual_asset_dict

  @d2deposit.setter
  def d2deposit(self, value):
    self.__d2deposit = value

  def set_deposit_from_tr(self, data):
    self.__d2deposit = int(data['d+2출금가능금액'].iloc[0])

  def set_gross_asset_from_tr(self, data):
    """
    그로스 계좌평가결과 반영
    """
    row = data.iloc[0]
    self.__gross_asset_dict.update(
      {
        '총평가금액': int(row['총평가금액']),
        '총평가손익금액': int(row['총평가손익금액']),
        '총수익률(%)': float(row['총수익률(%)'])/100.0,
      }
    )

  def set_individual_asset_from_tr(self, data):
    """
    종목별평가결과 반영
    """
    self.__individual_asset_dict = {}
    for i, row_data in data.iterrows():
      item_code = row_data['종목번호'][1:]
      self.__individual_asset_dict[item_code] = {
        '종목명': row_data['종목명'],
        '보유수량': int(row_data['보유수량']),
        '매입가': int(row_data['매입가']),
        '현재가': int(row_data['현재가']),
        '평가금액': int(row_data['평가금액']),
        '평가손익': int(row_data['평가손익']),
        '수익률(%)': float(row_data['수익률(%)'])/100.0, # 9월19일 기준 100을 곱한 값이 전달고 있음 (100으로 나눠야 함)
        '매입금액': int(row_data['매입금액']),
        '매매가능수량': int(row_data['매매가능수량']),
      }

  def set_unexecuted_order_from_tr(self, data):
    """
    미체결 주문 반영
    """
    self.__unexecuted_order_dict = {}
    for i, row_data in data.iterrows():
      order_no = row_data['주문번호']
      self.__unexecuted_order_dict[order_no] = {
        '종목코드': row_data['종목코드'][1:],
        '주문번호': order_no,
        '종목명': row_data['종목명'],
        '주문수량': int(row_data['주문수량']),
        '주문가격': int(row_data['주문가격']),
        '미체결수량': int(row_data['미체결수량']),
        '체결량': int(row_data['체결량']),
        '주문구분': row_data['주문구분'],
        '주문구분': row_data['주문구분'],
        '매매구분': row_data['매매구분'],
        '주문상태': row_data['주문상태'],
      }

  def update_unexecuted_order_and_check_if_completed(self, data):
    """
    미체결수량이 0이 되면 미체결 주문에서 제거 및 True 반환
    """
    if data['주문번호'] in self.__unexecuted_order_dict:
      self.__unexecuted_order_dict[data['주문번호']].update(data)
    else:
      self.__unexecuted_order_dict[data['주문번호']]=data

    if data['미체결수량'] == 0:
      del self.__unexecuted_order_dict[data['주문번호']]
      return True

    return False

  def update_individual_asset_and_check_if_empty(self, items):
    """보유수량이 0이면 제거"""
    code = items['종목코드']
    if items['보유수량'] == 0:
      del self.__individual_asset_dict[code]
      return True
    
    self.__individual_asset_dict[code].update(items)
    return False

  def holds(self, code):
    return code in self.__individual_asset_dict

  def how_many_to_sell(self, code):
    """"매도가능수량"""
    best_ask_price = self.__bid_ask_dict[code]['(최우선)매도호가'] # 최우선 매수호가가 곧 best_ask_price
    return best_ask_price, self.__individual_asset_dict[code]['매매가능수량']

  def how_many_to_buy(self, code):
    """매수가능수량"""
    best_bid_price = self.__bid_ask_dict[code]['(최우선)매도호가'] # 최우선 매도호가 가 곧 best_bid_price
    return best_bid_price, int(self.__d2deposit / (best_bid_price * (1+0.00015))) # TODO: 수수료 하드코딩 제거할 것

  def update_real_time_bid_ask_price(self, real_data):
    field_dic = RealType.REALTYPE['주식체결']
    transform_dic = RealType.PostProcessing['주식체결']

    code = real_data['code']
    items = {tag:transform_dic[tag](real_data[fid]) for tag, fid in field_dic.items() if fid in real_data}

    self.__bid_ask_dict[code] = items

class AgentState(IntEnum):
  INIT = 0 # 최초 상태
  WAIT = 1 # 준비완료 대기중
  BEING_RECOVERED = 2 # 복구중
  READY = 3 # 준비완료 (정상 행동 수행 가능)
  BEING_TERMINATED = 4 # 종료중
  TERMINATED = 5 # 종료됨

class AgentStateManager:
  # TODO: 사용하지 않은 기능으로 폐기 예정
  def __init__(self, agent):
    self.__agent = agent
    self.state = AgentState.INIT

  def is_ready(self):
    return self.state == AgentState.READY

  def on_ready(self):
    self.state = AgentState.READY
    #TODO: 분봉데이터 최종 정리
    self.__agent.on_ready()

  def on_being_recovered(self):
    self.state = AgentState.BEING_RECOVERED
    pass

  def on_being_terminated(self):
    self.state = AgentState.BEING_TERMINATED
    pass

  def on_terminated(self):
    self.state = AgentState.TERMINATED
    pass

  def step(self):
    if self.state == AgentState.WAIT:
      if self.__agent.market_state == MarketState.OPEN: 
        if self.__agent.launched_state == LaunchedTimingState.LAUNCHED_BEFORE_OPEN:
          self.state = AgentState.READY
          self.on_ready()
        elif self.__agent.recovery_manager.state < RecoveryState.RECOVERED:
          self.state = AgentState.BEING_RECOVERED
          self.on_being_recovered()
    elif self.state == AgentState.BEING_RECOVERED:
      if self.__agent.recovery_manager.state == RecoveryState.RECOVERED:
        self.state = AgentState.READY
        self.on_ready()
    elif self.state == AgentState.READY:
      if self.__agent.market_state == MarketState.AFTER_CLOSE:
        self.state = AgentState.BEING_TERMINATED
        self.on_being_terminated()
    elif self.state == AgentState.BEING_TERMINATED:
      if self.__agent.market_state == MarketState.AFTER_CLOSE_COMPLETELY:
        self.state = AgentState.TERMINATED
        self.on_terminated()

class CombinedMinuteData:
  def __init__(self, agent:RTAgent, history_minute_provider: MinuteChartDataProvider, today_minute_provider: MinuteChartDataProvider):
    self.__agent = agent
    self.__history_minute_provider = history_minute_provider # 어제까지 분봉데이터 (정적)
    self.__today_minute_provider = today_minute_provider # 오늘 분봉데이터 (정적)
    self.__static_history_minute_data = None
    self.__static_today_minute_data = None
    self.__pre_pivot_data = {} # 피봇 전까지 정적 데이터
    self.__combined_data = {} # 결합데이터
    self.__ts_last_updated = None
    self.hhmmssdic = {
      'static_minute_end': '090000', # 정적 분봉데이터 마지막 시간 (미만)
      'real_minute_start': '090000', # 실시간 분봉 시작 (이상)
      'real_minute_end': '153000', # 실시간 분봉 종료 (미만)
    }

  @property
  def get_ts_last_updated(self):
    return self.__ts_last_updated

  @property
  def today_minute_provider(self):
    return self.__today_minute_provider

  @property
  def combined_data(self):
    return self.__combined_data

  def __get_last_inserted_ts(self):
    return max([v.index[-1] for k, v in self.__pre_pivot_data.items()])
      
  def set_static_history_minute_data(self):
    # TODO: 기간 하드 코딩 수정 필요
    self.__static_history_minute_data = self.__history_minute_provider.get_history_from_ndays_ago()

  def set_static_today_minute_data(self):
    # 수집한 분봉 데이터중 오늘 것만 로딩
    self.__static_today_minute_data = self.__today_minute_provider.get_history_from_ndays_ago(n_days=0)

  def finalize_pre_pivot_data(self):
    '''
    히스토리와 정적으로 수집한 오늘 분봉 결합 -> 최종 정적 데이터
    '''
    if self.__static_history_minute_data is None:
      return
    for st_code in map(lambda x: x[0], self.__agent.config_manager.retrieve_candidate_ETFs()):
      if not self.__static_today_minute_data or st_code not in self.__static_today_minute_data:
        self.__pre_pivot_data[st_code] = self.__static_history_minute_data[st_code]
      else:
        self.__pre_pivot_data[st_code] = pd.concat((self.__static_history_minute_data[st_code], self.__static_today_minute_data[st_code]), axis=0)
    for st_code in map(lambda x: x[0], self.__agent.config_manager.retrieve_candidate_ETFs()):
      self.__agent.get_logger().info(f'PIVOT 이전 데이터 (실시간 반영 전 정적 데이터): {st_code=} {len(self.__pre_pivot_data[st_code])} / {self.__pre_pivot_data[st_code].index[-1]}')

  def update_minute_data_realtime(self, real_data:pd.DataFrame):
    if self.__pre_pivot_data is None:
      return
    real_data['dt'] = pd.to_datetime(real_data['dt']).dt.tz_localize('Asia/Seoul')
    for st_code in map(lambda x: x[0], self.__agent.config_manager.retrieve_candidate_ETFs()):
      real_df = real_data.query(f"st_code == '{st_code}'").set_index('dt')
      if len(real_df) > 0:
        self.__combined_data[st_code] = pd.concat((self.__pre_pivot_data[st_code], real_df), axis=0)
        self.__agent.get_logger().info(f'분봉데이터 실시간 업데이트 완료: {st_code=}, {len(self.__pre_pivot_data[st_code])} / {self.__pre_pivot_data[st_code].index[-1]} / {real_df.index[-1]}')
  
class RTAgent:
  def __init__(self, kiwoom_backend_ocx:RTKiwoom = None, config_manager:ConfigManager = None, log_config_path=None, log_path=None):
    self.__rt = kiwoom_backend_ocx
    self.__login_info = {}
    self.__account = {}
    self.__timer = None
    self.__config_manager = config_manager
    self.__rt_data_provider = RealTimeTickDataPrivder.Factory(config_manager)
    self.__time_manager = TimeManager(fast_debug=False) 
    self.__market_state = MarketState.NOT_OPERATIONAL
    self.__launched_state = LaunchedTimingState.LAUNCHED_BEFORE_OPEN
    self.__recovery_manager = None
    self.__action_manager = None
    self.__toggled_minutes_checker = None
    self.minute_data_manager = CombinedMinuteData(
      self,
      history_minute_provider=MinuteChartDataProvider.Factory(config_manager, tag='history'),
      today_minute_provider=MinuteChartDataProvider.Factory(config_manager, tag='today')
      )
    
    self.callbacks = {
      # "Connect":CallBackConnect(self),
      "DepositInfo":CallBackDepositInfo(self),
      "GrossAssetInfo":CallBackGrossAssetInfo(self),
      "IndividualAssetInfo":CallBackIndividualAssetInfo(self),
      "UnexecutedOrderInfo":CallBackUnexecutedOrderInfo(self),
      }

    self.realtime_callbacks = {
      "장시작시간":CallBackRealTimeMarketStatus(self),
      "주식체결":CallBackRealTimeStockPrice(self),
      "업종지수":CallBackRealTimeIndexPrice(self),
      "체잔:주문체결":CallBackChejanExecution(self),
      "체잔:잔고":CallBackChejanAccountBalance(self),
      ###########

    }

    if kiwoom_backend_ocx is None:
      self.__log_instance=Logging(log_config_path, log_path)

    # RTKiwoom에 등록
    if self.__rt is not None:
      self.__rt.set_rt_agent(self)

    # TODO: 테스트 후 지울 것
    self.__test_is_done = False

  def apply_real_time_market_status(self, real_data):
    """
    실시간 '장시작시간' 처리
    """
    status = real_data['215'].strip()
    if status == '0':
      self.__market_state = MarketState.BEFORE_OPEN
    elif status == '3':
      self.__market_state = MarketState.OPEN
      self.__time_manager.set_ts_pivot(TimeManager.get_now() + pd.Timedelta(seconds=10))
      self.minute_data_manager.finalize_pre_pivot_data()
    elif status == '2':
      self.__market_state = MarketState.AFTER_SIMULTANEOUS_QUOTE 
    elif status == '4':
      self.__market_state = MarketState.AFTER_CLOSE

    self.get_logger().info(real_data)

  def apply_real_time_stock_price(self, real_data):
    """
    실시간 '주식체결' 처리
    """
    # self.get_logger().info(real_data)
    self.__rt_data_provider.insert_by_dataframe(real_data)
    self.__account.update_real_time_bid_ask_price(real_data)

  def apply_real_time_index_price(self, real_data):
    """
    실시간 '업종지수' 처리
    """
    self.get_logger().info(real_data)

  def apply_chejan_execution(self, real_data):
    # self.get_logger().info(real_data)

    field_dic = RealType.REALTYPE['주문체결']
    transform_dic = RealType.PostProcessing['주문체결']

    items = {tag:transform_dic[tag](real_data[fid]) for tag, fid in field_dic.items() if fid in real_data}
    self.get_logger().info(items)
    if self.__account.update_unexecuted_order_and_check_if_completed(items):
      if self.__action_manager:
        self.__action_manager.update_execution_completion_info(items)
      self.get_logger().info(f"주문체결 완료: 종목코드={items['종목코드']} 주문번호={items['주문번호']}")

  def apply_chejan_account_balance(self, real_data):
    # self.get_logger().info(real_data)

    field_dic = RealType.REALTYPE['잔고']
    transform_dic = RealType.PostProcessing['잔고']

    items = {tag:transform_dic[tag](real_data[fid]) for tag, fid in field_dic.items() if fid in real_data}
    self.get_logger().info(items)
    if self.__account.update_individual_asset_and_check_if_empty(items):
      self.get_logger().info(f"개별종목 잔고 소진: 관리에서 제외됨 종목코드={items['종목코드']}")

  @property
  def login_info(self):
    return self.__login_info

  @property
  def config_manager(self):
    return self.__config_manager

  @property
  def account(self):
    return self.__account

  @property
  def time_manager(self):
    return self.__time_manager

  @property
  def rt_data_provider(self):
    return self.__rt_data_provider

  @property
  def market_state(self):
    return self.__market_state
  
  @property
  def launched_state(self):
    return self.__launched_state

  @property
  def recovery_manager(self):
    return self.__recovery_manager

  def get_logger(self):
    if self.__rt is not None:
      return self.__rt.get_logger()
    else:
      return self.__log_instance.logger

  def _callback(self, data):
      print(data)
  
  def is_connected(self):
    return self.__rt.connected

  def __set_login_info(self):
    acc_cnt = self.__rt.GetLoginInfo("ACCOUNT_CNT")
    account_nos = self.__rt.GetLoginInfo("ACCNO").split(';')
    user_id = self.__rt.GetLoginInfo("USER_ID")
    user_name = self.__rt.GetLoginInfo("USER_NAME")
    server_gubun = self.__rt.GetLoginInfo("GetServerGubun")
    self.__login_info = {
      "acc_cnt": int(acc_cnt),
      "account_nos": account_nos,
      "user_id": user_id,
      "user_name": user_name,
      "server_gubun": "모의투자" if server_gubun == "1" else "실서버",
    }

  def get_account_str(self):
    return str(self.__account)

  def get_today_etf_minute_data(self, code):
    dic = {'종목코드': code, 'output': "주식분봉차트조회", '수정주가구분': "1", '틱범위': "1", 'next':0}
    df = self.__rt.block_TR_request("opt10080", **dic)
    return df

  def try_to_sell(self, code, ask_request_info):
    """
    시장가 매도
    TODO: 스크린번호 처리
    """

    _, ask_quantity = ask_request_info

    ret_code = self.__rt.SendOrder("시장가매도", "0301", self.__account.acc_no, 2, code, ask_quantity, 0, "03", "")
    self.get_logger().info(f"매도주문: {code} {ask_quantity=} => f{self.__rt.kiwoom_errors[ret_code]=}")

  def try_to_buy(self, code, bid_request_info):
    """
    지정가 매수
    TODO: 스크린번호 처리
    """
    bid_price, bid_quantity = bid_request_info

    ret_code = self.__rt.SendOrder("지정가매수", "0301", self.__account.acc_no, 1, code, bid_quantity, bid_price, "00", "")
    self.get_logger().info(f"매수주문: {code} {self.account.d2deposit=}, {bid_price=}, {bid_quantity=} => f{self.__rt.kiwoom_errors[ret_code]=}")

  def __test_buy_and_sell(self):
    """
    매수-매도 테스트
    """
    self.__action_manager = ActionManager(self, 'Y')
    self.__test_is_done = True

  def treat_response(self, prediction_dic:dict):
    """
    grpc 서버로부터 받은 예측 결과를 처리
    """
    tag, prob = sorted(prediction_dic.items(), key=lambda x: x[1])[-1]
    if not self.__action_manager:
      self.get_logger().info(f"Decision from Server: {tag=}, {prob=}")
      self.__action_manager = ActionManager(self, tag)
    else:
      self.get_logger().info(f"이미 ActionManager가 존재!!! 이번 응답 무시함. ")

  def update_deposit(self):
    dic = {"계좌번호":self.login_info['account_nos'][0], "비밀번호":"0000", "비밀번호입력매체구분":"00", "조회구분":1}
    dic['output'] = '예수금상세현황'
    dic['next'] = 0
    df = self.__rt.block_TR_request("opw00001", **dic)
    self.callbacks['DepositInfo'].apply(df)
  
  def update_account_info(self):
    # 주기적으로 호출받게 됨
     # 예수금상세현황요청
    self.update_deposit()

    # 계좌평가잔고내역요청
    dic = {"계좌번호":self.login_info['account_nos'][0], "비밀번호":"0000", "비밀번호입력매체구분":"00", "조회구분":1}
    dic['output'] = '계좌평가결과'
    dic['next'] = 0
    df = self.__rt.block_TR_request("opw00018", **dic)
    self.callbacks['GrossAssetInfo'].apply(df)

    dfs = []
    dic = {"계좌번호":self.login_info['account_nos'][0], "비밀번호":"0000", "비밀번호입력매체구분":"00", "조회구분":1}
    dic['output'] = '계좌평가잔고개별합산'
    dic['next'] = 0
    df = self.__rt.block_TR_request("opw00018", **dic)
    dfs.append(df)

    while self.__rt.tr_remained:
      dic['next'] = 2
      time.sleep(1)
      df = self.__rt.block_TR_request("opw00018", **dic)
      dfs.append(df)
    
    df = pd.concat(dfs)
    self.callbacks['IndividualAssetInfo'].apply(df)  

    self.get_logger().info(self.__account)

  def launch_timer(self):
    self.__timer = QTimer()
    self.__timer.setInterval(1000)
    self.__timer.timeout.connect(self.__timer_callback)
    self.__timer.start()
    self.__toggled_minutes_checker = ToggledMinutesChecker(TimeManager.get_now())

  # 타이머 콜백 함수 (1초마다 호출)
  def __timer_callback(self):
    # 분이 변경 되었는지
    ts_now = TimeManager.get_now()
    is_new_minute = self.__toggled_minutes_checker.updae_and_check_if_minute_changed(ts_now)

    # 프로그램 강제 종료 조건
    if self.__market_state == MarketState.AFTER_CLOSE:
      self.get_logger().info(f"장 마감으로 인한 프로그램 종료: {TimeManager.get_now(ts_now)}")
      sys.exit(0)

    # 복구 매니저가 필요하면 이에 대한 디스패치 수행
    if self.__recovery_manager:
      self.__recovery_manager.dispatch_request()

    # 거래 가능 상황
    # 시장 OPEN 상태 & 복구매니저가 없는 경우: 장 개장전 기동된 경우임
    # 시장 OPEN 상태 & 복구매니저가 복구 완료한 경우: 장 개장후 기동되었으며 복구가 된 상황
    can_do_trading = (self.__market_state == MarketState.OPEN) and ( self.__recovery_manager is None or self.__recovery_manager.state == RecoveryState.RECOVERED )
    
    # 거래 가능 상황이라면
    if can_do_trading:
      # 매초 처리할 내용들
      if self.__action_manager:
        self.__action_manager.step()
        if self.__action_manager.is_completed():
          self.get_logger().info("ActionManager completed")
          self.__action_manager = None

      if is_new_minute:
        self.update_account_info()

      # 매 분마다 처리할 내용들
      if is_new_minute and self.__time_manager.get_ts_pivot():
        ts_from = self.__time_manager.get_ts_pivot()
        ts_end = TimeManager.ts_floor_time(TimeManager.get_now())
        # df = self.__rt_data_provider.query('SELECT count(*) cnt FROM today_in_ticks')
        # self.get_logger().info(f"{df.iloc[0]['cnt']} real tick rows are inserted.")
        if ts_end - ts_from >= pd.Timedelta(1, unimt='m'):
          self.get_logger().info(f"[실시간 분봉 계산 범위: {ts_from}, {ts_end})")
          from_pivot_df = self.__rt_data_provider.make_minute_chart_df(ts_from, ts_end)
          self.minute_data_manager.update_minute_data_realtime(from_pivot_df)
          # self.minute_data_manager.get_combined_data('069500')[-400:].to_csv('probe_realtime_minute.csv')
          # self.get_logger().info(from_pivot_df)

          if self.minute_data_manager.combined_data:
            # 만약 리커버리 시간이 15시 20분과 30분 이내 라면, 유입된 실시간 틱이 없어 combined_data가 비어 있게 된다. 
            request = RequestBuilder(self, self.minute_data_manager.combined_data, self.config_manager, window_size=720)
            # print(self.minute_data_manager.combined_data)
            response = request.send_and_wait()
            self.treat_response(response)

  ## 콜백 함수들
  ## TODO: 필요한 콜백만 추가
  def on_ready(self):
    self.get_logger().info("on_ready")
    self.__recovery_manager.get_effective_real_minutes_str()

  def PreStage(self):
    # 로그인 (연결)
    self.__rt.ComConnect()

    # 로그인 정보
    self.__set_login_info()
    self.__account = Account(
      self.__login_info['account_nos'][0], 
      self.__login_info['user_name'],
      self.__login_info['server_gubun'] == '실서버'
    )

    # 예수금상세현황요청
    dic = {"계좌번호":self.login_info['account_nos'][0], "비밀번호":"0000", "비밀번호입력매체구분":"00", "조회구분":1}
    dic['output'] = '예수금상세현황'
    dic['next'] = 0
    df = self.__rt.block_TR_request("opw00001", **dic)
    self.callbacks['DepositInfo'].apply(df)

    # 계좌평가잔고내역요청
    dic = {"계좌번호":self.login_info['account_nos'][0], "비밀번호":"0000", "비밀번호입력매체구분":"00", "조회구분":1}
    dic['output'] = '계좌평가결과'
    dic['next'] = 0
    df = self.__rt.block_TR_request("opw00018", **dic)
    self.callbacks['GrossAssetInfo'].apply(df)

    dfs = []
    dic = {"계좌번호":self.login_info['account_nos'][0], "비밀번호":"0000", "비밀번호입력매체구분":"00", "조회구분":1}
    dic['output'] = '계좌평가잔고개별합산'
    dic['next'] = 0
    df = self.__rt.block_TR_request("opw00018", **dic)
    dfs.append(df)

    while self.__rt.tr_remained:
      dic['next'] = 2
      time.sleep(1)
      df = self.__rt.block_TR_request("opw00018", **dic)
      dfs.append(df)
    
    df = pd.concat(dfs)
    self.callbacks['IndividualAssetInfo'].apply(df)

    # 미체결요청
    dfs = []
    dic = {"계좌번호":self.login_info['account_nos'][0], "전체종목구분":"0", "매매구분":0, "종목코드":"", "체결구분":"1"}
    dic['output'] = '미체결'
    dic['next'] = 0
    dic['has_no_single'] = True
    df = self.__rt.block_TR_request("opt10075", **dic)
    dfs.append(df)

    while self.__rt.tr_remained:
      dic['next'] = 2
      time.sleep(1)
      df = self.__rt.block_TR_request("opt10075", **dic)
      dfs.append(df)

    df = pd.concat(dfs)
    self.callbacks['UnexecutedOrderInfo'].apply(df)

    # 어제까지 분봉 데이터 로딩
    self.minute_data_manager.set_static_history_minute_data()

  def MainStage(self):
    self.__time_manager.set_timestamp('MainStageEntered')
    self.launch_timer()

    if False and not self.__test_is_done:
      # TODO: 디버깅 목적으로 남겨둠; 제거 필요
      # 임의 때나 실행시켜도 정상 실행인 것처럼 취급하기 위함: 
      self.__launched_state = LaunchedTimingState.LAUNCHED_BEFORE_OPEN
      self.apply_real_time_market_status({'215':'3'})
    elif self.__time_manager.get_timestamp('MainStageEntered') > self.__time_manager.when_to_open():
      self.get_logger().warning(f"Recovery needed...{self.__time_manager.get_timestamp('MainStageEntered')} / {self.__time_manager.when_to_open()}")
      self.__market_state = MarketState.OPEN
      self.__launched_state = LaunchedTimingState.LAUNCHED_AFTER_OPEN
      self.__recovery_manager = RecoveryManager(self)
    else:
      self.__launched_state = LaunchedTimingState.LAUNCHED_BEFORE_OPEN
      # self.apply_real_time_market_status({'215':'3'})

    # 장시작시간 수신
    rtRequest = RealtimeRequestItem("2000", [], ["215", "20", "214"], "0")
    self.__rt.RegisterRealtimeRequest(rtRequest)

    # 관심종목 체결 수신
    rtRequest = RealtimeRequestItem("2001", ["069500", "114800", "226490"], ["20", "16", "17", "18", "10", "15", "11", "12", "13", "27", "28"], "0")
    self.__rt.RegisterRealtimeRequest(rtRequest)
    if self.__recovery_manager:
      self.__recovery_manager.set_state(RecoveryState.START_WARMUP_RT_EXECUTION)

if __name__ == "__main__":
  pass