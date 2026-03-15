"""환경 설정 관리 모듈."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def _load_env() -> None:
    """Load .env file from config directory."""
    env_path = CONFIG_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()


_load_env()


@dataclass
class CoupangConfig:
    access_key: str = field(default_factory=lambda: os.getenv("COUPANG_ACCESS_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("COUPANG_SECRET_KEY", ""))
    products_per_post: int = 3


@dataclass
class TistoryConfig:
    blog_name: str = field(default_factory=lambda: os.getenv("TISTORY_BLOG_NAME", "kgbae2369"))
    blog_url: str = field(
        default_factory=lambda: os.getenv(
            "TISTORY_BLOG_URL", "https://kgbae2369.tistory.com"
        )
    )
    kakao_email: str = field(default_factory=lambda: os.getenv("KAKAO_EMAIL", ""))
    kakao_password: str = field(default_factory=lambda: os.getenv("KAKAO_PASSWORD", ""))


@dataclass
class ContentConfig:
    model: str = "gemini-2.5-flash"
    max_tokens: int = 4096
    min_word_count: int = 1500
    max_word_count: int = 3000
    language: str = "ko"
    tone: str = "친근하고 전문적인"


@dataclass
class AdsenseConfig:
    gtag_id: str = field(default_factory=lambda: os.getenv("ADSENSE_GTAG_ID", "G-SD7PEXH5NK"))
    pub_id: str = field(default_factory=lambda: os.getenv("ADSENSE_PUB_ID", ""))
    ad_slots: list[str] = field(
        default_factory=lambda: [
            os.getenv("ADSENSE_SLOT_TOP", ""),
            os.getenv("ADSENSE_SLOT_MID", ""),
            os.getenv("ADSENSE_SLOT_BOTTOM", ""),
        ]
    )
    ad_positions: list[str] = field(
        default_factory=lambda: ["after_first_h2", "after_third_h2", "before_conclusion"]
    )


@dataclass
class SchedulerConfig:
    publish_hour: int = 9
    publish_minute: int = 0
    posts_per_day: int = 1
    timezone: str = "Asia/Seoul"


@dataclass
class AppConfig:
    coupang: CoupangConfig = field(default_factory=CoupangConfig)
    tistory: TistoryConfig = field(default_factory=TistoryConfig)
    content: ContentConfig = field(default_factory=ContentConfig)
    adsense: AdsenseConfig = field(default_factory=AdsenseConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    categories: list[str] = field(
        default_factory=lambda: [
            "건강정보", "생활꿀팁", "뷰티/스킨케어",
            "식품/영양", "정부지원/복지",
        ]
    )


def load_config() -> AppConfig:
    """Load configuration from settings.yaml and environment variables."""
    settings_path = CONFIG_DIR / "settings.yaml"
    config = AppConfig()

    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if "content" in data:
            c = data["content"]
            config.content.model = c.get("model", config.content.model)
            config.content.max_tokens = c.get("max_tokens", config.content.max_tokens)
            config.content.min_word_count = c.get("min_word_count", config.content.min_word_count)
            config.content.max_word_count = c.get("max_word_count", config.content.max_word_count)

        if "coupang" in data:
            config.coupang.products_per_post = data["coupang"].get(
                "products_per_post", config.coupang.products_per_post
            )

        if "scheduler" in data:
            s = data["scheduler"]
            if "publish_time" in s:
                parts = s["publish_time"].split(":")
                config.scheduler.publish_hour = int(parts[0])
                config.scheduler.publish_minute = int(parts[1])
            config.scheduler.posts_per_day = s.get(
                "posts_per_day", config.scheduler.posts_per_day
            )

        if "blog" in data:
            config.categories = data["blog"].get("categories", config.categories)

    return config
