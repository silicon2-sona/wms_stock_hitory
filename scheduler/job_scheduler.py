from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config.settings import (
    SCHEDULE_DOWNLOAD_INTERVAL_MINUTES,
    SCHEDULE_REPORT_INTERVAL_MINUTES,
)
from scheduler.jobs.report_job import run_report_job
from scheduler.jobs.db_export_job import run_db_export_job


def create_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    # 일일 재고 CSV 생성: 매일 오전 8시
    scheduler.add_job(
        run_db_export_job,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily_stock_csv_job",
        name="일일 재고 CSV 생성",
        replace_existing=True,
    )

    # 레포트 잡: cron 방식 (매일 오전 8시 10분)
    scheduler.add_job(
        run_report_job,
        trigger=CronTrigger(hour=8, minute=30),
        id="report_job",
        name="데이터 분석/레포팅",
        replace_existing=True,
    )

    # 참고: interval 방식으로 변경하려면:
    # scheduler.add_job(run_report_job, IntervalTrigger(minutes=SCHEDULE_REPORT_INTERVAL_MINUTES), ...)

    logger.info("스케줄러 잡 등록 완료")
    return scheduler
