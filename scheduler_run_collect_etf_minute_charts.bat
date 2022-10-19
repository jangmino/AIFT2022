@ECHO ON
call c:\ProgramData\Anaconda3\Scripts\activate.bat AIFT
python run_collect_etf_minute_charts.py --daily

