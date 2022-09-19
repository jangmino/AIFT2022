from realtime_kiwoom.rt_kiwoom import *
from realtime_kiwoom.agent import *

if __name__ == "__main__":
    app = QApplication(sys.argv)
    rt_kiwoom_ocx = RTKiwoom()
    agent = RTAgent(rt_kiwoom_ocx)
    agent.get_logger().info('Start PreStage')
    agent.PreStage()
    agent.get_logger().info(agent.get_account_str())
    agent.get_logger().info('End PreStage')
    app.exec_()