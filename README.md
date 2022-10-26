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
- ~~pykiwoom: (https://github.com/sharebook-kr/pykiwoom) 일부 참고~~

## 실시간 시스템

### 프리스테이지 (브랜치: feature/real_time_prestage)
- 로그인
- 계좌조회
- 잔고조회
- 미체결조회

### 메인스테이지 (브랜치: feature/real_time_mainstage)
- 실시간 주식체결정보 구독
- 분봉 데이터 계산
- 매수/매도 로직 계산
- 매수/매도 주문
- 장애처리
    - 장 중에 재기동시 복구 절차

기술적 지표/백테스팅 (브랜치: feature/techinal_indicators)
- Technical indicators
- 베이스라인 모델
    - flaml 활용하여 lightgbm 분류 문제 최적화
- Backtesting

## 예측서버 (브랜치: feature/pred_server_grpc)
- gRPC 서버-클라이언트 구현

## 기술적 지표/백테스팅 (브랜치: feature/techinal_indicators)
- Technical indicators
- Backtesting
- 추가 패키지
    - ta-lib
    - exchange-calendars
    - tqdm
    - flaml
## 설치 및 재현방법

### 콘다 env 생성

AIFT
- 32bit
- 키움 OpenAPI 연동 및, 실시간 액션 수행 에이전트
- gRPC 클라이언트

py310_64
- 64 비트
- 예측 서버 개발 및 서버 구동
- gRPC 서버
## 자동화

등등
