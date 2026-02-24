import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from config.path_helper import get_app_dir, resolve_data_path, ensure_dir

# config 파일 로드 (개발/운영)
# 우선순위: config.local.env > config.env
if not getattr(sys, 'frozen', False):
    # 개발 환경 - 프로젝트 루트
    project_root = Path(__file__).resolve().parent.parent

    # 1. config.env (템플릿) 로드
    config_file = project_root / "config.env"
    if config_file.exists():
        load_dotenv(config_file)

    # 2. config.local.env (실제 값) 우선 로드 (덮어쓰기)
    local_config_file = project_root / "config.local.env"
    if local_config_file.exists():
        load_dotenv(local_config_file, override=True)
        print(f"[설정] config.local.env 로드됨")
    else:
        print(f"[경고] config.local.env 파일이 없습니다. config.env의 예시값이 사용됩니다.")
else:
    # 빌드 환경 - 실행 파일 옆의 config.env만 사용
    app_dir = Path(sys.executable).parent
    config_file = app_dir / "config.env"
    if config_file.exists():
        load_dotenv(config_file)
    else:
        print(f"[경고] config.env 파일이 없습니다: {config_file}")

# Base paths
BASE_DIR = get_app_dir()  # 실행 파일 기준
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

# DB Export 출력 경로 (환경변수 또는 기본값)
# 기본값: 실행 파일 폴더의 output/daily-stock
DB_EXPORT_OUTPUT_DIR = resolve_data_path(
    os.getenv("DB_EXPORT_OUTPUT_DIR", "output/daily-stock")
)
# 폴더 자동 생성
ensure_dir(DB_EXPORT_OUTPUT_DIR)

# Scheduler settings
SCHEDULE_DOWNLOAD_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_DOWNLOAD_INTERVAL_MINUTES", 60))
SCHEDULE_REPORT_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_REPORT_INTERVAL_MINUTES", 120))

# Scheduler cron settings
# DB Export 시간 (기본: 오전 8시)
DB_EXPORT_HOUR = int(os.getenv("DB_EXPORT_HOUR", "8"))
DB_EXPORT_MINUTE = int(os.getenv("DB_EXPORT_MINUTE", "0"))

# Report 생성 시간 (기본: 오전 8시 30분)
REPORT_HOUR = int(os.getenv("REPORT_HOUR", "8"))
REPORT_MINUTE = int(os.getenv("REPORT_MINUTE", "30"))

# 하위 호환성을 위한 별칭
SCHEDULE_DOWNLOAD_CRON_HOUR = str(DB_EXPORT_HOUR)
SCHEDULE_DOWNLOAD_CRON_MINUTE = str(DB_EXPORT_MINUTE)
SCHEDULE_REPORT_CRON_HOUR = str(REPORT_HOUR)
SCHEDULE_REPORT_CRON_MINUTE = str(REPORT_MINUTE)

# Data source settings (e.g. API or FTP)
DATA_SOURCE_URL = os.getenv("DATA_SOURCE_URL", "")
DATA_SOURCE_API_KEY = os.getenv("DATA_SOURCE_API_KEY", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_ROTATION = os.getenv("LOG_ROTATION", "1 day")
LOG_RETENTION = os.getenv("LOG_RETENTION", "30 days")



