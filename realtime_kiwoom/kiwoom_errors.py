class KiwoomErrors:
  def __init__(self):
    self.errors = {
        0: "OP_ERR_NONE",
        -10: "OP_ERR_FAIL",
        -100: "OP_ERR_LOGIN",
        -101: "OP_ERR_CONNECT",
        -102: "OP_ERR_VERSION",
        -103: "OP_ERR_FIREWALL",
        -104: "OP_ERR_MEMORY",
        -105: "OP_ERR_INPUT",
        -106: "OP_ERR_SOCKET_CLOSED",
        -200: "OP_ERR_SISE_OVERFLOW",
        -201: "OP_ERR_RQ_STRUCT_FAIL",
        -202: "OP_ERR_RQ_STRING_FAIL",
        -203: "OP_ERR_NO_DATA",
        -204: "OP_ERR_OVER_MAX_DATA",
        -205: "OP_ERR_DATA_RCV_FAIL",
        -206: "OP_ERR_OVER_MAX_FID",
        -207: "OP_ERR_REAL_CANCEL",
        -300: "OP_ERR_ORD_WRONG_INPUT",
        -301: "OP_ERR_ORD_WRONG_ACCTNO",
        -302: "OP_ERR_OTHER_ACC_USE",
        -303: "OP_ERR_MIS_2BILL_EXC",
        -304: "OP_ERR_MIS_5BILL_EXC",
        -305: "OP_ERR_MIS_1PER_EXC",
        -306: "OP_ERR_MIS_3PER_EXC",
        -307: "OP_ERR_SEND_FAIL",
        -308: "OP_ERR_ORD_OVERFLOW",
        -309: "OP_ERR_MIS_300CNT_EXC",
        -310: "OP_ERR_MIS_500CNT_EXC",
        -340: "OP_ERR_ORD_WRONG_ACCTINFO",
        -500: "OP_ERR_ORD_SYMCODE_EMPTY",
    }

  def __getitem__(self, key):
    try:
        return self.errors[key]
    except KeyError:
        return "OP_ERR_UNKNOWN"