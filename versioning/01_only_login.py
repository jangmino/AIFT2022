import sys 
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *

'''
로그인만 수행하는 단순 응용프로그램

용도
- 로그인 후 메시지 루프를 수행하고 있음
- 윈도우즈 태스크바에 표시되는 아이콘을 통해...
- AUTOLOGIN 모드 변경 가능
- 계좌 비밀번호 저장 가능
'''


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.dynamicCall("CommConnect()")
        self.ocx.OnEventConnect.connect(self.OnEventConnect)

    def OnEventConnect(self, err_code):
        print(err_code)


app = QApplication(sys.argv)
window = MyWindow()
window.show()
app.exec_()