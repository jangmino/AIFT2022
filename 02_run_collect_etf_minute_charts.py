from pykiwoom.kiwoom import *
import time
import pandas as pd
import pickle
from tqdm.auto import tqdm

'''
 몇가지 ETF 종목과 업종 
'''

tr_dic = {
  'opt20005': {'001': 'kospi', '201': 'kospi200'},
  'opt10080': {'069500':'kodex_200', '114800':'kodex_inverse', '226490':'kodex_kospi'}
}

def make_argument_dic(tr_code, code, is_next=False):
  '''
    tr_code에 따라 적절한 arg_dic을 만들어서 반환한다.
  '''

  arg_dic = {'틱범위': "1", 'next':2 if is_next else 0}
  if tr_code == 'opt10080':
    arg_dic.update({'종목코드': code, 'output': "주식분봉차트조회", '수정주가구분': "1"})
  elif tr_code == 'opt20005':
    arg_dic.update({'업종코드': code, 'output': "업종분봉차트조회"})
  else:
    assert False, "Unknown tr_code"
  return arg_dic

def main_job(kiwoom, tr_code, code, name):
  dfs = []
  with tqdm(total=106) as pbar:
    df = kiwoom.block_request(__TODO__, __TODO__)
    dfs.append(df)
    nCalls = 1
    pbar.set_description(f'{code}/{name}')
    pbar.update(1)

    while kiwoom.tr_remained:
      time.sleep(1)
      df = kiwoom.block_request(__TODO__, __TODO__)
      dfs.append(df)
      nCalls += 1
      pbar.update(1)

  return pd.concat(dfs)

if __name__ == "__main__":
  kiwoom = Kiwoom()
  kiwoom.CommConnect(block=True)

  for tr_code, dic in tr_dic.items():
    for code, name in dic.items():
      df = main_job(kiwoom, tr_code, code, name)
      df.to_csv(f'data/{name}.csv', index=False)
      print(f'{name} saved.')
