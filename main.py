import sys
from pathlib import Path
from loguru import logger
from config.settings import LOGS_DIR, LOG_LEVEL, LOG_ROTATION, LOG_RETENTION
from scheduler.job_scheduler import create_scheduler

# Windows 터미널 cp949 환경에서 UTF-8 출력 가능하도록 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level=LOG_LEVEL, colorize=True,
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
    logger.add(
        LOGS_DIR / "app_{time:YYYY-MM-DD}.log",
        level=LOG_LEVEL,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        encoding="utf-8",
    )


def main():
    setup_logging()

    # 명령줄 인자 확인
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        # DB 데이터 내보내기 모드
        logger.info("일일 재고 CSV 생성 시작")
        from src.downloader.daily_stock_exporter import export_stock_data
        export_stock_data()
        logger.info("일일 재고 CSV 생성 완료")
        return

    # 기본 모드: 스케줄러 실행
    logger.info("WMS 재고 이력 스케줄링 서비스 시작")

    scheduler = create_scheduler()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러 종료")


if __name__ == "__main__":
    main()
