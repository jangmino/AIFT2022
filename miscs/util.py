import os
from datetime import datetime, timedelta
import math
import re
import collections
import time
from pytz import timezone

FORMAT_DATE = "%Y-%m-%d"
FORMAT_DATETIME = "%Y%m%d%H%M%S"
FORMAT_MONTH = "%Y/%m"
FORMAT_MONTHDAY = "%m/%d"


def get_today(tz=timezone('Asia/Seoul')):
    dt = datetime.fromtimestamp(time.time(), tz)
    date = dt.date()
    return date


def get_date_ago(n):
    return get_today() - timedelta(days=n)


def get_str_today(dt_format="%Y-%m-%d"):
    str_today = get_today().strftime(dt_format)
    return str_today


def get_str_date_ago(n):
    str_date = get_date_ago(n).strftime(FORMAT_DATE)
    return str_date


def get_str_month():
    str_month = get_today().strftime(FORMAT_MONTH)
    return str_month


def get_str_date_nago(n=20, base_date=None):
    if base_date is None:
        base_date = get_today()
    if type(base_date) is str:
        base_date = datetime.strptime()
    d = base_date - timedelta(days=n)
    return d.strftime(FORMAT_DATE)


def get_dayofweek():
    """
    :return: 0-4 평일, 5-6 주말
    """
    date_today = datetime.date.today()
    int_week = date_today.weekday()
    return int_week


def get_hour_min(tz=timezone('Asia/Seoul')):
    dt_now = datetime.now(tz)
    int_hour = dt_now.hour
    int_minute = dt_now.minute
    return int_hour, int_minute


def get_ts(tz=timezone('Asia/Seoul')):
    return datetime.now(tz)


def get_hhmmss(tz=timezone('Asia/Seoul')):
    return datetime.strftime(datetime.now(tz), "%H%M%S")


def is_to_overwait(query_hhmmss, duration_minutes=1, tz=timezone('Asia/Seoul')):
    ref_hhmmss = datetime.strftime(datetime.now(timezone('Asia/Seoul')) - timedelta(minutes=duration_minutes), '%H%M%S')
    return query_hhmmss < ref_hhmmss


def longer_than_duration(from_hhmmss, to_hhmmss, duration_in_minutes=20):
    return datetime.strptime(to_hhmmss, "%H%M%S") - datetime.strptime(from_hhmmss, "%H%M%S") > timedelta(minutes=duration_in_minutes)


def convert_date2month(str_date):
    if len(str_date) != 8:
        return None
    return '{}/{}'.format(str_date[:4], str_date[4:6])


def convert_str2date(str_date):
    return datetime.strptime(str_date, FORMAT_DATE)


def convert_date2str(dt):
    return dt.strftime(FORMAT_DATE)


def add_months(dt, months=1):
    return dt.replace(year=dt.year + math.floor((dt.month + months) / 12), month=max((dt.month + months) % 12, 1))


def convert_datetime2str(x):
    for k in x:
        if isinstance(x[k], datetime):
            x[k] = x[k].__str__()
    return x


# --------------------------------------------------------
# 변환 관련 유틸
# --------------------------------------------------------
def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def int_without_sgn(x):
    return x[1:] if x[0] == '+' or x[0] == '-' else x


def val_without_alphabet(x):
    return x if x[0].isdigit() else x[1:]