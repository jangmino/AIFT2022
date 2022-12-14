# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from . import prediction_pb2 as prediction__pb2


class PredictorStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Predict = channel.unary_unary(
                '/Predictor/Predict',
                request_serializer=prediction__pb2.PredictRequest.SerializeToString,
                response_deserializer=prediction__pb2.PredictResponse.FromString,
                )


class PredictorServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Predict(self, request, context):
        """Predicts the decision for the provided instances. 
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_PredictorServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Predict': grpc.unary_unary_rpc_method_handler(
                    servicer.Predict,
                    request_deserializer=prediction__pb2.PredictRequest.FromString,
                    response_serializer=prediction__pb2.PredictResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Predictor', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Predictor(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Predict(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Predictor/Predict',
            prediction__pb2.PredictRequest.SerializeToString,
            prediction__pb2.PredictResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
