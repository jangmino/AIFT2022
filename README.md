# AIFT2022
Artificial Intelligence Financial Trading 2022

## TR 목록 조회기반 히스토리 데이터 수집

|TR 코드|내용|대상|
|------|---|---|
|opt10080| 주식분봉차트조회요청|'KODEX 200', 'KODEX 인버스', 'KODEX KOSPI'|
|opt20005| 업종분봉조회요청| 'KOSPI', 'KOSPI 200'|


내용
- 학습, 분석, 백테스팅을 위한 히스토리 데이터를 증권사 서버로부터 확보하는 기능 개발 (.py)
- 확보한 데이터를 MySQL, SQLite에 추가하는 기능 개발 (주피터 노트북)

참고
- pykiwoom: (https://github.com/sharebook-kr/pykiwoom) 의 기능을 활용
