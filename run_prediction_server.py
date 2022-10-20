from __future__ import annotations
from concurrent import futures
from realtime_kiwoom.rt_kiwoom import *
from realtime_kiwoom.agent import *
from miscs.time_manager import TimeManager
from miscs.config_manager import ConfigManager
import grpc
import grpc_python.prediction_pb2 as prediction_pb2
import grpc_python.prediction_pb2_grpc as prediction_pb2_grpc
from models.baseline_model import InputBuilder_BaselineModel, BaselineModel
import sys
import pickle

class PredictionServer(prediction_pb2_grpc.PredictorServicer):
    def __init__(self, model, logger):
        self.model=model
        self.logger=logger

    def Predict(self, request, context):
        # dummy implementation for just testing
        input_builder = InputBuilder_BaselineModel(request)
        # self.logger.info(f"{input_builder.X_test=}")
        y_pred = self.model.predict(input_builder.X_test)
        # self.logger.info(f"{y_pred=}")
        y_proba = self.model.predict_proba(input_builder.X_test)
        # self.logger.info(f"{y_proba=}")

        self.logger.info(f"{input_builder.X_test.index[-1]}; NOP={y_proba[0][0]} X={y_proba[0][1]} Y={y_proba[0][2]}")

        return prediction_pb2.PredictResponse(actions={'NOP':y_proba[0][0], 'X':y_proba[0][1], 'Y':y_proba[0][2]})


def serve(model, logger):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    prediction_pb2_grpc.add_PredictorServicer_to_server(PredictionServer(model, logger), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":

    cm = ConfigManager('config/.config.xml')
    agent = RTAgent(
        kiwoom_backend_ocx=None, 
        config_manager=cm, 
        log_config_path=cm.get_path('log_config_path'),
        log_path=cm.get_path('server_log_path')
        )

    model_meta_info = cm.get_model_info('Baseline')
    agent.get_logger().info(f"Server starts with Baseline model: {model_meta_info['model_path']}")
    model = BaselineModel(model_meta_info['model_path'])

    serve(model, agent.get_logger())


