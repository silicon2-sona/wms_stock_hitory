from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config.settings import (
    DB_EXPORT_HOUR,
    DB_EXPORT_MINUTE,
    REPORT_HOUR,
    REPORT_MINUTE,
)
from scheduler.jobs.report_job import run_report_job
from scheduler.jobs.db_export_job import run_db_export_job


def create_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    # 일일 재고 CSV 생성 (환경변수에서 시간 설정)
    scheduler.add_job(
        run_db_export_job,
        trigger=CronTrigger(hour=DB_EXPORT_HOUR, minute=DB_EXPORT_MINUTE),
        id="daily_stock_csv_job",
        name=f"일일 재고 CSV 생성 (매일 {DB_EXPORT_HOUR:02d}:{DB_EXPORT_MINUTE:02d})",
        replace_existing=True,
    )

    # 레포트 잡 (환경변수에서 시간 설정)
    scheduler.add_job(
        run_report_job,
        trigger=CronTrigger(hour=REPORT_HOUR, minute=REPORT_MINUTE),
        id="report_job",
        name=f"데이터 분석/레포팅 (매일 {REPORT_HOUR:02d}:{REPORT_MINUTE:02d})",
        replace_existing=True,
    )

    logger.info("스케줄러 잡 등록 완료")
    return scheduler
