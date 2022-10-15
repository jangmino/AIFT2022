from __future__ import annotations
from abc import *
from lzma import is_check_supported
from realtime_kiwoom import Agent
from miscs.config_manager import ConfigManager

class ActionBase(metaclass=ABCMeta):
  def __init__(self, agent:Agent):
    self.__agent = agent
    self.submitted=False

  def is_submitted(self):
    return self.submitted

  def do(self, **kwargs):
    if self.is_submitted():
      return
    self.before()
    self.submit(**kwargs)
    self.submitted = True

  @abstractmethod
  def before(self):
    """Action 실행 전에 실행되는 메소드"""
    pass

  @abstractmethod
  def submit(self, **kwargs):
    """Action 실행 메소드"""
    pass

  @abstractmethod
  def can_terminate(self, manager:ActionManager):
    """종료 해도 되는지 여부를 반환하는 메소드"""
    pass
  

class ActionNop(ActionBase):
  def __init__(self, agent:Agent):
    super().__init__(agent)

  def before(self):
    self.agent.get_logger().info("ActionNop Before")

  def submit(self, **kwargs):
    return

  def can_terminate(self, manager:ActionManager):
    return True


class ActionBuy(ActionBase):

  def __init__(self, agent:Agent, code:str):
    super().__init__(agent)
    self.code = code

  def before(self):
    self.agent.get_logger().info("ActionBuy Before")

  def submit(self, **kwargs):
    # quantity == 0 이면 전량 매수 시도 한다.
    self.agent.try_to_buy(self.code, quantity=0)

  def can_terminate(self, manager:ActionManager):
    '''체잔: 미체결수량 0이면 완료로 취급하자'''
    if self.code in manager.completion_info_dic and manager.completion_info_dic[self.code] == '매수':
      return True

class ActionSell(ActionBase):
  
  def __init__(self, agent:Agent, code:str):
    super().__init__(agent)
    self.code = code

  def before(self):
    self.agent.get_logger().info("ActionSell Before")

  def submit(self, **kwargs):
    # quantity == 0 이면 전량 매도 시도 한다.
    self.agent.try_to_sell(self.code, quantity=0)

  def can_terminate(self, manager:ActionManager):
    '''체잔: 미체결수량 0이면 완료로 취급하자'''
    if self.code in manager.completion_info_dic and manager.completion_info_dic[self.code] == '매도':
      return True


class ActionManager:
  def __init__(self, agent:Agent, action_type:str):
    self.agent = agent
    self.action_type = action_type
    self.action_list = []
    self.__initilalize()
    self.__build_action_list(action_type)
    self.completion_info_dic = {}

  def is_completed(self):
    return len(self.action_list) == 0

  def __initilalize(self):
    self.tag_code_dic = {action_tag:code for code, _, action_tag in self.agent.config_manager.retrieve_candidate_ETFs()}

  def __build_action_list(self, action_type:str):
    if action_type == 'NOP':
      self.action_list.append(ActionNop(self.agent))
    elif action_type == 'X':
      if self.agent.holds(self.tag_code_dic['X']):
        self.action_list.append(ActionNop(self.agent))
      elif self.agent.holds(self.tag_code_dic['Y']):
        self.action_list.append(ActionSell(self.agent, self.tag_code_dic['Y']))
        self.action_list.append(ActionBuy(self.agent, self.tag_code_dic['X']))
    elif action_type == 'Y':
      if self.agent.holds(self.tag_code_dic['Y']):
        self.action_list.append(ActionNop(self.agent))
      elif self.agent.holds(self.tag_code_dic['X']):
        self.action_list.append(ActionSell(self.agent, self.tag_code_dic['X']))
        self.action_list.append(ActionBuy(self.agent, self.tag_code_dic['Y']))
    else:
      raise ValueError(f'Invalid action_type: {action_type}')

  def step(self):
    if self.is_completed():
      return

    self.agent.get_logger().info(f'ActionManager: {self.action_type=}, len={len(self.action_list)}')
    action = self.action_list[0]
    if not action.is_submitted():
      action.do()
    if action.can_terminate(self):
      self.action_list.pop(0)

  def update_execution_completion_info(self, execution_data:dict):
    self.completion_info_dic.update(
      {execution_data['종목코드']: execution_data['매도수구분']}
    )
    


