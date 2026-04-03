"""키워드 기반 이미지 자동 매칭 - GitHub 호스팅 고정 이미지 136개."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from src.core.logger import setup_logger

logger = setup_logger("image_search")

_USED_FILE = Path(__file__).parent.parent.parent / "data" / "used_images.json"
_USED_KEEP_DAYS = 60  # 60일 이내 사용 이미지는 중복으로 간주


def _load_used_images() -> set[str]:
    """최근 _USED_KEEP_DAYS일 내 사용된 이미지 파일명 집합 반환."""
    if not _USED_FILE.exists():
        return set()
    try:
        raw = json.loads(_USED_FILE.read_text(encoding="utf-8"))
        # 구버전 리스트 형식 처리
        if isinstance(raw, list):
            return set(raw)
        data: dict[str, list[str]] = raw
        cutoff = (date.today() - timedelta(days=_USED_KEEP_DAYS)).isoformat()
        used: set[str] = set()
        for day, fnames in data.items():
            if day >= cutoff:
                used.update(fnames)
        return used
    except Exception:
        return set()


def _save_used_images(fnames: list[str]) -> None:
    """오늘 날짜로 사용 이미지 기록. 오래된 항목은 자동 삭제."""
    try:
        data: dict[str, list[str]] = {}
        if _USED_FILE.exists():
            data = json.loads(_USED_FILE.read_text(encoding="utf-8"))
        today = date.today().isoformat()
        existing = set(data.get(today, []))
        existing.update(fnames)
        data[today] = sorted(existing)
        # _USED_KEEP_DAYS보다 오래된 항목 삭제
        cutoff = (date.today() - timedelta(days=_USED_KEEP_DAYS)).isoformat()
        data = {k: v for k, v in data.items() if k >= cutoff}
        _USED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("used_images 저장 실패: %s", e)

_BASE = "https://raw.githubusercontent.com/kgbae99/tistory-blog-auto/master/assets/images"

# 전체 이미지 풀 136개 (카테고리별 분류, 중복 없음)
_IMAGES: list[tuple[str, str]] = [
    # 건강 - 운동/피트니스 실제 내용 기반 재분류
    ("health_01.jpg", "운동"),   # 피트니스 코칭
    ("health_02.jpg", "운동"),   # 요가 일몰 실루엣
    ("health_07.jpg", "운동"),   # 달리기
    ("health_09.jpg", "운동"),   # 헬스 덤벨
    ("health_10.jpg", "운동"),   # 필라테스
    ("health_11.jpg", "운동"),   # 요가 실루엣
    # 건강 - 음식/식이 실제 내용 기반 재분류
    ("health_03.jpg", "음식"),   # 채소 뷔페
    ("health_04.jpg", "음식"),   # 샐러드 jar
    ("health_06.jpg", "음식"),   # 채소 과일
    ("health_13.jpg", "음식"),   # 채소 샐러드
    ("health_22.jpg", "음식"),   # 감귤류 과일
    # 건강 - 의료/의학 (건강 카테고리 유지)
    ("health_05.jpg", "건강"),   # 의사 청진기
    ("health_08.jpg", "건강"),   # 뇌 모형
    ("health_12.jpg", "건강"),   # 수술실 의사들
    ("health_14.jpg", "건강"),   # 수술실 공간
    ("health_15.jpg", "건강"),   # 심장 모형
    ("health_16.jpg", "건강"),   # 청진기 흑백
    ("health_17.jpg", "건강"),   # 의사 청진기
    ("health_18.jpg", "건강"),   # 뇌 모형
    ("health_19.jpg", "건강"),   # 의사 스마트폰
    ("health_20.jpg", "건강"),   # 수술실
    ("health_23.jpg", "건강"),   # 엑스레이
    ("health_25.jpg", "사무"),   # 컨퍼런스 청중
    # 음식 (24개)
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
    # 영양제 (3개) + 건강 이미지를 영양제로도 분류 (이미지 다양성 확보)
    ("vitamin_01.jpg", "영양제"), ("vitamin_02.jpg", "영양제"), ("vitamin_03.jpg", "영양제"),
    ("health_05.jpg", "영양제"),   # 의사 청진기
    ("health_08.jpg", "영양제"),   # 뇌 모형
    ("health_16.jpg", "영양제"),   # 청진기 흑백
    ("health_19.jpg", "영양제"),   # 의사 스마트폰
    ("health_23.jpg", "영양제"),   # 엑스레이
    ("medical_01.jpg", "영양제"), ("medical_02.jpg", "영양제"), ("medical_03.jpg", "영양제"),
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
    # 건강 - 알레르기/계절
    "알레르기": ["알레르기", "건강"], "꽃가루": ["알레르기", "봄"],
    "춘곤증": ["피곤", "봄"], "졸음": ["피곤", "수면"],
    "미세먼지": ["미세먼지", "건강"], "황사": ["미세먼지", "건강"],
    "환절기": ["봄", "건강"], "봄나물": ["봄", "음식"],
    "봄철": ["봄", "건강"], "봄": ["봄", "건강"],
    "여름": ["건강", "운동"],
    # 건강 - 일반
    "건강": ["건강"], "건강관리": ["건강"], "건강루틴": ["건강"],
    "루틴": ["건강", "운동"], "생활습관": ["건강"],
    "면역": ["건강", "음식"], "면역력": ["건강", "음식"],
    "공복": ["음식", "건강"], "아침": ["건강", "음식"],
    "해독": ["건강", "다이어트"],
    # 건강 - 수면/피로
    "수면": ["수면", "피곤"], "숙면": ["수면", "피곤"],
    "불면": ["수면", "피곤"], "피로": ["피곤", "건강"],
    "피로회복": ["피곤", "건강"], "스트레스": ["수면", "건강"],
    "휴식": ["수면", "건강"],
    # 건강 - 운동/신체
    "운동": ["운동", "건강"], "홈트레이닝": ["운동", "건강"],
    "홈트": ["운동", "건강"], "스트레칭": ["운동", "건강"],
    "근육": ["운동", "건강"], "체력": ["운동", "건강"],
    "관절": ["운동", "건강"], "무릎": ["운동", "건강"],
    "허리": ["운동", "건강"], "다리": ["운동", "건강"],
    "목": ["건강", "운동"], "뼈": ["건강", "운동"],
    "어깨": ["운동", "건강"], "손목": ["건강", "운동"],
    "발": ["건강", "운동"],
    # 건강 - 피부/미용
    "피부": ["피부", "건강"], "스킨케어": ["피부"],
    "보습": ["피부"], "노화": ["피부", "건강"],
    "탈모": ["건강", "피부"], "주름": ["피부", "건강"],
    "목주름": ["피부", "건강"], "미백": ["피부"],
    "자외선": ["피부", "건강"], "선크림": ["피부"],
    # 건강 - 식품/영양
    "다이어트": ["다이어트", "음식"], "식단": ["음식", "건강"],
    "비타민": ["영양제", "건강"], "영양제": ["영양제", "건강"],
    "아연": ["영양제", "건강"], "마그네슘": ["영양제", "건강"],
    "오메가": ["영양제", "건강"], "콜라겐": ["피부", "영양제"],
    "음식": ["음식", "건강"], "식품": ["음식", "건강"],
    "콜레스테롤": ["음식", "건강"], "혈관": ["건강", "음식"],
    "항산화": ["음식", "건강"], "단백질": ["음식", "운동"],
    "프로바이오틱스": ["영양제", "음식"], "유산균": ["영양제", "음식"],
    "혈압": ["건강", "음식"], "혈당": ["건강", "음식"],
    "당뇨": ["건강", "음식"], "간건강": ["건강", "음식"],
    "간기능": ["건강", "음식"],
    "장건강": ["건강", "음식"], "장": ["건강", "음식"],
    "눈건강": ["건강", "영양제"], "눈피로": ["건강", "피곤"],
    "호르몬": ["건강", "음식"], "여성호르몬": ["건강", "피부"],
    "갱년기": ["건강", "음식"],
    # 건강 - 질환/증상
    "두통": ["건강"], "변비": ["건강", "음식"],
    "소화": ["건강", "음식"], "위장": ["건강", "음식"],
    "비염": ["알레르기", "건강"], "천식": ["건강"],
    "고혈압": ["건강", "음식"], "저혈압": ["건강"],
    "발기부전": ["건강"], "전립선": ["건강"],
    "갑상선": ["건강"], "빈혈": ["건강", "음식"],
    "신장": ["건강", "음식"], "방광": ["건강"],
    "손목터널증후군": ["건강", "운동"],
    "오십견": ["운동", "건강"], "디스크": ["운동", "건강"],
    # 정부지원/복지/금융/의료
    "정부지원": ["정부지원", "사무"], "지원금": ["정부지원", "금융"],
    "복지": ["정부지원", "사무"], "보조금": ["정부지원", "금융"],
    "연금": ["정부지원", "금융"], "보험": ["금융", "정부지원"],
    "신청방법": ["정부지원", "사무"], "적금": ["금융", "사무"],
    "건강검진": ["의료", "건강"], "검진": ["의료", "건강"],
    "병원": ["의료", "건강"], "진료": ["의료", "건강"],
    "노인": ["정부지원", "건강"], "기초생활": ["정부지원"],
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
    "외장하드": ["IT_general", "IT"], "외장SSD": ["IT_general", "IT"],
    "그래픽카드": ["IT_general", "IT"], "GPU": ["IT_general", "IT"],
    "RAM": ["IT_general", "IT"], "마이크": ["IT_general", "IT"],
    "USB": ["IT_general", "IT"], "허브": ["IT_general", "IT"],
    "공유기": ["IT_general", "IT"], "와이파이": ["IT_general", "IT"],
    "WiFi": ["IT_general", "IT"], "인터넷": ["IT_general", "IT"],
    "클라우드": ["IT_coding", "IT"], "스토리지": ["IT_general", "IT"],
    # IT/테크 - 카메라/영상
    "액션캠": ["IT_monitor", "IT"], "웹캠": ["IT_monitor", "IT"],
    "카메라": ["IT_monitor", "IT"], "동영상": ["IT_monitor", "IT"],
    "화면녹화": ["IT_monitor", "IT"], "녹화": ["IT_monitor", "IT"],
    # IT/테크 - 소프트웨어/앱
    "소프트웨어": ["IT_coding", "IT"], "앱": ["IT_coding", "IT"],
    "프로그램": ["IT_coding", "IT"], "크롬": ["IT_coding", "IT"],
    "윈도우": ["IT_coding", "IT"], "맥OS": ["IT_coding", "IT"],
    "PDF": ["IT_coding", "IT"], "편집": ["IT_coding", "IT"],
    "확장프로그램": ["IT_coding", "IT"], "생산성": ["IT_coding", "IT"],
    "업그레이드": ["IT_general", "IT"], "발열": ["IT_general", "IT"],
    "속도": ["IT_general", "IT"], "최적화": ["IT_general", "IT"],
    "견적": ["IT_general", "IT"], "조립": ["IT_general", "IT"],
    # IT/테크 - AI
    "AI": ["IT_ai", "IT"], "인공지능": ["IT_ai", "IT"],
    "ChatGPT": ["IT_ai", "IT"], "GPT": ["IT_ai", "IT"],
    "챗봇": ["IT_ai", "IT"], "머신러닝": ["IT_ai", "IT"],
}


def get_images_for_keyword(keyword: str, count: int = 8, post_index: int = 0) -> list[str]:
    """키워드에 맞는 중복 없는 이미지 URL 리스트를 반환한다.

    GPT가 키워드를 분석해 이미지 카테고리를 자동 분류.
    캐시에 저장되어 동일 키워드는 API 호출 없이 즉시 처리.
    날짜 + post_index 기반 해시로 매일/포스트마다 다른 이미지 선택.
    """
    from datetime import date
    from src.content.category_classifier import classify_keyword

    # 날짜 + 키워드 + post_index 해시 (같은 날 포스트마다 다른 이미지 보장)
    today = date.today().isoformat()
    salt = f"{today}_{post_index}_{keyword}"
    kw_hash = int(hashlib.sha256(salt.encode()).hexdigest(), 16)

    _IT_SUBCATS_SET = {"IT_laptop", "IT_audio", "IT_phone", "IT_keyboard", "IT_coding", "IT_monitor", "IT_ai", "IT_watch", "IT_gaming", "IT_general"}

    # GPT로 카테고리 분류 (캐시 우선)
    gpt_cats = classify_keyword(keyword)
    primary_cats: set[str] = set(gpt_cats[:1])   # 1순위: GPT 첫 번째 카테고리
    secondary_cats: set[str] = set(gpt_cats[1:])  # 2순위: GPT 두 번째 카테고리

    is_it_keyword = bool(_IT_SUBCATS_SET & (primary_cats | secondary_cats))

    primary_imgs: list[str] = []    # 1순위: 주제어 카테고리 이미지
    secondary_imgs: list[str] = []  # 2순위: 보조 카테고리 이미지
    it_fallback: list[str] = []     # 3순위: 다른 IT 이미지 (IT 글 한정)
    other_imgs: list[str] = []      # 4순위: 무관 이미지

    for fname, cat in _IMAGES:
        url = f"{_BASE}/{fname}"
        if cat in primary_cats:
            primary_imgs.append(url)
        elif cat in secondary_cats:
            secondary_imgs.append(url)
        elif is_it_keyword and cat in _IT_SUBCATS_SET:
            it_fallback.append(url)
        else:
            other_imgs.append(url)

    def _shuffle(imgs: list[str], seed_div: int) -> list[str]:
        if not imgs:
            return []
        offset = (kw_hash // seed_div) % len(imgs)
        return [imgs[(offset + j) % len(imgs)] for j in range(len(imgs))]

    all_candidates = (
        _shuffle(primary_imgs, 1)
        + _shuffle(secondary_imgs, 97)
        + _shuffle(it_fallback, 211)
        + _shuffle(other_imgs, 137)
    )

    # cross-post 중복 방지: 최근 사용 이미지 제외
    recently_used = _load_used_images()

    # 중복 제거 (포스트 내 중복 + cross-post 중복 방지)
    seen: set[str] = set()
    result: list[str] = []
    fallback: list[str] = []  # 새 이미지 부족 시 최근 사용 이미지로 보충

    for img in all_candidates:
        if img in seen:
            continue
        seen.add(img)
        fname = img.split("/")[-1]
        if fname not in recently_used:
            result.append(img)
        else:
            fallback.append(img)
        if len(result) >= count:
            break

    # 새 이미지가 부족하면 최근 사용 이미지로 보충 (post_index 기반 오프셋으로 포스트간 다른 이미지 선택)
    if len(result) < count and fallback:
        offset = post_index % len(fallback)
        rotated = [fallback[(offset + j) % len(fallback)] for j in range(len(fallback))]
        for img in rotated:
            if img not in result:
                result.append(img)
            if len(result) >= count:
                break

    # 선택된 이미지를 사용 기록에 저장
    _save_used_images([img.split("/")[-1] for img in result])

    logger.info("이미지 매칭: '%s'(idx=%d) → 주제=%s, %d개 선택 (재사용 %d개)", keyword, post_index, list(primary_cats), len(result), max(0, len(result) - (len(result) - len(fallback[:max(0,count-len(result))]))))
    return result


def get_header_image(keyword: str) -> str:
    images = get_images_for_keyword(keyword, count=1)
    return images[0] if images else _ALL_URLS[0]
