"""제목/내용 중복 방지 모듈 - 기존 포스트와 신규 글의 중복을 검사한다."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.core.logger import setup_logger

logger = setup_logger("dedup_checker")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PUBLISHED_TITLES_FILE = DATA_DIR / "published_titles.json"
BLOG_INDEX_FILE = DATA_DIR / "blog_posts_index.json"


def _load_published_titles() -> list[dict]:
    """발행된 제목 DB를 로드한다."""
    if PUBLISHED_TITLES_FILE.exists():
        return json.loads(PUBLISHED_TITLES_FILE.read_text(encoding="utf-8"))
    return []


def _save_published_titles(titles: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_TITLES_FILE.write_text(
        json.dumps(titles, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_blog_index() -> list[dict]:
    """크롤링된 블로그 인덱스를 로드한다."""
    if BLOG_INDEX_FILE.exists():
        return json.loads(BLOG_INDEX_FILE.read_text(encoding="utf-8"))
    return []


def _normalize(text: str) -> str:
    """비교를 위해 텍스트를 정규화한다."""
    text = text.lower().strip()
    text = re.sub(r"[^\w가-힣\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _similarity(a: str, b: str) -> float:
    """두 문자열의 유사도를 계산한다 (0.0~1.0)."""
    a_norm = _normalize(a)
    b_norm = _normalize(b)

    if a_norm == b_norm:
        return 1.0

    # 단어 단위 Jaccard 유사도
    words_a = set(a_norm.split())
    words_b = set(b_norm.split())

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def check_title_duplicate(new_title: str, threshold: float = 0.6) -> dict | None:
    """새 제목이 기존 포스트와 중복되는지 검사한다.

    Args:
        new_title: 검사할 제목
        threshold: 유사도 임계값 (0.6 = 60% 이상 유사하면 중복)

    Returns:
        중복인 경우 기존 포스트 정보, 아니면 None
    """
    # 크롤링 DB + 발행 DB 모두 검사
    all_titles = []

    for post in _load_blog_index():
        all_titles.append({"title": post.get("title", ""), "source": "blog"})

    for post in _load_published_titles():
        all_titles.append({"title": post.get("title", ""), "source": "generated"})

    for existing in all_titles:
        sim = _similarity(new_title, existing["title"])
        if sim >= threshold:
            logger.warning(
                "제목 중복 감지: '%s' ↔ '%s' (유사도: %.0f%%)",
                new_title[:30], existing["title"][:30], sim * 100,
            )
            return {
                "existing_title": existing["title"],
                "similarity": sim,
                "source": existing["source"],
            }

    return None


def check_keyword_duplicate(keyword: str) -> bool:
    """키워드가 최근에 사용되었는지 검사한다."""
    published = _load_published_titles()

    for post in published[-9:]:  # 최근 9개 (3일치)만 검사
        if _normalize(keyword) == _normalize(post.get("keyword", "")):
            logger.warning("키워드 중복: '%s' (최근 9개 내 사용됨)", keyword)
            return True

    return False


def register_published(title: str, keyword: str, date: str = "") -> None:
    """발행된 포스트를 DB에 등록한다."""
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")

    titles = _load_published_titles()
    titles.append({
        "title": title,
        "keyword": keyword,
        "date": date,
    })

    # 최대 500개 유지
    if len(titles) > 500:
        titles = titles[-500:]

    _save_published_titles(titles)
    logger.info("발행 등록: '%s' (키워드: %s)", title[:30], keyword)


def filter_unique_keywords(keywords: list[str]) -> list[str]:
    """중복되지 않은 키워드만 필터링한다."""
    unique = []
    for kw in keywords:
        if not check_keyword_duplicate(kw):
            dup = check_title_duplicate(kw, threshold=0.5)
            if not dup:
                unique.append(kw)
            else:
                logger.info("키워드 스킵 (유사 포스트 존재): '%s'", kw)
        else:
            logger.info("키워드 스킵 (최근 사용): '%s'", kw)

    logger.info("중복 필터: %d개 → %d개 통과", len(keywords), len(unique))
    return unique
