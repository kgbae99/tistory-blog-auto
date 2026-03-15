"""키워드 기반 이미지 자동 매칭 - GitHub 호스팅 고정 이미지 63개."""

from __future__ import annotations

import hashlib

from src.core.logger import setup_logger

logger = setup_logger("image_search")

_BASE = "https://raw.githubusercontent.com/kgbae99/tistory-blog-auto/master/assets/images"

# 전체 이미지 풀 63개 (카테고리별 분류, 중복 없음)
_IMAGES: list[tuple[str, str]] = [
    # 건강 (15개)
    ("health_01.jpg", "건강"), ("health_02.jpg", "건강"), ("health_03.jpg", "건강"),
    ("health_04.jpg", "건강"), ("health_05.jpg", "건강"), ("health_06.jpg", "건강"),
    ("health_07.jpg", "건강"), ("health_08.jpg", "건강"), ("health_09.jpg", "건강"),
    ("health_10.jpg", "건강"), ("health_11.jpg", "건강"), ("health_12.jpg", "건강"),
    ("health_13.jpg", "건강"), ("health_14.jpg", "건강"), ("health_15.jpg", "건강"),
    # 음식 (15개)
    ("food_01.jpg", "음식"), ("food_02.jpg", "음식"), ("food_03.jpg", "음식"),
    ("food_04.jpg", "음식"), ("food_05.jpg", "음식"), ("food_06.jpg", "음식"),
    ("food_07.jpg", "음식"), ("food_08.jpg", "음식"), ("food_09.jpg", "음식"),
    ("food_10.jpg", "음식"), ("food_11.jpg", "음식"), ("food_12.jpg", "음식"),
    ("food_14.jpg", "음식"), ("food_15.jpg", "음식"),
    # 운동 (7개)
    ("exercise_01.jpg", "운동"), ("exercise_02.jpg", "운동"), ("exercise_03.jpg", "운동"),
    ("exercise_04.jpg", "운동"), ("exercise_06.jpg", "운동"), ("exercise_07.jpg", "운동"),
    ("exercise_09.jpg", "운동"),
    # 자연/봄 (5개)
    ("spring_01.jpg", "봄"), ("spring_02.jpg", "봄"),
    ("nature_01.jpg", "봄"), ("nature_02.jpg", "봄"), ("nature_03.jpg", "봄"),
    # 피부/뷰티 (7개)
    ("skin_01.jpg", "피부"), ("skin_02.jpg", "피부"), ("skin_03.jpg", "피부"),
    ("skin_04.jpg", "피부"), ("skin_05.jpg", "피부"),
    ("beauty_01.jpg", "피부"), ("beauty_02.jpg", "피부"),
    # 수면/휴식 (5개)
    ("tired_01.jpg", "피곤"), ("sleep_01.jpg", "수면"),
    ("sleep_02.jpg", "수면"), ("sleep_03.jpg", "수면"), ("rest_01.jpg", "수면"),
    # 영양제 (3개)
    ("vitamin_01.jpg", "영양제"), ("vitamin_02.jpg", "영양제"), ("vitamin_03.jpg", "영양제"),
    # 알레르기/미세먼지 (3개)
    ("allergy_01.jpg", "알레르기"), ("allergy_02.jpg", "알레르기"), ("dust_01.jpg", "미세먼지"),
    # 다이어트 (4개)
    ("diet_01.jpg", "다이어트"), ("diet_02.jpg", "다이어트"),
    ("diet_03.jpg", "다이어트"), ("diet_04.jpg", "다이어트"),
]

# 카테고리별 인덱스
IMAGE_POOL: dict[str, list[str]] = {}
_ALL_URLS: list[str] = []
for _fname, _cat in _IMAGES:
    url = f"{_BASE}/{_fname}"
    _ALL_URLS.append(url)
    IMAGE_POOL.setdefault(_cat, []).append(url)
IMAGE_POOL["기본"] = list(_ALL_URLS)

# 키워드 → 카테고리 매핑
KEYWORD_CATEGORY_MAP: dict[str, list[str]] = {
    "알레르기": ["알레르기", "건강"], "꽃가루": ["알레르기", "봄"],
    "춘곤증": ["피곤", "봄"], "졸음": ["피곤", "수면"],
    "미세먼지": ["미세먼지", "건강"], "황사": ["미세먼지", "건강"],
    "다이어트": ["다이어트", "음식"], "식단": ["음식", "건강"],
    "비타민": ["영양제", "건강"], "영양제": ["영양제", "건강"],
    "운동": ["운동", "건강"], "피부": ["피부", "건강"],
    "스킨케어": ["피부"], "보습": ["피부"],
    "수면": ["수면", "피곤"], "숙면": ["수면", "피곤"],
    "음식": ["음식", "건강"], "면역": ["건강", "음식"],
    "관절": ["운동", "건강"], "혈압": ["건강", "음식"],
    "당뇨": ["건강", "음식"], "간": ["건강", "음식"],
    "해독": ["건강", "다이어트"], "봄": ["봄", "건강"],
    "여름": ["건강", "운동"], "피로": ["피곤", "건강"],
    "다리": ["운동", "건강"], "뼈": ["건강", "운동"],
    "눈": ["건강", "영양제"], "장": ["건강", "음식"],
    "탈모": ["건강", "피부"], "체력": ["운동", "건강"],
    "스트레스": ["수면", "건강"], "환절기": ["봄", "건강"],
    "노화": ["피부", "건강"], "콜레스테롤": ["음식", "건강"],
    "혈관": ["건강", "음식"], "항산화": ["음식", "건강"],
    "단백질": ["음식", "운동"], "프로바이오틱스": ["영양제", "음식"],
}


def get_images_for_keyword(keyword: str, count: int = 8) -> list[str]:
    """키워드에 맞는 중복 없는 이미지 URL 리스트를 반환한다.

    키워드의 해시값으로 전체 풀에서 시작점을 결정하고,
    관련 카테고리 이미지를 우선 배치한 뒤 순차 선택한다.
    """
    keyword_lower = keyword.lower()

    # 키워드 해시 → 시작 오프셋 (매 키워드마다 다른 위치에서 시작)
    kw_hash = int(hashlib.md5(keyword.encode()).hexdigest(), 16)
    offset = kw_hash % len(_ALL_URLS)

    # 관련 카테고리 찾기
    matched_categories: list[str] = []
    for term, categories in KEYWORD_CATEGORY_MAP.items():
        if term in keyword_lower:
            matched_categories.extend(categories)
    if not matched_categories:
        matched_categories = ["기본"]

    # 관련 카테고리에서 2개만 우선 (나머지는 전체에서)
    related: list[str] = []
    seen: set[str] = set()
    for cat in matched_categories[:2]:  # 상위 2개 카테고리만
        pool = IMAGE_POOL.get(cat, [])
        start = offset % max(len(pool), 1)
        picked = 0
        for j in range(len(pool)):
            img = pool[(start + j) % len(pool)]
            if img not in seen:
                seen.add(img)
                related.append(img)
                picked += 1
            if picked >= 2:  # 카테고리당 2개만
                break

    # 나머지는 전체 풀에서 offset부터 순환 (최대 다양성)
    others: list[str] = []
    for j in range(len(_ALL_URLS)):
        img = _ALL_URLS[(offset + j) % len(_ALL_URLS)]
        if img not in seen:
            seen.add(img)
            others.append(img)

    all_candidates = related + others
    result = all_candidates[:count]

    logger.info("이미지 매칭: '%s' → %d개 (풀: %d개, offset: %d)", keyword, len(result), len(_ALL_URLS), offset)
    return result


def get_header_image(keyword: str) -> str:
    images = get_images_for_keyword(keyword, count=1)
    return images[0] if images else _ALL_URLS[0]
