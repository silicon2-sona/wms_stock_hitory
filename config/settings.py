import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

# Scheduler settings
SCHEDULE_DOWNLOAD_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_DOWNLOAD_INTERVAL_MINUTES", 60))
SCHEDULE_REPORT_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_REPORT_INTERVAL_MINUTES", 120))

# Scheduler cron (alternative to interval)
# e.g. every day at 08:00
SCHEDULE_DOWNLOAD_CRON_HOUR = os.getenv("SCHEDULE_DOWNLOAD_CRON_HOUR", "8")
SCHEDULE_DOWNLOAD_CRON_MINUTE = os.getenv("SCHEDULE_DOWNLOAD_CRON_MINUTE", "0")

SCHEDULE_REPORT_CRON_HOUR = os.getenv("SCHEDULE_REPORT_CRON_HOUR", "9")
SCHEDULE_REPORT_CRON_MINUTE = os.getenv("SCHEDULE_REPORT_CRON_MINUTE", "0")

# Data source settings (e.g. API or FTP)
DATA_SOURCE_URL = os.getenv("DATA_SOURCE_URL", "")
DATA_SOURCE_API_KEY = os.getenv("DATA_SOURCE_API_KEY", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_ROTATION = os.getenv("LOG_ROTATION", "1 day")
LOG_RETENTION = os.getenv("LOG_RETENTION", "30 days")



