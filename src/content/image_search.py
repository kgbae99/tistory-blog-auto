"""키워드 기반 이미지 자동 매칭 모듈 - Unsplash 검증된 URL 풀에서 선택."""

from __future__ import annotations

import hashlib

from src.core.logger import setup_logger

logger = setup_logger("image_search")

# 전체 이미지 풀 (각 URL은 단 1회만 등록, 중복 없음)
# ID만 관리하고 URL은 함수에서 조립
_UNSPLASH_IDS: list[tuple[str, str]] = [
    # (photo_id, 카테고리)
    ("1571019614242-c5c5dee9f50b", "건강"),
    ("1544367567-0f2fcb009e0b", "건강"),
    ("1498837167922-ddd27525d352", "건강"),
    ("1505576399279-565b52d4ac71", "건강"),
    ("1532938911079-1b06ac7ceec7", "건강"),

    ("1512621776951-a57141f2eefd", "음식"),
    ("1490645935967-10de6ba17061", "음식"),
    ("1546069901-ba9599a7e63c", "음식"),
    ("1476224203421-9ac39bcb3327", "음식"),
    ("1504674900247-0877df9cc836", "음식"),

    ("1517836357463-d25dfeac3438", "운동"),
    ("1538805060514-97d9cc17730c", "운동"),
    ("1476480862126-209bfaa8edc8", "운동"),
    ("1534258936925-c58bed479fcb", "운동"),

    ("1522748906645-95d8adfd52c7", "봄"),
    ("1516575334481-f85287c2c82d", "봄"),

    ("1541781774459-bb2af2f05b55", "피곤"),
    ("1506126613408-eca07ce68773", "수면"),

    ("1576091160550-2173dba999ef", "알레르기"),
    ("1584515933487-779824d29309", "알레르기"),

    ("1509042239860-f550ce710b93", "미세먼지"),
    ("1550572017-edd951b55104", "영양제"),

    ("1522337360788-8b13dee7a37e", "피부"),
    ("1556228578-0d85b1a4d571", "피부"),

    ("1483721310020-03333e577078", "다이어트"),
    ("1540189549336-e6e99c3679fe", "다이어트"),
]


def _id_to_url(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?w=486&h=315&fit=crop"


# 카테고리별 이미지 인덱스 구축
IMAGE_POOL: dict[str, list[str]] = {}
_ALL_URLS: list[str] = []
for _pid, _cat in _UNSPLASH_IDS:
    url = _id_to_url(_pid)
    _ALL_URLS.append(url)
    IMAGE_POOL.setdefault(_cat, []).append(url)

# 기본 카테고리 = 전체 풀
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
}


def _keyword_hash(keyword: str, index: int) -> int:
    h = hashlib.md5(f"{keyword}_{index}".encode()).hexdigest()
    return int(h[:8], 16)


def get_images_for_keyword(keyword: str, count: int = 7) -> list[str]:
    """키워드에 맞는 중복 없는 이미지 URL 리스트를 반환한다."""
    keyword_lower = keyword.lower()

    # 키워드에서 카테고리 찾기
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

    # 기본 풀로 부족분 채우기
    for img in _ALL_URLS:
        if img not in seen:
            seen.add(img)
            candidate_urls.append(img)

    # 키워드 기반 결정론적 선택 (같은 키워드 = 같은 이미지 순서)
    result: list[str] = []
    available = list(candidate_urls)

    for i in range(min(count, len(available))):
        idx = _keyword_hash(keyword, i) % len(available)
        result.append(available[idx])
        available.pop(idx)
        if not available:
            break

    logger.info("이미지 매칭: '%s' → %d개 (중복 0)", keyword, len(result))
    return result


def get_header_image(keyword: str) -> str:
    """키워드에 맞는 대표 이미지를 반환한다."""
    images = get_images_for_keyword(keyword, count=1)
    return images[0] if images else _ALL_URLS[0]
