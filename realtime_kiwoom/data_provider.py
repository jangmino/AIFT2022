import pandas as pd
from sqlalchemy import create_engine

class TodayMinuteChartDataProvider:
  table_query = '''
  CREATE TABLE IF NOT EXISTS today_in_minute (
    st_code TEXT not NULL,
    dt TEXT not NULL,
    open INTEGER,
    high INTEGER,
    low INTEGER,
    close INTEGER,
    volume INTEGER
  )
  '''
  index_query = '''
  CREATE INDEX IF NOT EXISTS idx_today_in_minute ON today_in_minute (st_code, dt)
  '''

  insert_query = '''
  INSERT INTO today_in_minute (st_code, dt, open, high, low, close, volume)
  VALUES (?, ?, ?, ?, ?, ?, ?)
  '''

  def __init__(self, engine):
    pass


class RealTimeTickDataPrivder:
  table_query = '''
  CREATE TABLE IF NOT EXISTS today_in_ticks (
    st_code TEXT not NULL,
    dt TEXT not NULL,
    open INTEGER,
    high INTEGER,
    low INTEGER,
    close INTEGER,
    volume INTEGER
  )
  '''
  index_query = '''
  CREATE INDEX IF NOT EXISTS idx_today_in_ticks ON today_in_ticks (st_code, dt)
  '''

  insert_query = '''
  INSERT INTO today_in_ticks (st_code, dt, open, high, low, close, volume)
  VALUES (?, ?, ?, ?, ?, ?, ?)
  '''

  def __init__(self, db_path, in_memory_db = False, with_index=False):
      self.engine = create_engine(f"sqlite://") if in_memory_db else create_engine(f"sqlite:///{db_path}")
      self.with_index = with_index
      self.create_table()

  def clear_table(self):
    with self.engine.connect() as connection:
      connection.execute('DROP TABLE IF EXISTS today_in_ticks')
      if self.with_index:
        connection.execute('DROP INDEX IF EXISTS idx_today_in_ticks')

  def create_table(self):
    with self.engine.connect() as connection:
      connection.execute(self.table_query)
      connection.execute(self.index_query)
  
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

  def insert(self, real_data):
    with self.engine.begin() as connection:
      connection.execute(self.insert_query, self.__build_data(real_data))

  def insert_by_dataframe(self, real_data):
    self.build_dataframe(real_data).to_sql('today_in_ticks', self.engine, if_exists='append', index=False)