from realtime_kiwoom.rt_kiwoom import *
from realtime_kiwoom.agent import *
from miscs.time_manager import TimeManager
from miscs.config_manager import ConfigManager
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    cm = ConfigManager('config/.config.xml')
    rt_kiwoom_ocx = RTKiwoom()
    agent = RTAgent(rt_kiwoom_ocx, config_manager=cm)
    if not agent.time_manager.is_today_open():
        agent.get_logger().warning("Today is not a open day... will be terminated.")
        sys.exit(0)
    elif not agent.time_manager.less_than_minutes_before_open(30):
        agent.get_logger().warning("Now does not reach the open time - 30 minutes... will be terminated.")
        sys.exit(0)
    elif TimeManager.get_now() > agent.time_manager.when_to_close():
        agent.get_logger().warning("Now is after close time... will be terminated.")
        sys.exit(0)

    agent.get_logger().info('Start PreStage')
    agent.PreStage()
    agent.get_logger().info(agent.get_account_str())
    agent.get_logger().info('End PreStage')
    agent.get_logger().info('Start MainStage')

    agent.MainStage()
    agent.get_logger().info('End MainStage... EventLoop enters.')
    app.exec_()