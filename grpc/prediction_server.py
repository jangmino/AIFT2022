from concurrent import futures
import logging

import grpc
import prediction_pb2
import prediction_pb2_grpc


class PredictionServer(prediction_pb2_grpc.PredictorServicer):

    def Predict(self, request, context):
        # dummy implementation for just testing
        ss = request.st_code + f",length={len(request.x)}"
        logging.getLogger().info(ss + str(request.x))
        return prediction_pb2.PredictResponse(st_code=ss, actions={0:0.9, 1:0.1})


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    prediction_pb2_grpc.add_PredictorServicer_to_server(PredictionServer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    serve()