"""키워드 기반 이미지 자동 매칭 모듈 - Unsplash 검증된 URL 풀에서 선택."""

from __future__ import annotations

import hashlib

from src.core.logger import setup_logger

logger = setup_logger("image_search")

# 카테고리별 Unsplash 검증 이미지 풀
IMAGE_POOL: dict[str, list[str]] = {
    "건강": [
        "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?w=486&h=315&fit=crop",
    ],
    "음식": [
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=486&h=315&fit=crop",
    ],
    "운동": [
        "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1538805060514-97d9cc17730c?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=486&h=315&fit=crop",
    ],
    "봄": [
        "https://images.unsplash.com/photo-1522748906645-95d8adfd52c7?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1516575334481-f85287c2c82d?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1462275646964-a0e3c11f18a6?w=486&h=315&fit=crop",
    ],
    "피곤": [
        "https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=486&h=315&fit=crop",
    ],
    "알레르기": [
        "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1584515933487-779824d29309?w=486&h=315&fit=crop",
    ],
    "미세먼지": [
        "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1550572017-edd951b55104?w=486&h=315&fit=crop",
    ],
    "영양제": [
        "https://images.unsplash.com/photo-1550572017-edd951b55104?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=486&h=315&fit=crop",
    ],
    "수면": [
        "https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=486&h=315&fit=crop",
    ],
    "피부": [
        "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=486&h=315&fit=crop",
    ],
    "다이어트": [
        "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=486&h=315&fit=crop",
    ],
    "기본": [
        "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=486&h=315&fit=crop",
        "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=486&h=315&fit=crop",
    ],
}

# 키워드 → 카테고리 매핑
KEYWORD_CATEGORY_MAP: dict[str, list[str]] = {
    "알레르기": ["알레르기", "건강", "봄"],
    "꽃가루": ["알레르기", "봄", "건강"],
    "춘곤증": ["피곤", "봄", "건강"],
    "졸음": ["피곤", "수면"],
    "미세먼지": ["미세먼지", "건강"],
    "황사": ["미세먼지", "건강"],
    "다이어트": ["다이어트", "음식", "운동"],
    "식단": ["음식", "다이어트", "건강"],
    "비타민": ["영양제", "건강"],
    "영양제": ["영양제", "건강"],
    "운동": ["운동", "건강"],
    "피부": ["피부", "건강"],
    "스킨케어": ["피부"],
    "수면": ["수면", "건강"],
    "음식": ["음식", "건강"],
    "면역": ["건강", "음식"],
    "관절": ["건강", "운동"],
    "혈압": ["건강", "음식"],
    "당뇨": ["건강", "음식"],
    "간": ["건강", "음식"],
    "해독": ["건강", "음식", "다이어트"],
}


def _keyword_hash(keyword: str, index: int) -> int:
    """키워드와 인덱스로 결정론적 해시값을 생성한다."""
    h = hashlib.md5(f"{keyword}_{index}".encode()).hexdigest()
    return int(h[:8], 16)


def get_images_for_keyword(keyword: str, count: int = 7) -> list[str]:
    """키워드에 맞는 이미지 URL 리스트를 반환한다.

    Args:
        keyword: 포커스 키워드
        count: 필요한 이미지 수

    Returns:
        중복 없는 이미지 URL 리스트
    """
    keyword_lower = keyword.lower()

    # 키워드에서 카테고리 찾기
    matched_categories: list[str] = []
    for term, categories in KEYWORD_CATEGORY_MAP.items():
        if term in keyword_lower:
            matched_categories.extend(categories)

    if not matched_categories:
        matched_categories = ["기본", "건강"]

    # 카테고리별 이미지 수집 (중복 제거)
    all_images: list[str] = []
    seen: set[str] = set()

    for cat in matched_categories:
        for img in IMAGE_POOL.get(cat, []):
            if img not in seen:
                seen.add(img)
                all_images.append(img)

    # 기본 이미지로 부족분 채우기
    for img in IMAGE_POOL["기본"]:
        if img not in seen:
            seen.add(img)
            all_images.append(img)

    # 키워드 기반 결정론적 셔플 (같은 키워드면 같은 순서)
    result: list[str] = []
    for i in range(min(count, len(all_images))):
        idx = _keyword_hash(keyword, i) % len(all_images)
        img = all_images[idx]
        if img not in result:
            result.append(img)
        else:
            # 충돌 시 순차 선택
            for fallback in all_images:
                if fallback not in result:
                    result.append(fallback)
                    break

    logger.info("이미지 매칭: '%s' → %d개 (카테고리: %s)", keyword, len(result), matched_categories[:3])
    return result


def get_header_image(keyword: str) -> str:
    """키워드에 맞는 대표 이미지를 반환한다."""
    images = get_images_for_keyword(keyword, count=1)
    return images[0] if images else IMAGE_POOL["기본"][0]
