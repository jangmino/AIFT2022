# from abc import *
import pandas as pd
from sqlalchemy import create_engine

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

  def __init__(self, db_path, table_name, index_name=None, drop_table=False):
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
  def __init__(self, db_path, table_name, drop_table=True):
    super().__init__(db_path, table_name, index_name=f'idx_{table_name}', drop_table=drop_table)

  def filter_from_raw_data(self, raw_df, code):
    cols = ['현재가','거래량','체결시간','시가','고가','저가']
    df_ = raw_df[cols]
    df = pd.concat((
    df_['체결시간'],
    df_['시가'].abs(),
    df_['고가'].abs(),
    df_['저가'].abs(),
    df_['현재가'].abs(),
    df_['거래량'].abs(),
    ), axis=1)
    df.columns=['dt','open','high','low','close', 'volume']
    df['st_code'] = code
    return df

  def insert_by_dataframe(self, raw_df, code):
    if len(raw_df) != 0:
      self.filter_from_raw_data(raw_df, code).to_sql(self.table_name, self.engine, if_exists='append', index=False)

  def safe_bulk_insert_from_csv(self, csv_path, code):
    '''
    벌크 인서트: 매일 1회 실행한다고 가정
    '''
    df = pd.read_csv(csv_path, dtype={'체결시간':str})
    df.rename(columns={'체결시간':'dt'}, inplace=True)
    last_dt = self.query(f"SELECT dt FROM {self.table_name} WHERE st_code='{code}' ORDER BY dt DESC LIMIT 1")

    self.insert_by_dataframe(
      df.query(f'dt > "{last_dt["dt"][0]}"') if len(last_dt) > 0 else df
      , code
    )  


class RealTimeTickDataPrivder(DataProviderBase):
  make_minute_chart_query = '''
  select DISTINCT t.st_code, {YYYYMMDD}||t.minute||'00' as dt,
  first_value(t.close) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as open,
  max(t.close) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as high,
  min(t.close) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as low,
  last_value(t.close) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close,
  sum(t.volume) over (partition by t.st_code, t.minute order by t.dt ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as volume
  from (
    select *, substr(dt, 0, 5) as minute from today_in_ticks substr
    ) as t
  '''  

  def __init__(self):
      super().__init__(':memory:', table_name='today_in_ticks', index_name='idx_today_in_ticks', drop_table=True)
      self.make_minute_chart_query = RealTimeTickDataPrivder.make_minute_chart_query.format(YYYYMMDD=self.today.strftime('%Y%m%d'))

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
    self.__build_dataframe(real_data).to_sql('today_in_ticks', self.engine, if_exists='append', index=False)

  def recent_inserted_ts(self):
    query_string = '''
    SELECT dt FROM today_in_ticks ORDER BY dt DESC LIMIT 1
    '''
    with self.engine.connect() as connection:
      ts_str = connection.execute(query_string).fetchall()[0][0]
    return pd.to_datetime(ts_str, format='%H%M%S').replace(year=self.today.year, month=self.today.month, day=self.today.day).tz_localize('Asia/Seoul')

  def make_minute_chart_df(self):
    return self.query(self.make_minute_chart_query)

  if __name__ == '__main__':
    minute_data_provider1 = MinuteChartDataProvider(db_path="../data/kiwoom_db.sqlite3", table_name='data_in_minute', drop_table=True)
    minute_data_provider2 = MinuteChartDataProvider(db_path="../data/kiwoom_db.sqlite3", table_name='today_in_minute', drop_table=True)
    print(minute_data_provider1.query(f'select count(*) cnt from {minute_data_provider1.table_name}'))
    print(minute_data_provider2.query(f'select count(*) cnt from {minute_data_provider2.table_name}'))
    pass