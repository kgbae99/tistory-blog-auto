"""실시간 트렌드 키워드 자동 선정 - 구글/네이버 트렌드 기반."""

from __future__ import annotations

import re

import requests

from src.core.logger import setup_logger

logger = setup_logger("realtime_trends")

# 블로그 주제 필터 (건강/생활/뷰티만 선별)
TOPIC_FILTERS = [
    "건강", "다이어트", "영양", "비타민", "운동", "식단", "면역",
    "피부", "스킨케어", "뷰티", "화장품", "선크림",
    "알레르기", "미세먼지", "감기", "독감", "수면", "스트레스",
    "혈압", "당뇨", "관절", "눈", "간", "위", "장",
    "음식", "효능", "좋은", "나쁜", "추천", "방법",
    "봄", "여름", "가을", "겨울", "환절기",
    "정부지원", "보조금", "지원금", "복지",
    "생활", "절약", "꿀팁",
]


def get_google_trending_searches() -> list[str]:
    """구글 실시간 인기 검색어를 가져온다 (한국)."""
    try:
        url = "https://trends.google.co.kr/trends/trendingsearches/daily/rss?geo=KR"
        resp = requests.get(url, timeout=10)
        titles = re.findall(r"<title>([^<]+)</title>", resp.text)
        # 첫 번째는 RSS 피드 제목이므로 제외
        trends = [t.strip() for t in titles[1:] if t.strip()]
        logger.info("구글 트렌드: %d개 인기 검색어", len(trends))
        return trends
    except Exception as e:
        logger.warning("구글 트렌드 실패: %s", e)
        return []


def get_naver_realtime_keywords() -> list[str]:
    """네이버 데이터랩 인기 검색어를 가져온다."""
    try:
        url = "https://www.naver.com"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        # 실시간 검색어는 네이버에서 2021년에 폐지됨
        # 대신 자동완성에서 건강 관련 트렌드 추출
        health_seeds = ["봄철 건강", "다이어트", "피부관리", "면역력", "영양제 추천"]
        trends = []

        for seed in health_seeds:
            try:
                ac_url = "https://ac.search.naver.com/nx/ac"
                params = {"q": seed, "con": 1, "frm": "nv", "ans": 2, "r_format": "json", "r_enc": "UTF-8"}
                ac_resp = requests.get(ac_url, params=params, timeout=5)
                data = ac_resp.json()
                for group in data.get("items", []):
                    for item in group:
                        if isinstance(item, list) and item:
                            trends.append(item[0])
            except Exception:
                pass

        logger.info("네이버 트렌드: %d개 키워드", len(trends))
        return trends
    except Exception as e:
        logger.warning("네이버 트렌드 실패: %s", e)
        return []


def filter_health_topics(keywords: list[str]) -> list[str]:
    """건강/생활/뷰티 관련 키워드만 필터링한다."""
    filtered = []
    for kw in keywords:
        kw_lower = kw.lower()
        for topic in TOPIC_FILTERS:
            if topic in kw_lower:
                filtered.append(kw)
                break
    return filtered


def get_trending_blog_keywords(count: int = 10) -> list[dict]:
    """블로그에 적합한 트렌드 키워드를 선정한다."""
    # 구글 + 네이버 트렌드 수집
    google_trends = get_google_trending_searches()
    naver_trends = get_naver_realtime_keywords()

    all_trends = google_trends + naver_trends

    # 건강/생활 주제 필터
    health_keywords = filter_health_topics(all_trends)

    # 중복 제거
    seen: set[str] = set()
    unique = []
    for kw in health_keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    # 롱테일 키워드로 변환 (블로그 최적화)
    blog_keywords = []
    for kw in unique[:count]:
        expanded = _expand_to_blog_keyword(kw)
        blog_keywords.append({
            "original": kw,
            "blog_keyword": expanded,
            "source": "google" if kw in google_trends else "naver",
        })

    logger.info("블로그 키워드 %d개 선정 (구글 %d + 네이버 %d)", len(blog_keywords), len(google_trends), len(naver_trends))
    return blog_keywords


def _expand_to_blog_keyword(keyword: str) -> str:
    """짧은 키워드를 블로그 포스트에 적합한 롱테일로 확장한다."""
    expansions = {
        "다이어트": "다이어트 식단 구성법",
        "비타민": "비타민 효능과 올바른 섭취법",
        "면역력": "면역력 높이는 음식과 생활습관",
        "피부": "피부 좋아지는 생활 습관",
        "혈압": "혈압 낮추는 식단과 운동법",
        "당뇨": "당뇨 예방을 위한 식단 관리법",
        "수면": "수면 질 높이는 방법",
        "스트레스": "스트레스 해소에 좋은 방법",
        "관절": "관절 건강에 좋은 음식과 운동",
    }

    for key, expanded in expansions.items():
        if key in keyword and len(keyword) <= len(key) + 3:
            return expanded

    # 이미 충분히 긴 경우 그대로 반환
    if len(keyword) >= 8:
        return keyword

    # 짧은 경우 "효능", "방법", "추천" 등 추가
    suffixes = ["효능과 올바른 섭취법", "관리법", "추천 방법"]
    return f"{keyword} {suffixes[len(keyword) % len(suffixes)]}"


def select_daily_keywords(count: int = 3) -> list[str]:
    """오늘 포스팅할 키워드 3개를 자동 선정한다."""
    trending = get_trending_blog_keywords(count=count * 2)

    if len(trending) >= count:
        return [t["blog_keyword"] for t in trending[:count]]

    # 트렌드가 부족하면 시즌 키워드로 보충
    from src.content.trend_analyzer import get_best_keyword_for_today
    result = [t["blog_keyword"] for t in trending]
    exclude = list(result)

    while len(result) < count:
        kw = get_best_keyword_for_today(exclude=exclude)
        result.append(kw)
        exclude.append(kw)

    logger.info("오늘의 키워드: %s", result)
    return result
