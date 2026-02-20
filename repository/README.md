# WMS 재고 이력 분석 시스템

Pandas 기반 재고 현황 분석 및 레포팅 자동화 시스템

---

## 📁 전체 프로젝트 구조

```
wms_stock_hitory/
├── .claude/                      # Claude Code 설정
│   └── settings.local.json
├── config/                       # 설정 관리
│   ├── __init__.py
│   └── settings.py              # 환경 설정 (경로, 스케줄 간격 등)
├── data/                        # 데이터 폴더 (gitignore)
│   ├── raw/                     # 원본 데이터
│   ├── processed/               # 전처리된 데이터
│   └── reports/                 # 분석 리포트
├── logs/                        # 로그 파일 (gitignore)
├── output/                      # 출력 파일 (gitignore)
│   └── report_*.md             # 마크다운 리포트
├── repository/                  # SQL 쿼리 관리
│   ├── README.md               # 이 문서
│   └── stock_export.sql        # 재고 데이터 조회 쿼리
├── scheduler/                   # 스케줄러
│   ├── __init__.py
│   ├── job_scheduler.py        # 스케줄러 설정 (20분 간격)
│   └── jobs/                   # 스케줄 작업
│       ├── __init__.py
│       ├── db_export_job.py    # DB export 작업
│       ├── download_job.py     # 데이터 다운로드 작업
│       └── report_job.py       # 레포트 생성 작업
├── src/                        # 소스 코드
│   ├── __init__.py
│   ├── analyzer/               # 데이터 분석
│   │   ├── __init__.py
│   │   └── data_analyzer.py   # 최신 CSV 2개 자동 비교 분석
│   ├── downloader/             # 데이터 다운로드
│   │   ├── __init__.py
│   │   ├── data_downloader.py
│   │   └── db_exporter.py     # SQL Server → CSV export
│   ├── processor/              # 데이터 전처리
│   │   ├── __init__.py
│   │   └── data_processor.py
│   └── reporter/               # 리포트 생성
│       ├── __init__.py
│       ├── report_generator.py
│       └── slack_notifier.py  # 슬랙 알림 (사내 API)
├── tests/                      # 테스트 코드
│   └── __init__.py
├── .env                        # 환경 변수 (gitignore)
├── .env.example                # 환경 변수 예시
├── .gitignore                  # Git 제외 파일
├── main.py                     # 메인 실행 파일
└── requirements.txt            # Python 의존성
```

---

## 🚀 주요 기능

### 1. DB 자동 Export (20분 간격)
- SQL Server에서 재고 데이터 조회
- CSV 파일로 자동 저장 (`Stock{날짜}_{시간}.csv`)
- 한글 컬럼명 자동 변환
- 일치율 자동 계산: `min(CMS, Physical) / max(CMS, Physical) * 100`

### 2. 최신 파일 자동 비교 분석
- 폴더에서 **최신 CSV 파일 2개**를 자동으로 찾아 비교
- 날짜 기반 파일명 검색 불필요
- 일치율 변동 상품만 필터링 (CMS/WMS 수량 변화량이 다른 경우)
- 마크다운/CSV 리포트 자동 생성

### 3. 스케줄러 자동 실행
- DB export: 20분 간격
- 데이터 다운로드: 설정 가능
- 레포트 생성: 설정 가능

### 4. 슬랙 알림 (사내 API 연동)
- 변동 상품이 있을 경우 슬랙 알림
- Block Kit 형식 지원

---

## 📝 사용 방법

### 환경 설정

`.env` 파일을 생성하고 다음 내용을 설정하세요:

```env
# DB 설정 (SQL Server)
DB_TYPE=mssql
DB_HOST=211.111.24.245
DB_PORT=37729
DB_NAME=CMSGLOBAL
DB_USER=your_username
DB_PASSWORD=your_password
DB_ODBC_DRIVER=ODBC Driver 17 for SQL Server

# DB Export 설정
DB_EXPORT_OUTPUT_DIR=D:/inventory-test/daily-stock
DB_EXPORT_SQL_FILE=repository/stock_export.sql

# 재고 분석 설정
STOCK_ANALYSIS_INPUT_DIR=D:/inventory-test/daily-stock
STOCK_ANALYSIS_OUTPUT_DIR=./output

# 슬랙 설정 (선택)
SLACK_API_URL=https://your-company-api.com/slack
SEND_SLACK_NOTIFICATION=false

# 스케줄러 설정
SCHEDULE_DOWNLOAD_INTERVAL_MINUTES=60
SCHEDULE_REPORT_INTERVAL_MINUTES=120
```

### 실행 방법

```bash
# 1. 스케줄러 모드 (자동 실행)
python main.py

# 2. DB 수동 export
python main.py export

# 3. 최신 파일 2개 비교 분석 (수동)
python src/analyzer/data_analyzer.py
```

### 스케줄러 작동 방식

```
┌─────────────────────────────────────────────────────┐
│  main.py 실행                                        │
└─────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  스케줄러 시작 (20분 간격)                            │
│  - DB export job                                    │
│  - Download job (설정 간격)                          │
│  - Report job (설정 간격)                            │
└─────────────────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────┐    ┌─────┐    ┌─────┐
    │ DB  │    │다운 │    │리포 │
    │export│   │로드 │    │트  │
    └─────┘    └─────┘    └─────┘
         │
         ▼
    D:/inventory-test/daily-stock/
    Stock2026-02-20_1025.csv (생성)
```

---

## 📄 SQL 쿼리 관리 (repository/)

### stock_export.sql

재고 데이터를 조회하는 SQL 쿼리입니다.

**특징:**
- Multi-statement 지원 (임시 테이블, CTE 등)
- pyodbc로 직접 실행
- 결과는 자동으로 한글 컬럼명으로 변환

**현재 쿼리 구조:**
```sql
-- 1. 임시 테이블 생성
CREATE TABLE #TEMP_PROD (...)

-- 2. 데이터 삽입
INSERT INTO #TEMP_PROD ...

-- 3. CTE로 재고 계산
;WITH CTE_CMS_STOCK AS (...)

-- 4. 최종 결과 조회
SELECT prod_cd, prod_nm, brand_nm, cms_total_qty, ...
FROM CTE_CMS_STOCK
WHERE (cms_total_qty != 0 OR wms_total_qty != 0)
```

**CSV 출력 컬럼:**
- 상품코드, 상품명, 브랜드
- CMS 재고, WMS 재고, 대기 수량
- 일치율 (자동 계산)

### SQL 파일 수정 방법

1. `repository/stock_export.sql` 파일 수정
2. SQL Server Management Studio에서 쿼리 테스트
3. 컬럼명은 자유롭게 작성 (자동 매핑됨)
4. `python main.py export` 실행하여 테스트

**주의사항:**
- 마지막 SELECT 문이 실제 export 될 데이터입니다
- WHERE 조건으로 데이터 필터링 가능
- CMS/WMS 재고가 모두 0인 상품은 제외하는 것을 권장

---

## 📊 데이터 분석 (data_analyzer.py)

### 자동 비교 로직

```python
# 1. 최신 CSV 파일 2개 찾기 (수정 시간 기준)
latest_files = get_latest_csv_files(INPUT_DIR, count=2)

# 2. 파일 로드 (한글/영문 컬럼명 모두 지원)
today_df = load_csv_file_directly(latest_files[0])
yesterday_df = load_csv_file_directly(latest_files[1])

# 3. 상품코드 기준 병합 및 비교
comparison = today_df.merge(yesterday_df, on='prod_cd')

# 4. 변동 상품 필터링
# - 일치율 변화 > 0
# - CMS 변화량 ≠ Physical 변화량
changed = comparison[(change_abs > 0) & (cms_diff != physical_diff)]
```

### 출력 결과

**마크다운 리포트** (`output/report_2026-02-20.md`):
- 개요: 총 상품 수, 변동 상품, 변동 비율
- 변동 분석: 증가/감소 상품 목록
- 상세 내역: 상품코드, CMS/WMS 재고, 일치율 변화

**CSV 리포트** (`data/reports/changed_*.csv`):
- 변동 상품만 추출
- Excel에서 바로 확인 가능

---

## 🔧 추가 SQL 파일 작성

다른 용도의 SQL 쿼리를 추가할 수 있습니다:

```
repository/
├── stock_export.sql           # 기본 재고 조회
├── stock_history_export.sql   # 재고 이력 조회
└── custom_report.sql          # 커스텀 리포트
```

`.env` 파일에서 사용할 SQL 파일 지정:
```env
DB_EXPORT_SQL_FILE=repository/custom_report.sql
```

---

## 🐛 문제 해결

### DB 연결 실패
- ODBC Driver 17 for SQL Server 설치 확인
- 방화벽/네트워크 설정 확인
- `.env` 파일의 DB 정보 확인

### CSV 파일이 비어있음
- SQL 쿼리에서 WHERE 조건 확인
- SQL Server Management Studio에서 직접 쿼리 실행 테스트

### 한글 깨짐
- UTF-8 인코딩 설정 확인
- `sys.stdout.reconfigure(encoding='utf-8')` 적용 여부 확인

### 변동 상품이 없음
- 두 CSV 파일의 시간 간격이 너무 짧은 경우
- 실제로 재고 변동이 없는 경우

---

## 📌 버전 히스토리

### v1.2 (2026-02-20)
- ✅ DB export 스케줄러 추가 (20분 간격)
- ✅ 최신 파일 2개 자동 비교 기능
- ✅ 한글/영문 컬럼명 호환성 개선
- ✅ UTF-8 인코딩 전역 적용

### v1.1
- ✅ DB export 기능 추가
- ✅ 슬랙 알림 연동
- ✅ 필터링 로직 개선 (CMS/WMS 변화량 비교)

### v1.0
- ✅ 초기 버전 (CSV 파일 비교 분석)
- ✅ 마크다운 리포트 생성
- ✅ 일치율 계산 로직

---

## 💡 Tips

1. **스케줄러 백그라운드 실행** (Windows)
   ```bash
   pythonw main.py
   ```

2. **로그 확인**
   ```bash
   tail -f logs/app_2026-02-20.log
   ```

3. **특정 날짜 파일 비교**
   - 파일명을 수동으로 지정하려면 `data_analyzer.py` 수정 필요
   - 현재는 최신 2개 자동 검색

4. **슬랙 알림 테스트**
   ```python
   from src.reporter.slack_notifier import send_to_slack
   send_to_slack("테스트 메시지")
   ```

---

## 📞 문의

프로젝트 관련 문의: [이슈 등록](https://github.com/your-repo/issues)
