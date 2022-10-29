from __future__ import annotations
from realtime_kiwoom.rt_kiwoom import *
from realtime_kiwoom.agent import *
from miscs.time_manager import TimeManager
from miscs.config_manager import ConfigManager
import grpc
import grpc_python.prediction_pb2 as prediction_pb2
import grpc_python.prediction_pb2_grpc as prediction_pb2_grpc
from realtime_kiwoom.data_provider import *
from grpc_python.request import RequestBuilder
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    cm = ConfigManager('config/.config.xml')
    agent = RTAgent(
        kiwoom_backend_ocx=None, 
        config_manager=cm, 
        log_config_path=cm.get_path('log_config_path'),
        log_path=cm.get_path('agent_log_path')
        )

    history_provider = MinuteChartDataProvider.Factory(cm, tag='history')
    history_minute_dic = history_provider.get_history_from_ndays_ago(n_days=5)
    
    # tag_code_dic = {tag:code for code, _, tag in cm.retrieve_candidate_ETFs()}

    # request_data = {}
    # for code, dic in history_minute_dic.items():
    #     request_data[code] = dic.reset_index().drop(columns=['st_code'])
    #     request_data[code]['dt'] = request_data[code].dt.dt.strftime('%Y%m%d%H%M')

    # x_history = [prediction_pb2.Item(**record) for record in request_data[tag_code_dic['X']].to_dict(orient='records')]
    # y_history = [prediction_pb2.Item(**record) for record in request_data[tag_code_dic['Y']].to_dict(orient='records')]

    # with grpc.insecure_channel('localhost:50051') as channel:
    #     stub = prediction_pb2_grpc.PredictorStub(channel)
    #     response = stub.Predict(prediction_pb2.PredictRequest(x_history=prediction_pb2.History(items=x_history), y_history=prediction_pb2.History(items=y_history)))
    # agent.get_logger().info(f"Prediction client received: {dict(response.actions)}")

    agent.get_logger().info(f"Prediction client before request")
    request = RequestBuilder(agent, history_minute_dic, cm, window_size=720)
    response = request.send_and_wait()
    agent.get_logger().info(f"Prediction client received: {response}")

