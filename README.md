# AIFT2022
Artificial Intelligence Financial Trading 2022

## TR 목록 조회기반 히스토리 데이터 수집 (브랜치: feature/batch_collect_minute)

|TR 코드|내용|대상|
|------|---|---|
|opt10080| 주식분봉차트조회요청|'KODEX 200', 'KODEX 인버스', 'KODEX KOSPI'|
|opt20005| 업종분봉조회요청| 'KOSPI', 'KOSPI 200'|


내용
- 학습, 분석, 백테스팅을 위한 히스토리 데이터를 증권사 서버로부터 확보하는 기능 개발 (.py)
- 확보한 데이터를 MySQL, SQLite에 추가하는 기능 개발 (주피터 노트북)

참고
- pykiwoom: (https://github.com/sharebook-kr/pykiwoom) 의 기능을 활용

## 실시간 시스템

프리스테이지 (브랜치: feature/real_time_prestage)
- 로그인
- 계좌조회
- 잔고조회
- 미체결조회

메인스테이지 (브랜치: feature/real_time_mainstage)
- 실시간 주식체결정보 구독
- 분봉 데이터 계산
- 매수/매도 로직 계산
- 매수/매도 주문

장애처리
- 장 중에 재기동시 복구 절차

등등
