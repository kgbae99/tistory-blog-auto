"""키워드 기반 이미지 자동 매칭 - GitHub 호스팅 고정 이미지."""

from __future__ import annotations

import hashlib

from src.core.logger import setup_logger

logger = setup_logger("image_search")

# GitHub raw URL 베이스 (절대 변경되지 않는 고정 URL)
_BASE = "https://raw.githubusercontent.com/kgbae99/tistory-blog-auto/master/assets/images"

# 전체 이미지 풀 (각 이미지는 단 1회만 등록)
_IMAGES: list[tuple[str, str]] = [
    # (파일명, 카테고리)
    ("health_01.jpg", "건강"),
    ("health_02.jpg", "건강"),
    ("health_03.jpg", "건강"),
    ("health_04.jpg", "건강"),
    ("health_05.jpg", "건강"),
    ("food_01.jpg", "음식"),
    ("food_02.jpg", "음식"),
    ("food_03.jpg", "음식"),
    ("food_04.jpg", "음식"),
    ("food_05.jpg", "음식"),
    ("exercise_01.jpg", "운동"),
    ("exercise_02.jpg", "운동"),
    ("exercise_03.jpg", "운동"),
    ("exercise_04.jpg", "운동"),
    ("spring_01.jpg", "봄"),
    ("spring_02.jpg", "봄"),
    ("tired_01.jpg", "피곤"),
    ("sleep_01.jpg", "수면"),
    ("allergy_01.jpg", "알레르기"),
    ("allergy_02.jpg", "알레르기"),
    ("dust_01.jpg", "미세먼지"),
    ("vitamin_01.jpg", "영양제"),
    ("skin_01.jpg", "피부"),
    ("skin_02.jpg", "피부"),
    ("diet_01.jpg", "다이어트"),
    ("diet_02.jpg", "다이어트"),
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
    "알레르기": ["알레르기", "건강"],
    "꽃가루": ["알레르기", "봄"],
    "춘곤증": ["피곤", "봄"],
    "졸음": ["피곤", "수면"],
    "미세먼지": ["미세먼지", "건강"],
    "황사": ["미세먼지", "건강"],
    "다이어트": ["다이어트", "음식"],
    "식단": ["음식", "건강"],
    "비타민": ["영양제", "건강"],
    "영양제": ["영양제", "건강"],
    "운동": ["운동", "건강"],
    "피부": ["피부", "건강"],
    "스킨케어": ["피부"],
    "수면": ["수면", "피곤"],
    "음식": ["음식", "건강"],
    "면역": ["건강", "음식"],
    "관절": ["운동", "건강"],
    "혈압": ["건강", "음식"],
    "당뇨": ["건강", "음식"],
    "간": ["건강", "음식"],
    "해독": ["건강", "다이어트"],
    "봄": ["봄", "건강"],
    "여름": ["건강", "운동"],
    "피로": ["피곤", "건강"],
    "다리": ["운동", "건강"],
    "뼈": ["건강", "운동"],
    "눈": ["건강", "영양제"],
    "장": ["건강", "음식"],
    "탈모": ["건강", "피부"],
}


def _keyword_hash(keyword: str, index: int) -> int:
    h = hashlib.md5(f"{keyword}_{index}".encode()).hexdigest()
    return int(h[:8], 16)


def get_images_for_keyword(keyword: str, count: int = 7) -> list[str]:
    """키워드에 맞는 중복 없는 이미지 URL 리스트를 반환한다."""
    keyword_lower = keyword.lower()

    matched_categories: list[str] = []
    for term, categories in KEYWORD_CATEGORY_MAP.items():
        if term in keyword_lower:
            matched_categories.extend(categories)

    if not matched_categories:
        matched_categories = ["기본"]

    # 카테고리별 이미지 수집 (중복 제거)
    candidate_urls: list[str] = []
    seen: set[str] = set()

    for cat in matched_categories:
        for img in IMAGE_POOL.get(cat, []):
            if img not in seen:
                seen.add(img)
                candidate_urls.append(img)

    for img in _ALL_URLS:
        if img not in seen:
            seen.add(img)
            candidate_urls.append(img)

    # 결정론적 선택 (pop 방식으로 중복 원천 차단)
    result: list[str] = []
    available = list(candidate_urls)

    for i in range(min(count, len(available))):
        idx = _keyword_hash(keyword, i) % len(available)
        result.append(available[idx])
        available.pop(idx)
        if not available:
            break

    logger.info("이미지 매칭: '%s' → %d개 (GitHub 고정 URL)", keyword, len(result))
    return result


def get_header_image(keyword: str) -> str:
    images = get_images_for_keyword(keyword, count=1)
    return images[0] if images else _ALL_URLS[0]
