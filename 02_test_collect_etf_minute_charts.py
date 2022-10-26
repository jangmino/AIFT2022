from realtime_kiwoom.rt_kiwoom import *
import time
import pandas as pd
import pickle
from tqdm.auto import tqdm
from realtime_kiwoom.data_provider import *
import os
import argparse
from miscs.config_manager import ConfigManager
from miscs.time_manager import TimeManager

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
    arg_dic.update({'업종코드': code, 'output': "업종분봉조회"})
  else:
    assert False, "Unknown tr_code"
  return arg_dic

def main_job(kiwoom, tr_code, code, name, is_daily=False):
  dfs = []
  with tqdm(total=1 if is_daily else 106) as pbar:
    df = kiwoom.block_TR_request(tr_code,
                              **make_argument_dic(tr_code, code))
    dfs.append(df)
    nCalls = 1
    pbar.set_description(f'{code}/{name}')
    pbar.update(1)

    if not is_daily:
      while kiwoom.tr_remained:
        time.sleep(1)
        df = kiwoom.block_TR_request(tr_code,
                                  **make_argument_dic(tr_code, code, is_next=True))
        dfs.append(df)
        nCalls += 1
        pbar.update(1)

  return pd.concat(dfs)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-d", "--daily", help="하루치의 데이터만 수집", action="store_true")
  parser.add_argument("-n", "--daysago", type=int, help="number of days ago", default=0)
  args = parser.parse_args()

  cm = ConfigManager('config/.config.xml')
  table_info = cm.get_tables()

  if args.daily:
    ts = TimeManager.ts_day_shift(TimeManager.get_now(), days=-args.daysago, floor=True)
    day_str = TimeManager.ts_to_str(ts, format="%Y%m%d")
    from_dt_str = TimeManager.ts_to_str(ts, format="%Y%m%d090000")

  minute_data_provider = MinuteChartDataProvider.Factory(cm, tag='history')

  kiwoom = RTKiwoom()
  
  if args.daily:
    kiwoom.get_logger().info(f"Run with daily={args.daily}, daysago={args.daysago}")
    kiwoom.get_logger().info(f"Run with from_dt_str={from_dt_str}, day_str={day_str}")
  else:
    kiwoom.get_logger().info(f"Run as a long-range collector")

  kiwoom.ComConnect(block=True)
  for tr_code, dic in tr_dic.items():
    for code, name in dic.items():
      df = main_job(kiwoom, tr_code, code, name, is_daily=args.daily)

      if args.daily:
        df = df[df['체결시간'] >= from_dt_str]
        name = f'{name}_{day_str}'
      df.to_csv(f'data/{name}.csv', index=False)
      num_inserted = minute_data_provider.insert_raw_dataframe_data(df, code)
      kiwoom.get_logger().info(f'{name} saved (or updated) with #{num_inserted} rows')
