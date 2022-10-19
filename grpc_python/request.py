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
  def __init__(self, history_minute_dic, config_manager:ConfigManager):
      self.history_minute_dic = history_minute_dic
      self.tag_code_dic = {action_tag:code for code, _, action_tag in config_manager.retrieve_candidate_ETFs()}

  def build(self):
    request_data = {}
    for code, dic in self.history_minute_dic.items():
      request_data[code] = dic.reset_index().drop(columns=['st_code'])
      request_data[code]['dt'] = request_data[code].dt.dt.strftime('%Y%m%d%H%M')

    x_history = [prediction_pb2.Item(**record) for record in request_data[self.tag_code_dic['X']].to_dict(orient='records')]
    y_history = [prediction_pb2.Item(**record) for record in request_data[self.tag_code_dic['Y']].to_dict(orient='records')]
    return prediction_pb2.PredictRequest(x_history=prediction_pb2.History(items=x_history), y_history=prediction_pb2.History(items=y_history))

  def send_and_wait(self):
    with grpc.insecure_channel('localhost:50051') as channel:
      stub = prediction_pb2_grpc.PredictorStub(channel)
      response = stub.Predict(self.build())
    return dict(response.actions)