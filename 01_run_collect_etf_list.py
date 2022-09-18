from pykiwoom.kiwoom import *
import pandas as pd

'''

참고함수
    GetCodeListByMarket(market) : 시장별 종목코드를 반환한다.
    market : "0" - 코스피, "8" - ETF

    GetMasterCodeName(code) : 종목코드에 해당하는 종목명을 반환한다.

    etf.csv로 저장

    - 069500 : KODEX 200
    - (226490 : KODEX 코스피)
    - 114800 : KODEX 인버스
'''

if __name__ == "__main__":
    kiwoom = Kiwoom()
    kiwoom.CommConnect(block=True)

    etf = kiwoom.GetCodeListByMarket('8')

    ret = [(e, kiwoom.GetMasterCodeName(e)) for e in etf]
    pd.DataFrame.from_records(ret, columns=['share_code', 'share_name']).to_csv('etf.csv', index=False)

