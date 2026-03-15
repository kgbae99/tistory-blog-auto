"""내부 링크 자동 매칭 모듈 - 기존 포스트 URL과 신규 글 키워드를 매칭한다."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.logger import setup_logger

logger = setup_logger("internal_links")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CRAWLED_INDEX = DATA_DIR / "blog_posts_index.json"

# 기존 블로그 포스트 DB (URL, 제목, 관련 키워드)
BLOG_POSTS: list[dict[str, str | list[str]]] = [
    # 건강 & 웰빙
    {"url": "/530", "title": "봄만 되면 쏟아지는 졸음, 춘곤증 이렇게 이기세요", "keywords": ["춘곤증", "졸음", "봄", "피로", "수면"]},
    {"url": "/528", "title": "아침 공복에 좋은 음식, 따로 있습니다", "keywords": ["공복", "아침", "식사", "위", "건강"]},
    {"url": "/527", "title": "건강온도사가 알려주는 건강 노하우 꿀팁", "keywords": ["건강", "노하우", "꿀팁", "생활습관"]},
    {"url": "/526", "title": "몸이 가벼워지는 해독 습관, 지금 시작하세요", "keywords": ["해독", "디톡스", "다이어트", "체중"]},
    {"url": "/525", "title": "소화 잘되는 식단, 이렇게 구성해보세요", "keywords": ["소화", "식단", "위장", "장건강"]},
    {"url": "/523", "title": "간 건강을 위해 피해야 할 음식은?", "keywords": ["간", "간건강", "음식", "해독", "알코올"]},
    {"url": "/522", "title": "두통 잦다면 이 음식 꼭 드셔보세요", "keywords": ["두통", "편두통", "음식", "영양"]},
    {"url": "/521", "title": "매일 먹는 아침 식사가 건강을 바꿉니다", "keywords": ["아침식사", "건강", "식단", "혈당"]},
    {"url": "/520", "title": "노화를 늦추는 비밀, 바로 이 음식", "keywords": ["노화", "항산화", "안티에이징", "식품"]},
    {"url": "/519", "title": "당뇨 걱정 줄이는 식단의 핵심은 이것", "keywords": ["당뇨", "혈당", "식단", "탄수화물"]},
    {"url": "/493", "title": "1일 1식단, 이걸로 건강 지켜냅니다", "keywords": ["식단", "다이어트", "건강식", "체중관리"]},
    {"url": "/491", "title": "뼈가 약해졌다면 지금 꼭 챙기세요", "keywords": ["뼈", "골다공증", "칼슘", "비타민D", "관절"]},
    {"url": "/16", "title": "관절에 좋은 음식 BEST 7", "keywords": ["관절", "음식", "연골", "무릎", "콜라겐"]},
    {"url": "/28", "title": "혈압 낮추는 식단 가이드", "keywords": ["혈압", "고혈압", "식단", "나트륨", "칼륨"]},
    # 생활/뷰티
    {"url": "/524", "title": "피부가 좋아지는 생활 습관 5가지", "keywords": ["피부", "스킨케어", "생활습관", "뷰티"]},
    # 복지/정부지원
    {"url": "/500", "title": "2026년 정부 지원금 총정리", "keywords": ["정부지원", "지원금", "복지", "보조금"]},
]

BLOG_BASE_URL = "https://kgbae2369.tistory.com"


def _load_crawled_posts() -> list[dict]:
    """크롤링된 포스트 인덱스를 로드한다."""
    if CRAWLED_INDEX.exists():
        data = json.loads(CRAWLED_INDEX.read_text(encoding="utf-8"))
        logger.info("크롤링 DB 로드: %d개 포스트", len(data))
        return data
    return []


def _get_all_posts() -> list[dict]:
    """크롤링 DB + 하드코딩 DB를 합쳐서 반환한다."""
    crawled = _load_crawled_posts()
    if crawled:
        # 크롤링 DB가 있으면 우선 사용
        merged = {p["url"]: p for p in BLOG_POSTS}
        for cp in crawled:
            url = cp.get("url", "")
            if url not in merged:
                merged[url] = {
                    "url": url,
                    "title": cp.get("title", ""),
                    "keywords": cp.get("keywords", []),
                }
        return list(merged.values())
    return BLOG_POSTS


def find_related_posts(
    keyword: str,
    exclude_urls: list[str] | None = None,
    max_results: int = 2,
) -> list[dict[str, str]]:
    """키워드와 관련된 기존 포스트를 찾아 반환한다.

    Args:
        keyword: 현재 글의 포커스 키워드
        exclude_urls: 제외할 URL 리스트
        max_results: 최대 반환 개수

    Returns:
        [{"url": "전체URL", "title": "제목"}, ...]
    """
    if exclude_urls is None:
        exclude_urls = []

    keyword_lower = keyword.lower()
    keyword_parts = keyword_lower.replace(",", " ").split()

    all_posts = _get_all_posts()
    scored: list[tuple[int, dict]] = []

    for post in all_posts:
        if post["url"] in exclude_urls:
            continue

        score = 0
        post_keywords = [k.lower() for k in post["keywords"]]
        post_title = post["title"].lower()

        # 키워드 매칭 점수
        for part in keyword_parts:
            for pk in post_keywords:
                if part in pk or pk in part:
                    score += 3
            if part in post_title:
                score += 2

        # 건강 관련 범용 매칭
        health_terms = ["건강", "식단", "음식", "영양", "운동", "비타민"]
        for term in health_terms:
            if term in keyword_lower and term in " ".join(post_keywords):
                score += 1

        # 같은 카테고리 약한 매칭 (최소 1개 보장)
        if score == 0:
            common_health = ["건강", "음식", "식단", "영양"]
            for term in common_health:
                if term in " ".join(post_keywords):
                    score += 0.5
                    break

        if score > 0:
            scored.append((score, post))

    # 점수 높은 순 정렬
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for _, post in scored[:max_results]:
        results.append({
            "url": f"{BLOG_BASE_URL}{post['url']}",
            "title": post["title"],
        })

    logger.info(
        "내부 링크 매칭: '%s' → %d개 (%s)",
        keyword,
        len(results),
        ", ".join(r["title"][:15] + "..." for r in results),
    )
    return results


def generate_internal_link_html(related_posts: list[dict[str, str]]) -> str:
    """내부 링크 HTML을 생성한다."""
    if not related_posts:
        return ""

    links = []
    for post in related_posts:
        links.append(
            f'<a style="color: #c0392b; text-decoration: underline;" '
            f'href="{post["url"]}">{post["title"]}</a>'
        )
    return " / ".join(links)
