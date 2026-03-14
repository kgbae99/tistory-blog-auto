"""발행 스케줄러 - APScheduler 기반 일일 자동 발행."""

from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.config import SchedulerConfig, load_config
from src.core.logger import setup_logger

logger = setup_logger("scheduler")


def create_scheduler(config: SchedulerConfig) -> BlockingScheduler:
    """스케줄러를 생성하고 설정한다."""
    scheduler = BlockingScheduler(timezone=config.timezone)
    return scheduler


def add_publish_job(scheduler: BlockingScheduler, config: SchedulerConfig) -> None:
    """일일 발행 작업을 스케줄러에 추가한다."""
    from scripts.daily_publish import run_daily_publish

    trigger = CronTrigger(
        hour=config.publish_hour,
        minute=config.publish_minute,
        timezone=config.timezone,
    )

    scheduler.add_job(
        run_daily_publish,
        trigger=trigger,
        id="daily_publish",
        name="일일 블로그 자동 발행",
        replace_existing=True,
    )

    logger.info(
        "일일 발행 스케줄 등록: 매일 %02d:%02d (%s)",
        config.publish_hour, config.publish_minute, config.timezone,
    )


def start_scheduler() -> None:
    """스케줄러를 시작한다."""
    config = load_config()
    scheduler = create_scheduler(config.scheduler)
    add_publish_job(scheduler, config.scheduler)

    logger.info("스케줄러 시작")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러 종료")
        scheduler.shutdown()


if __name__ == "__main__":
    start_scheduler()
