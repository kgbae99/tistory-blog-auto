"""키워드 기반 이미지 자동 매칭 - GitHub 호스팅 고정 이미지 136개."""

from __future__ import annotations

import hashlib

from src.core.logger import setup_logger

logger = setup_logger("image_search")

_BASE = "https://raw.githubusercontent.com/kgbae99/tistory-blog-auto/master/assets/images"

# 전체 이미지 풀 136개 (카테고리별 분류, 중복 없음)
_IMAGES: list[tuple[str, str]] = [
    # 건강 (25개)
    ("health_01.jpg", "건강"), ("health_02.jpg", "건강"), ("health_03.jpg", "건강"),
    ("health_04.jpg", "건강"), ("health_05.jpg", "건강"), ("health_06.jpg", "건강"),
    ("health_07.jpg", "건강"), ("health_08.jpg", "건강"), ("health_09.jpg", "건강"),
    ("health_10.jpg", "건강"), ("health_11.jpg", "건강"), ("health_12.jpg", "건강"),
    ("health_13.jpg", "건강"), ("health_14.jpg", "건강"), ("health_15.jpg", "건강"),
    ("health_16.jpg", "건강"), ("health_17.jpg", "건강"), ("health_18.jpg", "건강"),
    ("health_19.jpg", "건강"), ("health_20.jpg", "건강"),
    ("health_22.jpg", "건강"), ("health_23.jpg", "건강"), ("health_25.jpg", "건강"),
    # 음식 (25개)
    ("food_01.jpg", "음식"), ("food_02.jpg", "음식"), ("food_03.jpg", "음식"),
    ("food_04.jpg", "음식"), ("food_05.jpg", "음식"), ("food_06.jpg", "음식"),
    ("food_07.jpg", "음식"), ("food_08.jpg", "음식"), ("food_09.jpg", "음식"),
    ("food_10.jpg", "음식"), ("food_11.jpg", "음식"), ("food_12.jpg", "음식"),
    ("food_14.jpg", "음식"), ("food_15.jpg", "음식"),
    ("food_16.jpg", "음식"), ("food_17.jpg", "음식"), ("food_18.jpg", "음식"),
    ("food_19.jpg", "음식"), ("food_20.jpg", "음식"), ("food_21.jpg", "음식"),
    ("food_22.jpg", "음식"), ("food_23.jpg", "음식"), ("food_24.jpg", "음식"), ("food_25.jpg", "음식"),
    # 운동 (15개)
    ("exercise_01.jpg", "운동"), ("exercise_02.jpg", "운동"), ("exercise_03.jpg", "운동"),
    ("exercise_04.jpg", "운동"), ("exercise_06.jpg", "운동"), ("exercise_07.jpg", "운동"),
    ("exercise_09.jpg", "운동"), ("exercise_10.jpg", "운동"), ("exercise_11.jpg", "운동"),
    ("exercise_12.jpg", "운동"), ("exercise_13.jpg", "운동"), ("exercise_14.jpg", "운동"),
    ("exercise_15.jpg", "운동"),
    # 자연/봄 (5개)
    ("spring_01.jpg", "봄"), ("spring_02.jpg", "봄"),
    ("nature_01.jpg", "봄"), ("nature_02.jpg", "봄"), ("nature_03.jpg", "봄"),
    # 피부/뷰티 (11개)
    ("skin_01.jpg", "피부"), ("skin_02.jpg", "피부"), ("skin_03.jpg", "피부"),
    ("skin_04.jpg", "피부"), ("skin_05.jpg", "피부"), ("skin_08.jpg", "피부"),
    ("skin_09.jpg", "피부"), ("skin_10.jpg", "피부"), ("skin_11.jpg", "피부"),
    ("beauty_01.jpg", "피부"), ("beauty_02.jpg", "피부"),
    # 수면/휴식 (8개)
    ("tired_01.jpg", "피곤"), ("sleep_01.jpg", "수면"),
    ("sleep_02.jpg", "수면"), ("sleep_03.jpg", "수면"), ("rest_01.jpg", "수면"),
    ("sleep_04.jpg", "수면"), ("sleep_05.jpg", "수면"), ("sleep_06.jpg", "수면"),
    # 영양제 (3개)
    ("vitamin_01.jpg", "영양제"), ("vitamin_02.jpg", "영양제"), ("vitamin_03.jpg", "영양제"),
    # 알레르기/미세먼지 (3개)
    ("allergy_01.jpg", "알레르기"), ("allergy_02.jpg", "알레르기"), ("dust_01.jpg", "미세먼지"),
    # 다이어트 (7개)
    ("diet_01.jpg", "다이어트"), ("diet_02.jpg", "다이어트"),
    ("diet_03.jpg", "다이어트"), ("diet_04.jpg", "다이어트"),
    ("diet_05.jpg", "다이어트"), ("diet_06.jpg", "다이어트"), ("diet_07.jpg", "다이어트"),
    # 정부지원/복지/금융 (4개)
    ("gov_02.jpg", "정부지원"), ("gov_03.jpg", "정부지원"),
    ("gov_04.jpg", "정부지원"), ("gov_06.jpg", "정부지원"),
    # 의료/건강검진 (3개)
    ("medical_01.jpg", "의료"), ("medical_02.jpg", "의료"), ("medical_03.jpg", "의료"),
    # 금융/생활 (3개)
    ("money_02.jpg", "금융"), ("office_01.jpg", "사무"), ("office_02.jpg", "사무"),
    # IT/테크 (29개)
    ("tech_01.jpg", "IT"), ("tech_02.jpg", "IT"), ("tech_03.jpg", "IT"),
    ("tech_04.jpg", "IT"), ("tech_05.jpg", "IT"), ("tech_06.jpg", "IT"),
    ("tech_07.jpg", "IT"), ("tech_08.jpg", "IT"), ("tech_09.jpg", "IT"),
    ("tech_10.jpg", "IT"), ("tech_11.jpg", "IT"), ("tech_12.jpg", "IT"),
    ("tech_13.jpg", "IT"), ("tech_14.jpg", "IT"), ("tech_15.jpg", "IT"),
    ("tech_17.jpg", "IT"), ("tech_18.jpg", "IT"), ("tech_19.jpg", "IT"),
    ("tech_20.jpg", "IT"), ("tech_21.jpg", "IT"), ("tech_22.jpg", "IT"),
    ("tech_23.jpg", "IT"), ("tech_24.jpg", "IT"), ("tech_25.jpg", "IT"),
    ("tech_26.jpg", "IT"), ("tech_27.jpg", "IT"), ("tech_28.jpg", "IT"),
    ("tech_29.jpg", "IT"), ("tech_30.jpg", "IT"),
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
    # 정부지원/복지/금융/의료
    "정부": ["정부지원", "사무"], "지원금": ["정부지원", "금융"],
    "복지": ["정부지원", "사무"], "보조금": ["정부지원", "금융"],
    "연금": ["정부지원", "금융"], "보험": ["금융", "정부지원"],
    "신청": ["정부지원", "사무"], "적금": ["금융", "사무"],
    "건강검진": ["의료", "건강"], "검진": ["의료", "건강"],
    "병원": ["의료", "건강"], "진료": ["의료", "건강"],
    # IT/테크
    "키보드": ["IT"], "마우스": ["IT"], "모니터": ["IT"],
    "노트북": ["IT"], "컴퓨터": ["IT"], "PC": ["IT"],
    "스마트폰": ["IT"], "폰": ["IT"], "아이폰": ["IT"],
    "이어폰": ["IT"], "헤드폰": ["IT"], "블루투스": ["IT"],
    "SSD": ["IT"], "하드": ["IT"], "저장": ["IT"],
    "그래픽카드": ["IT"], "RAM": ["IT"], "메모리": ["IT"],
    "배터리": ["IT"], "충전": ["IT"], "보조배터리": ["IT"],
    "웹캠": ["IT"], "마이크": ["IT"], "스피커": ["IT"],
    "태블릿": ["IT"], "아이패드": ["IT"], "갤럭시탭": ["IT"],
    "소프트웨어": ["IT"], "앱": ["IT"], "프로그램": ["IT"],
    "AI": ["IT"], "인공지능": ["IT"], "ChatGPT": ["IT"],
    "크롬": ["IT"], "윈도우": ["IT"], "맥북": ["IT"],
    "듀얼모니터": ["IT"], "스마트워치": ["IT"], "워치": ["IT"],
}


def get_images_for_keyword(keyword: str, count: int = 8, post_index: int = 0) -> list[str]:
    """키워드에 맞는 중복 없는 이미지 URL 리스트를 반환한다.

    날짜 + 키워드 + post_index 조합으로 매일, 포스트마다 다른 이미지 선택.
    관련 카테고리 이미지를 우선 배치한다.
    """
    from datetime import date
    keyword_lower = keyword.lower()

    # 날짜 + 키워드 + post_index 해시 (같은 날 포스트마다 다른 이미지 보장)
    today = date.today().isoformat()
    salt = f"{today}_{post_index}_{keyword}"
    kw_hash = int(hashlib.sha256(salt.encode()).hexdigest(), 16)

    # 관련 카테고리 이미지 우선 선별
    matched_categories: list[str] = []
    for term, categories in KEYWORD_CATEGORY_MAP.items():
        if term in keyword_lower:
            matched_categories.extend(categories)

    # 카테고리 매칭 이미지와 나머지 분리
    cat_imgs: list[str] = []
    other_imgs: list[str] = []
    for fname, cat in _IMAGES:
        url = f"{_BASE}/{fname}"
        if cat in matched_categories:
            cat_imgs.append(url)
        else:
            other_imgs.append(url)

    # 카테고리 이미지 내에서 post_index로 시작점 분산
    cat_offset = kw_hash % max(len(cat_imgs), 1)
    cat_shuffled = [cat_imgs[(cat_offset + j) % len(cat_imgs)] for j in range(len(cat_imgs))]

    # 나머지 이미지도 다른 offset으로 분산
    other_offset = (kw_hash // 137) % max(len(other_imgs), 1)
    other_shuffled = [other_imgs[(other_offset + j) % len(other_imgs)] for j in range(len(other_imgs))]

    all_candidates = cat_shuffled + other_shuffled
    # 중복 제거
    seen: set[str] = set()
    result: list[str] = []
    for img in all_candidates:
        if img not in seen:
            seen.add(img)
            result.append(img)
        if len(result) >= count:
            break

    logger.info("이미지 매칭: '%s'(idx=%d) → 카테고리=%s, %d개 선택", keyword, post_index, matched_categories[:2], len(result))
    return result


def get_header_image(keyword: str) -> str:
    images = get_images_for_keyword(keyword, count=1)
    return images[0] if images else _ALL_URLS[0]
