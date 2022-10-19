from __future__ import annotations
from realtime_kiwoom.rt_kiwoom import *
from realtime_kiwoom.agent import *
from miscs.time_manager import TimeManager
from miscs.config_manager import ConfigManager
import grpc
import grpc_python.prediction_pb2 as prediction_pb2
import grpc_python.prediction_pb2_grpc as prediction_pb2_grpc
from realtime_kiwoom.data_provider import *
import sys

class RequestBuilder:
  def __init__(self, agent:RTAgent, history_minute_dic, config_manager:ConfigManager, window_size=0):
    self.agent = agent
    self.history_minute_dic = history_minute_dic
    self.tag_code_dic = {action_tag:code for code, _, action_tag in config_manager.retrieve_candidate_ETFs()}
    self.window_size=window_size

  def __build(self):
    info_dic = {}
    request_data = {}
    self.agent.get_logger().info(f"inside build")
    for code, dic in self.history_minute_dic.items():
      # window_size 만큼의 최신 길이만큼만 사용
      request_data[code] = dic.reset_index().drop(columns=['st_code']) if self.window_size==0 else dic.reset_index().drop(columns=['st_code'])[-self.window_size:]
      request_data[code]['dt'] = request_data[code].dt.dt.strftime('%Y%m%d%H%M')
      info_dic[code] = dic.index[-1]

    info_str = '; '.join([f'code:{code}, dt:{dt}' for code, dt in info_dic.items()])
    self.agent.get_logger().info(f"{info_str}")

    x_history = [prediction_pb2.Item(**record) for record in request_data[self.tag_code_dic['X']].to_dict(orient='records')]
    y_history = [prediction_pb2.Item(**record) for record in request_data[self.tag_code_dic['Y']].to_dict(orient='records')]
    return prediction_pb2.PredictRequest(x_history=prediction_pb2.History(items=x_history), y_history=prediction_pb2.History(items=y_history))

  def send_and_wait(self):
    with grpc.insecure_channel('localhost:50051') as channel:
      stub = prediction_pb2_grpc.PredictorStub(channel)
      response = stub.Predict(self.__build())
    return dict(response.actions)