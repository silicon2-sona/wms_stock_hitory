from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config.settings import (
    SCHEDULE_DOWNLOAD_INTERVAL_MINUTES,
    SCHEDULE_REPORT_INTERVAL_MINUTES,
)
from scheduler.jobs.download_job import run_download_job
from scheduler.jobs.report_job import run_report_job
from scheduler.jobs.db_export_job import run_db_export_job


def create_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    # DB export 잡: 20분 간격
    scheduler.add_job(
        run_db_export_job,
        trigger=IntervalTrigger(minutes=20),
        id="db_export_job",
        name="DB 데이터 export",
        replace_existing=True,
    )

    # 다운로드 잡: interval 방식
    scheduler.add_job(
        run_download_job,
        trigger=IntervalTrigger(minutes=SCHEDULE_DOWNLOAD_INTERVAL_MINUTES),
        id="download_job",
        name="데이터 다운로드",
        replace_existing=True,
    )

    # 레포트 잡: interval 방식
    scheduler.add_job(
        run_report_job,
        trigger=IntervalTrigger(minutes=SCHEDULE_REPORT_INTERVAL_MINUTES),
        id="report_job",
        name="데이터 분석/레포팅",
        replace_existing=True,
    )

    # 필요 시 cron 방식으로 변경:
    # scheduler.add_job(run_report_job, CronTrigger(hour=9, minute=0), ...)

    logger.info("스케줄러 잡 등록 완료")
    return scheduler
