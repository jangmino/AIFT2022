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
- 키움 OpenAPI 연동 및, 실시간 트레이딩 액션 수행 클라이언트
- 설치
```bash
set CONDA_FORCE_32BIT=1
conda create -n AIFT python=3.8
cd $REPO_FOLDER$/AIFT2002/pip_install
pip install -r requirements_aift.txt
```
- 주의: requirements.txt에서 아래 패키지 whl 파일의 경로를 `$REPO_FOLDER$/AIFT2002/pip_install` 로 수정한 후 인스톨 할 것!!!
```
pywinpty @ file:///c:/Sungshin/Lectures/2022/repos/AIFT2022/pip_install/pywinpty-2.0.5-cp38-none-win32.whl
```

AIFT64
- 64 비트
- 예측 서버 개발 및 서버 구동
- 설치
```bash
conda create -n AIFT64 python=3.8
cd $REPO_FOLDER$/AIFT2002/pip_install
pip install -r requirements_aift64.txt
```
- 주의: requirements.txt에서 아래 패키지 whl 파일의 경로를 `$REPO_FOLDER$/AIFT2002/pip_install` 로 수정한 후 인스톨 할 것!!!
```
TA-Lib @ file:///c:/Sungshin/Lectures/2022/repos/AIFT2022/pip_install/TA_Lib-0.4.24-cp38-cp38-win_amd64.whl
```

# 자동화

준비
- 윈도우즈 10 운영체제 (11도 가능)
- Anaconda 설치되어 있어야 함
- https://github.com/jangmino/AIFT2022.git 리포지터리 다운로드
- 윈도우즈 작업 스케줄러 활용

초기화
- config 폴더의 `.config.template.xml` 파일을 복사하여 `.config.xml` 파일 생성하고...
- `.config.xml` 파일의 내용을 수정하여 사용자 환경에 맞게 설정
- db 폴더의 `kiwoom_db.sqlite3` 파일이 없다면...
- `$REPO_FOLDER$/AIFT2002` 폴더 (리포지터리 메인 폴더)에서 `python run_collect_etf_minute_charts.py` 명령어 실행하여 데이터베이스 파일 생성 (약 1년치 데이터 확보)

세팅
1. `AIFT_run_versioning`: `scheduler_run_versioning.bat` 등록
    - `run_versioning.py` 실행하여 키움 OpenAPI 버전 업데이트
    - 월~금 매일 07시 트리거
2. `AIFT_run_collect_daily_data`: `scheduler_run_collect_eft_minute_charts.bat`
    - `run_collect_eft_minute_charts.py` 실행하여 EFT 일봉 데이터 수집하여 반영
    - 월~금 매일 17시 트리거 (장이 열리지 않았으면 실제 진행하지 않음)
3. `AIFT_run_agent`: `scheduler_run_agent.bat`
    - `run_agent.py` 실시간 트레이딩 액션 수행
    - 월~금 매일 08시 30분 트리거

서버실행
- 수동 실행
- `AIFT64` 환경에서 `$REPO_FOLDER$/AIFT2002`로 이동 후
- `python run_prediction_server.py` 실행 시켜둠 (일단위 종료할 필요 없음)
