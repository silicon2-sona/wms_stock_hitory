# WMS Stock Scheduler

재고 일치율 변동 분석 및 자동 리포트 생성 시스템

## 📋 주요 기능

- **DB Export**: SQL Server에서 재고 데이터 추출 및 CSV 저장
- **일치율 분석**: 전일 대비 재고 일치율 변동 분석
- **자동 리포트**: 마크다운 형식의 분석 리포트 생성
- **Slack 알림**: 변동 요약 메시지 자동 전송
- **Notion 연동**: 전체 리포트를 Notion 데이터베이스에 자동 저장
- **스케줄러**: 매일 정해진 시간에 자동 실행

## 🚀 빠른 시작

### 1. 빌드

```bash
build.bat
```

`deploy` 폴더가 생성됩니다.

### 2. 설정

`config.env` 파일을 열어 DB 정보 입력:

```env
DB_HOST=your-database-host
DB_NAME=CMSGLOBAL
DB_USER=your-username
DB_PASSWORD=your-password
```

### 3. 실행

```bash
# 스케줄러 모드 (매일 자동 실행)
WMS-Stock-Scheduler.exe

# 즉시 실행 모드 (DB Export만)
WMS-Stock-Scheduler.exe export
```

### 4. 서비스 등록

배포 서버(`deploy` 폴더)를 원하는 위치에 복사한 뒤 `nassim` 명령어로 Windows 서비스에 등록하면 재부팅 후에도 자동 실행됩니다.

```powershell
nassim install WMSStockScheduler "C:\WMS-Stock-Scheduler-Deploy\WMS-Stock-Scheduler.exe"
nassim set WMSStockScheduler start auto
nassim start WMSStockScheduler
```

- `WMSStockScheduler`는 서비스 이름이므로 필요 시 다른 이름으로 변경할 수 있습니다.
- `config.env` 경로가 기본 위치가 아니라면 `nassim edit`으로 `Working directory`와 `AppDirectory`를 배포 경로로 맞춰 주세요.
- 등록 후 `nassim status WMSStockScheduler`로 정상 실행 여부를 확인합니다.

## 📁 폴더 구조

```
WMS-Stock-Scheduler-Deploy/
├── WMS-Stock-Scheduler.exe    # 실행 파일
├── config.env                 # 설정 파일
├── repository/
│   └── stock_export.sql       # SQL 쿼리
├── output/                    # 자동 생성
│   └── daily-stock/
│       ├── 2026-02/           # 월별 폴더
│       │   ├── Stock_2026-02-23_0800.csv
│       │   └── Stock_2026-02-24_0800.csv
│       └── 2026-03/
└── logs/                      # 자동 생성
    └── app_2026-02-23.log
```

## ⚙️ 설정 가이드

### 필수 설정

**데이터베이스** (`config.env`)
```env
DB_TYPE=mssql
DB_HOST=your-server.com
DB_PORT=1433
DB_NAME=CMSGLOBAL
DB_USER=username
DB_PASSWORD=password
```

**스케줄 시간**
```env
DB_EXPORT_HOUR=8         # DB Export 실행 시간
DB_EXPORT_MINUTE=0
REPORT_HOUR=8            # 리포트 생성 시간
REPORT_MINUTE=30
```

### 선택 설정

**Slack 알림**
```env
SEND_SLACK_NOTIFICATION=true
COMMON_API_PATH=https://your-api.com
SLACK_DM_RECEIVER=your-email@company.com
```

**Notion 연동**
```env
SEND_NOTION_REPORT=true
NOTION_API_TOKEN=ntn_xxxxx
NOTION_DATABASE_ID=xxxxx
```

## 💡 사용 팁

### 파일 정리

- CSV 파일은 **월별 폴더**로 자동 정리됩니다
- 최근 2개월 폴더만 검색하여 성능 최적화
- 같은 날짜의 다른 시간 파일도 비교 가능

### 로그 확인

문제 발생 시 `logs/` 폴더의 최신 로그 파일 확인:
```
logs/app_2026-02-23.log
```

### 파일명 형식

```
Stock_YYYY-MM-DD_HHMM.csv
예: Stock_2026-02-23_0800.csv
```

## 🔧 문제 해결

### DB 연결 오류

1. `config.env`의 DB 설정 확인
2. 방화벽에서 DB 포트 열림 확인
3. ODBC 드라이버 설치 확인
   - [ODBC Driver 17 for SQL Server](https://aka.ms/downloadmsodbcsql)

### CSV 파일 미생성

1. SQL 쿼리 확인: `repository/stock_export.sql`
2. DB 권한 확인 (SELECT 권한)
3. 로그 파일에서 오류 메시지 확인

### 스케줄러 미작동

1. `config.env`의 시간 설정 확인
2. 프로그램이 계속 실행 중인지 확인
3. 로그 파일 확인

## 📊 출력 예시

### CSV 파일
```csv
상품코드,상품명,CMS 재고,WMS 재고,대기 수량,일치율
P001,상품A,100,100,0,100.0
P002,상품B,50,48,2,100.0
```

### 리포트 (Markdown)
```
# 재고 일치율 변동 분석 리포트

## 개요
- 총 상품 수: 1,234개
- 변동 상품: 56개
- 평균 변동폭: 3.5%

## 변동 상품 상세
### 일치율 증가 (32개)
1. **P001** | 일치율 100.0% (+5.0%) | CMS 100 (+0) | WMS수량 100 (+5)
...
```

## 📞 지원

문제가 발생하면 로그 파일과 함께 문의하세요.

---

**버전**: 1.2
**업데이트**: 2026-02-23
