"""트렌드 분석 모듈 - 계절성 키워드 및 추천 주제 관리."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.core.logger import setup_logger

logger = setup_logger("trend_analyzer")

# 월별 건강/생활/뷰티 시즈널 키워드
SEASONAL_KEYWORDS: dict[int, dict[str, list[str]]] = {
    1: {
        "건강": ["면역력 강화", "감기 예방", "겨울 운동", "비타민 추천"],
        "뷰티": ["건조피부 관리", "겨울 보습 크림", "핸드크림 추천"],
        "생활": ["신년 목표", "가습기 추천", "난방비 절약"],
    },
    2: {
        "건강": ["면역력 높이는 음식", "환절기 건강", "꽃샘추위 대비"],
        "뷰티": ["봄맞이 스킨케어", "보습 세럼", "각질 관리"],
        "생활": ["봄맞이 대청소", "미세먼지 대비", "공기청정기"],
    },
    3: {
        "건강": ["꽃가루 알레르기", "춘곤증 극복", "봄나물 효능", "황사 건강"],
        "뷰티": ["자외선 차단제 추천", "봄 메이크업", "톤업 크림"],
        "생활": ["미세먼지 마스크", "봄 인테리어", "환기 방법"],
    },
    4: {
        "건강": ["봄철 운동", "다이어트 시작", "알레르기 비염", "피로 회복"],
        "뷰티": ["선크림 추천", "모공 관리", "수분 크림"],
        "생활": ["봄옷 정리", "제습기 준비", "벌레 퇴치"],
    },
    5: {
        "건강": ["다이어트 식단", "체력 관리", "수분 보충", "자외선 주의"],
        "뷰티": ["여름 준비 스킨케어", "바디로션", "제모"],
        "생활": ["에어컨 청소", "여름 준비", "가정의 달 선물"],
    },
    6: {
        "건강": ["여름 건강 관리", "식중독 예방", "열사병 예방"],
        "뷰티": ["선크림 SPF50", "워터프루프 메이크업", "쿨링 스킨케어"],
        "생활": ["에어컨 추천", "냉감 침구", "제습"],
    },
    7: {
        "건강": ["여름 다이어트", "열대야 수면", "식중독 주의"],
        "뷰티": ["피지 관리", "모공 축소", "썬스틱"],
        "생활": ["냉방병 예방", "여행 준비물", "모기 퇴치"],
    },
    8: {
        "건강": ["면역력 여름", "수분 보충", "눈 건강"],
        "뷰티": ["자외선 후 케어", "수분팩", "바디스크럽"],
        "생활": ["가을맞이 준비", "에어컨 관리", "여름 정리"],
    },
    9: {
        "건강": ["환절기 감기", "비타민 보충", "가을 운동", "탈모 관리"],
        "뷰티": ["가을 스킨케어", "보습 전환", "안티에이징"],
        "생활": ["환기 관리", "가을 인테리어", "추석 선물"],
    },
    10: {
        "건강": ["면역력 강화 식품", "관절 건강", "독감 예방접종"],
        "뷰티": ["보습 크림 추천", "립밤", "핸드크림"],
        "생활": ["난방 준비", "가습기 청소", "겨울 이불"],
    },
    11: {
        "건강": ["겨울 건강 관리", "비타민D", "관절 보호", "독감 예방"],
        "뷰티": ["겨울 보습", "바디버터", "건조 두피"],
        "생활": ["블랙프라이데이", "겨울 가전", "연말 선물"],
    },
    12: {
        "건강": ["겨울 면역력", "감기약 추천", "관절 건강"],
        "뷰티": ["크리스마스 코스메틱", "겨울 립케어", "올인원"],
        "생활": ["연말 정리", "새해 준비", "송년회 선물"],
    },
}


@dataclass
class TrendKeyword:
    """트렌드 키워드 데이터."""

    keyword: str
    category: str
    search_volume: str  # 높음, 중간, 낮음
    competition: str  # 높음, 중간, 낮음
    is_seasonal: bool
    peak_month: int | None = None


@dataclass
class TrendReport:
    """트렌드 분석 리포트."""

    date: str
    current_keywords: list[TrendKeyword]
    upcoming_keywords: list[TrendKeyword]
    recommended_topics: list[str]


def get_seasonal_keywords(month: int | None = None) -> dict[str, list[str]]:
    """현재 월의 시즈널 키워드를 반환한다."""
    if month is None:
        month = datetime.now().month
    return SEASONAL_KEYWORDS.get(month, {})


def get_upcoming_keywords(month: int | None = None) -> dict[str, list[str]]:
    """다음 달 시즈널 키워드를 반환한다 (선점 전략)."""
    if month is None:
        month = datetime.now().month
    next_month = month % 12 + 1
    return SEASONAL_KEYWORDS.get(next_month, {})


def generate_weekly_topics(month: int | None = None) -> list[dict[str, str]]:
    """주간 포스트 주제를 생성한다."""
    current = get_seasonal_keywords(month)
    upcoming = get_upcoming_keywords(month)

    topics = []
    days = ["월", "화", "수", "목", "금", "토", "일"]

    all_keywords = []
    for cat_keywords in current.values():
        all_keywords.extend(cat_keywords)
    for cat_keywords in upcoming.values():
        all_keywords.extend(cat_keywords[:1])  # 다음달 키워드 1개씩 선점

    for i, day in enumerate(days):
        if i < len(all_keywords):
            keyword = all_keywords[i]
            topics.append({"day": day, "keyword": keyword, "type": "시즈널"})
        else:
            topics.append({"day": day, "keyword": "에버그린 주제", "type": "상시"})

    logger.info("주간 %d개 주제 생성 완료", len(topics))
    return topics


def load_trending_keywords_from_config() -> dict[str, list[str]]:
    """settings.yaml에서 트렌드 키워드를 로드한다."""
    from src.core.config import CONFIG_DIR

    settings_path = CONFIG_DIR / "settings.yaml"
    if not settings_path.exists():
        return {}

    import yaml

    with open(settings_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("trending_keywords", {})


def get_best_keyword_for_today(exclude: list[str] | None = None) -> str:
    """오늘 발행에 최적인 키워드를 선택한다.

    Args:
        exclude: 제외할 키워드 리스트 (같은 날 중복 방지)
    """
    if exclude is None:
        exclude = []

    # 모든 키워드 풀 구성
    all_keywords: list[str] = []

    # 1. settings.yaml 트렌드 키워드 우선
    trending = load_trending_keywords_from_config()
    for group in ["immediate", "beauty_2026", "evergreen"]:
        all_keywords.extend(trending.get(group, []))

    # 2. 시즌 키워드 추가
    seasonal = get_seasonal_keywords()
    for cat_keywords in seasonal.values():
        all_keywords.extend(cat_keywords)

    # 중복 제거 (순서 유지)
    seen: set[str] = set()
    unique_keywords = []
    for kw in all_keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    # 이미 선택된 키워드 제외
    available = [kw for kw in unique_keywords if kw not in exclude]
    if not available:
        available = unique_keywords

    # 날짜 + exclude 길이 기반으로 다른 키워드 선택
    day_of_year = datetime.now().timetuple().tm_yday
    idx = (day_of_year + len(exclude)) % len(available)
    selected = available[idx]

    logger.info("키워드 선택: '%s' (풀: %d개, 제외: %d개)", selected, len(available), len(exclude))
    return selected
