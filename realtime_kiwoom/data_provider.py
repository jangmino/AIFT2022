from __future__ import annotations
# from abc import *
from sqlite3 import Time
import pandas as pd
import os
from sqlalchemy import create_engine
from miscs.config_manager import ConfigManager
from miscs.time_manager import TimeManager

class QueryBaseStrings:
  table_create_query = '''
  CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    st_code TEXT not NULL,
    dt TEXT not NULL,
    open INTEGER,
    high INTEGER,
    low INTEGER,
    close INTEGER,
    volume INTEGER
  )
  '''
  index_create_query = '''
  CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON {TABLE_NAME} (st_code ASC, dt ASC)
  '''

  insert_query = '''
  INSERT INTO {TABLE_NAME} (st_code, dt, open, high, low, close, volume)
  VALUES (?, ?, ?, ?, ?, ?, ?)
  '''

  drop_table_query = '''
  DROP TABLE IF EXISTS {TABLE_NAME}
  '''

  drop_index_query = '''
  DROP INDEX IF EXISTS {INDEX_NAME}
  '''

class DataProviderBase():

  def __init__(self, config_manager:ConfigManager, db_path, table_name, index_name=None, drop_table=False):
    self.config_manager = config_manager
    self.db_name = db_path
    self.table_name = table_name
    self.index_name = index_name
    self.table_create_query = QueryBaseStrings.table_create_query.format(TABLE_NAME=table_name)
    self.index_create_query = QueryBaseStrings.index_create_query.format(INDEX_NAME=index_name, TABLE_NAME=table_name)
    self.insert_query = QueryBaseStrings.insert_query.format(TABLE_NAME=table_name)
    self.drop_table_query = QueryBaseStrings.drop_table_query.format(TABLE_NAME=table_name)
    self.drop_index_query = QueryBaseStrings.drop_index_query.format(INDEX_NAME=index_name)

    self.with_index = False if self.index_name is None or self.index_name == '' else True

    self.engine = self.get_engine()

    if drop_table:
      self.clear_table()
    self.create_table()

    self.today = pd.Timestamp.today(tz='Asia/Seoul').date()

  def is_in_memory_db(self, db_name):
    return db_name == ':memory:'

  def get_engine(self):
    return create_engine("sqlite://") if self.is_in_memory_db(self.db_name) else create_engine("sqlite:///" + self.db_name)

  def create_table(self):
    with self.engine.connect() as connection:
      connection.execute(self.table_create_query)
      if self.with_index:
        connection.execute(self.index_create_query)   

  def clear_table(self):
    with self.engine.connect() as connection:
      connection.execute(self.drop_table_query)
      if self.with_index:
        connection.execute(self.drop_index_query) 

  def query(self, query_string):
    with self.engine.connect() as connection:
      return pd.read_sql_query(query_string, connection) 


class MinuteChartDataProvider(DataProviderBase):

  @staticmethod
  def Factory(config_manager: ConfigManager, tag='history'):
    """
    Factory method: MinuteChartDataProvider 객체 생성
    """
    table_info = config_manager.get_tables()
    return MinuteChartDataProvider(
      config_manager,
      db_path=os.path.join(config_manager.get_work_path(), config_manager.get_database()['database']), 
      table_name=table_info[tag]['table_name'], 
      drop_table=table_info[tag]['drop_table']
    )

  def __init__(self, config_manager, db_path, table_name, drop_table=True):
    super().__init__(config_manager, db_path, table_name, index_name=f'idx_{table_name}', drop_table=drop_table)

  def filter_from_raw_data(self, raw_df, code, ts_from:pd.Timestamp=None, ts_end:pd.Timestamp=None):
    """
    [ts_from, ts_end)
    to_datetime() 사용시, format을 지정해주지 않으면 각 엘리먼트마다 포맷 추론을 시도하므로,
    속도가 매우 느려진다. (십만건 기준: 0.3ms vs 5s)
    """
    cols = ['현재가','거래량','체결시간','시가','고가','저가']
    df_ = raw_df[cols]
    df = pd.concat((
    df_['체결시간'],
    df_['시가'].astype('int').abs(),
    df_['고가'].astype('int').abs(),
    df_['저가'].astype('int').abs(),
    df_['현재가'].astype('int').abs(),
    df_['거래량'].astype('int').abs(),
    ), axis=1)
    df.columns=['dt','open','high','low','close', 'volume']
    df['st_code'] = code

    dt_series = pd.to_datetime(df['dt'], format='%Y%m%d%H%M%S').dt.tz_localize('Asia/Seoul')
    ii = (dt_series >= ts_from) if ts_end is None else (dt_series > ts_from) & (dt_series < ts_end)
    return df[ii]

  def get_ts_last_inserted(self, code):
    """
    마지막으로 입력된 시간을 반환
    """
    last_dt = self.query(f"SELECT dt FROM {self.table_name} WHERE st_code='{code}' ORDER BY dt DESC LIMIT 1")
    return TimeManager.str_to_ts(last_dt['dt'].values[0] if len(last_dt) != 0 else '19700101000000')

  def insert_raw_dataframe_data(self, raw_df:pd.DatFame, code:str, ts_end:pd.Timestamp=None):
    """
    [ts_after_last_inserted, ts_end): 날 것의 데이터프레임 데이터를 삽입
    """
    num_inserted = 0
    if len(raw_df) != 0:
      ts_after_last_inserted=TimeManager.ts_min_shift(self.get_ts_last_inserted(code), minutes=1, floor=True)
      num_inserted = self.filter_from_raw_data(raw_df, code, ts_from=ts_after_last_inserted, ts_end=ts_end).to_sql(self.table_name, self.engine, if_exists='append', index=False)
    return num_inserted

  def get_history_from_ndays_ago(self, n_days=14):
    '''
    과거 n일치 데이터를 가져온다.
    '''
    from_ts = TimeManager.ts_day_shift(TimeManager.get_now(), days=-n_days, floor=True)
    df = self.query(f'''
    SELECT * FROM {self.table_name} 
    WHERE dt >= '{TimeManager.ts_to_str(from_ts)}'
    ORDER BY st_code ASC, dt ASC
    ''')
    df['dt'] = pd.to_datetime(df['dt']).dt.tz_localize('Asia/Seoul')
    return {st_code: df.query(f"st_code=='{st_code}'").set_index('dt') for st_code in map(lambda x: x[0], self.config_manager.get_candidate_ETFs())}

class RealTimeTickDataPrivder(DataProviderBase):
  make_minute_chart_query = '''
  select DISTINCT t.st_code, {YYYYMMDD}||t.minute||'00' as dt,
  first_value(t.close) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as open,
  max(t.close) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as high,
  min(t.close) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as low,
  last_value(t.close) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close,
  sum(t.volume) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as volume
  from (
    select *, substr(dt, 0, 5) as minute
    from today_in_ticks
    where dt >= '{FROM_HHMMSS}' and dt < '{END_HHMMSS}'
    ) as t
  '''

  @staticmethod
  def Factory(config_manager: ConfigManager):
    """
    Factory method: RealTimeTickDataPrivder 객체 생성
    """
    return RealTimeTickDataPrivder(config_manager)

  def __init__(self, coonfig_manager:ConfigManager):
      super().__init__(coonfig_manager, ':memory:', table_name='today_in_ticks', index_name='idx_today_in_ticks', drop_table=True)

  def __build_data(self, real_data):
    return (
      real_data['code'],
      real_data['20'], # 체결시간 (HHMMSS)
      abs(int(real_data['16'])), # 시가 +-
      abs(int(real_data['17'])), # 고가 +-
      abs(int(real_data['18'])), # 저가 +-
      abs(int(real_data['10'])), # 현재가 +-
      abs(int(real_data['15'])), # 거래량 +-
    )

  def __build_dataframe(self, real_data):
    return pd.DataFrame(
      [self.__build_data(real_data)],
      columns=['st_code', 'dt', 'open', 'high', 'low', 'close', 'volume']
    )

  def insert_by_query(self, real_data):
    with self.engine.begin() as connection:
      connection.execute(self.insert_query, self.__build_data(real_data))

  def insert_by_dataframe(self, real_data):
    self.__build_dataframe(real_data).to_sql(self.table_name, self.engine, if_exists='append', index=False)

  def recent_inserted_ts(self):
    # 실시간 체결이라서 HHMMSS 형식이다.
    query_string = f'''
    SELECT dt FROM {self.table_name} ORDER BY dt DESC LIMIT 1
    '''
    with self.engine.connect() as connection:
      hhmmss = connection.execute(query_string).fetchall()[0][0]
    return TimeManager.hhmmss_to_ts(hhmmss)

  def make_minute_chart_df(self, ts_from:pd.Timestamp=None, ts_end:pd.Timestamp=None):
    """
    [ts_from, ts_end)
    """
    query_string = RealTimeTickDataPrivder.make_minute_chart_query.format(
      YYYYMMDD=TimeManager.ts_to_str(TimeManager.get_now(), '%Y%m%d'), 
      FROM_HHMMSS=TimeManager.ts_to_str(TimeManager.ts_floor_time(ts_from, freq='T'), '%H%M00') if ts_from is not None else '090000',
      END_HHMMSS=TimeManager.ts_to_str(TimeManager.ts_floor_time(ts_end, freq='T'), '%H%M00') if ts_end is not None else '153001'
      )
    return self.query(query_string=query_string)

  def retrieve_all(self):
    return self.query(f'SELECT * FROM {self.table_name}')


  if __name__ == '__main__':
    pass
