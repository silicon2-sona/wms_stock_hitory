import sys
from loguru import logger

# Windows 터미널 cp949 환경에서 UTF-8 출력 가능하도록 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def run_db_export_job():
    """스케줄러에 의해 주기적으로 실행되는 일일 재고 CSV 생성 잡"""
    logger.info("=== [JOB] 일일 재고 CSV 생성 시작 ===")
    try:
        from src.downloader.daily_stock_exporter import export_stock_data
        export_stock_data()
        logger.info("=== [JOB] 일일 재고 CSV 생성 완료 ===")
    except Exception as e:
        logger.error(f"[JOB] 일일 재고 CSV 생성 오류: {e}")
