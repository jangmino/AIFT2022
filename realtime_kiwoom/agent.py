from abc import *
from numbers import Real
from realtime_kiwoom.rt_kiwoom import *
import pandas as pd
import time
from enum import IntEnum

class SystemState(IntEnum):
  NOT_OPERATIONAL = 0     # 비영업일
  BEFORE_OPEN = 1             # 영업일: 장 시작 전
  OPEN = 2   # 영업일: 개장
  AFTER_SIMULTANEOUS_QUOTE = 3    # 동시호가 시작 (15시 20분 이후)
  AFTER_CLOSE = 4                 # 15시 30분 이후
  AFTER_CLOSE_COMPLETELY = 5      # 16시 00분 이후

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
  def __init__(self, name, agent):
    super().__init__("realtime stock price (주식체결)", agent)

  def apply(self, data):
    self.agent.apply_stock_price_from_realtime(data)

class CallBackRealTimeIndexPrice(CallBackBase):
  """
  실시간 '업종지수' 콜백
  """
  def __init__(self, name, agent):
    super().__init__("realtime index price (지수체결)", agent)

  def apply(self, data):
    self.agent.apply_index_price_from_realtime(data)

class Account:
  def __init__(self, acc_no, user_name, is_real):
    self.acc_no = acc_no
    self.user_name = user_name
    self.is_real  = is_real
    self.__d2deposit = 0
    self.__gross_asset_dict = {}
    self.__individual_asset_dict = {}
    self.__unexecuted_order_dict = {}

  def __str__(self):
    return '\n'.join([f"Account(acc_no={self.acc_no}, user_name={self.user_name}, is_real={self.is_real})",
    f"deposit={self.__d2deposit}",
    f"__gross_asset_dict={self.__gross_asset_dict}",
    f"__individual_asset_dict={self.__individual_asset_dict}",
    f"__unexecuted_order_dict={self.__unexecuted_order_dict}"])

  @property
  def d2deposit(self):
    return self.__d2deposit

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
    for i, row_data in data.iterrows():
      item_code = row_data['종목번호']
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
    for i, row_data in data.iterrows():
      order_no = row_data['주문번호']
      self.__unexecuted_order_dict[order_no] = {
        '종목코드': row_data['종목코드'],
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

class RTAgent:
  def __init__(self, kiwoom_backend_ocx:RTKiwoom = None):
    self.__rt = kiwoom_backend_ocx
    self.__login_info = {}
    self.__account = {}
    self.__systemstate = SystemState.BEFORE_OPEN
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
    }

    # RTKiwoom에 등록
    self.__rt.set_rt_agent(self)

  def apply_real_time_market_status(self, real_data):
    """
    실시간 '장시작시간' 처리
    """
    status = real_data['215'].strip()
    if status == '0':
      self.__systemstate = SystemState.BEFORE_OPEN
    elif status == '3':
      self.__systemstate = SystemState.OPEN
    elif status == '2':
      self.__systemstate = SystemState.AFTER_SIMULTANEOUS_QUOTE 
    elif status == '4':
      self.__systemstate = SystemState.AFTER_CLOSE
    # self.__systemstate = SystemState(int(real_data['장운영구분']))
    self.get_logger().info(real_data)

  def apply_real_time_stock_price(self, real_data):
    """
    실시간 '주식체결' 처리
    """
    self.get_logger().info(real_data)

  def apply_real_time_index_price(self, real_data):
    """
    실시간 '업종지수' 처리
    """
    self.get_logger().info(real_data)

  @property
  def login_info(self):
    return self.__login_info

  @property
  def account(self):
    return self.__account

  def get_logger(self):
    return self.__rt.get_logger()

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

  ## 콜백 함수들
  ## TODO: 필요한 콜백만 추가

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

  def MainStage(self):
    # 장시작시간 수신
    rtRequest = RealtimeRequestItem("2000", [], ["215", "20", "214"], "0")
    self.__rt.RegisterRealtimeRequest(rtRequest)

    # 관심종목 체결 수신
    rtRequest = RealtimeRequestItem("2001", ["069500", "114800", "226490"], ["20", "16", "17", "18", "10", "15", "11", "12", "13"], "0")
    self.__rt.RegisterRealtimeRequest(rtRequest)

if __name__ == "__main__":
  pass