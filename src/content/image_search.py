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
    # IT/테크 - 노트북 (5개)
    ("tech_01.jpg", "IT_laptop"), ("tech_02.jpg", "IT_laptop"), ("tech_03.jpg", "IT_laptop"),
    ("tech_12.jpg", "IT_laptop"), ("tech_13.jpg", "IT_laptop"),
    # IT/테크 - 이어폰/헤드폰/오디오 (2개, tech_15는 선글라스라 제외)
    ("tech_06.jpg", "IT_audio"), ("tech_22.jpg", "IT_audio"),
    # IT/테크 - 기타 (tech_15: 선글라스 이미지, IT_general로 분류)
    ("tech_15.jpg", "IT_general"),
    # IT/테크 - 스마트폰 (2개)
    ("tech_07.jpg", "IT_phone"), ("tech_21.jpg", "IT_phone"),
    # IT/테크 - 키보드/마우스 (4개)
    ("tech_10.jpg", "IT_keyboard"), ("tech_14.jpg", "IT_keyboard"),
    ("tech_19.jpg", "IT_keyboard"), ("tech_24.jpg", "IT_keyboard"),
    # IT/테크 - 코딩/소프트웨어 (4개)
    ("tech_08.jpg", "IT_coding"), ("tech_09.jpg", "IT_coding"),
    ("tech_11.jpg", "IT_coding"), ("tech_23.jpg", "IT_coding"),
    # IT/테크 - 모니터/셋업 (2개)
    ("tech_17.jpg", "IT_monitor"), ("tech_18.jpg", "IT_monitor"),
    # IT/테크 - AI/로봇 (4개)
    ("tech_25.jpg", "IT_ai"), ("tech_26.jpg", "IT_ai"),
    ("tech_27.jpg", "IT_ai"), ("tech_28.jpg", "IT_ai"),
    # IT/테크 - 스마트워치 (1개)
    ("tech_29.jpg", "IT_watch"),
    # IT/테크 - 게이밍 (1개)
    ("tech_20.jpg", "IT_gaming"),
    # IT/테크 - 일반/하드웨어 (3개)
    ("tech_04.jpg", "IT_general"), ("tech_05.jpg", "IT_general"), ("tech_30.jpg", "IT_general"),
]

# 카테고리별 인덱스
IMAGE_POOL: dict[str, list[str]] = {}
_ALL_URLS: list[str] = []
for _fname, _cat in _IMAGES:
    url = f"{_BASE}/{_fname}"
    _ALL_URLS.append(url)
    IMAGE_POOL.setdefault(_cat, []).append(url)
IMAGE_POOL["기본"] = list(_ALL_URLS)

# IT 세부 카테고리를 상위 "IT" 풀에도 포함
_IT_SUBCATS = ["IT_laptop", "IT_audio", "IT_phone", "IT_keyboard", "IT_coding", "IT_monitor", "IT_ai", "IT_watch", "IT_gaming", "IT_general"]
IMAGE_POOL["IT"] = []
for _subcat in _IT_SUBCATS:
    IMAGE_POOL["IT"].extend(IMAGE_POOL.get(_subcat, []))

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
    "당뇨": ["건강", "음식"], "간건강": ["건강", "음식"], "간기능": ["건강", "음식"],
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
    # IT/테크 - 이어폰/헤드폰/오디오
    "이어폰": ["IT_audio", "IT"], "헤드폰": ["IT_audio", "IT"],
    "노이즈캔슬링": ["IT_audio", "IT"], "무선이어폰": ["IT_audio", "IT"],
    "TWS": ["IT_audio", "IT"], "에어팟": ["IT_audio", "IT"],
    "갤럭시버즈": ["IT_audio", "IT"], "스피커": ["IT_audio", "IT"],
    "블루투스": ["IT_audio", "IT_phone", "IT"],
    # IT/테크 - 키보드/마우스
    "키보드": ["IT_keyboard", "IT"], "마우스": ["IT_keyboard", "IT"],
    "기계식": ["IT_keyboard", "IT"], "게이밍키보드": ["IT_keyboard", "IT"],
    "무선키보드": ["IT_keyboard", "IT"], "트랙패드": ["IT_keyboard", "IT"],
    # IT/테크 - 스마트폰/모바일
    "스마트폰": ["IT_phone", "IT"], "아이폰": ["IT_phone", "IT"],
    "갤럭시S": ["IT_phone", "IT"], "핸드폰": ["IT_phone", "IT"],
    "휴대폰": ["IT_phone", "IT"], "배터리": ["IT_phone", "IT"],
    "충전기": ["IT_phone", "IT"], "보조배터리": ["IT_phone", "IT"],
    # IT/테크 - 노트북/컴퓨터
    "노트북": ["IT_laptop", "IT"], "컴퓨터": ["IT_laptop", "IT"],
    "PC": ["IT_laptop", "IT"], "맥북": ["IT_laptop", "IT"],
    "데스크탑": ["IT_laptop", "IT"],
    # IT/테크 - 모니터/디스플레이
    "모니터": ["IT_monitor", "IT"], "듀얼모니터": ["IT_monitor", "IT"],
    "디스플레이": ["IT_monitor", "IT"], "4K": ["IT_monitor", "IT"],
    "웹캠": ["IT_monitor", "IT"], "화면": ["IT_monitor", "IT"],
    # IT/테크 - 태블릿
    "태블릿": ["IT_laptop", "IT_phone", "IT"], "아이패드": ["IT_laptop", "IT"],
    "갤럭시탭": ["IT_laptop", "IT"],
    # IT/테크 - 스마트워치/웨어러블
    "스마트워치": ["IT_watch", "IT"], "워치": ["IT_watch", "IT"],
    "애플워치": ["IT_watch", "IT"], "갤럭시워치": ["IT_watch", "IT"],
    "웨어러블": ["IT_watch", "IT"],
    # IT/테크 - 저장장치/하드웨어
    "SSD": ["IT_general", "IT"], "하드디스크": ["IT_general", "IT"],
    "외장하드": ["IT_general", "IT"], "그래픽카드": ["IT_general", "IT"],
    "RAM": ["IT_general", "IT"], "마이크": ["IT_general", "IT"],
    # IT/테크 - 소프트웨어/앱
    "소프트웨어": ["IT_coding", "IT"], "앱": ["IT_coding", "IT"],
    "프로그램": ["IT_coding", "IT"], "크롬": ["IT_coding", "IT"],
    "윈도우": ["IT_coding", "IT"],
    # IT/테크 - AI
    "AI": ["IT_ai", "IT"], "인공지능": ["IT_ai", "IT"],
    "ChatGPT": ["IT_ai", "IT"], "GPT": ["IT_ai", "IT"],
    "챗봇": ["IT_ai", "IT"],
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

    _IT_SUBCATS_SET = {"IT_laptop", "IT_audio", "IT_phone", "IT_keyboard", "IT_coding", "IT_monitor", "IT_ai", "IT_watch", "IT_gaming", "IT_general"}

    # 1순위: 키워드에서 직접 매핑된 세부 카테고리 (IT 제외)
    direct_cats = set(matched_categories) - {"IT"}
    # IT 관련 키워드이면 다른 IT 세부 이미지를 2순위 폴백으로 사용
    is_it_keyword = bool(_IT_SUBCATS_SET & direct_cats)

    cat_imgs: list[str] = []       # 1순위: 직접 매핑 카테고리
    it_fallback: list[str] = []    # 2순위: 다른 IT 이미지 (IT 키워드일 때)
    other_imgs: list[str] = []     # 3순위: 무관 이미지

    for fname, cat in _IMAGES:
        url = f"{_BASE}/{fname}"
        if cat in direct_cats:
            cat_imgs.append(url)
        elif is_it_keyword and cat in _IT_SUBCATS_SET:
            it_fallback.append(url)
        else:
            other_imgs.append(url)

    # 1순위 카테고리 이미지 순서 분산
    cat_offset = kw_hash % max(len(cat_imgs), 1)
    cat_shuffled = [cat_imgs[(cat_offset + j) % len(cat_imgs)] for j in range(len(cat_imgs))]

    # 2순위 IT 폴백 이미지 순서 분산
    it_offset = (kw_hash // 97) % max(len(it_fallback), 1)
    it_shuffled = [it_fallback[(it_offset + j) % len(it_fallback)] for j in range(len(it_fallback))]

    # 3순위 무관 이미지 순서 분산
    other_offset = (kw_hash // 137) % max(len(other_imgs), 1)
    other_shuffled = [other_imgs[(other_offset + j) % len(other_imgs)] for j in range(len(other_imgs))]

    all_candidates = cat_shuffled + it_shuffled + other_shuffled
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
