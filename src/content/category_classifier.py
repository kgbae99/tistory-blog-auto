"""GPT 기반 키워드→이미지 카테고리 자동 분류 + 캐시."""

from __future__ import annotations

import json
import os
from pathlib import Path

from src.core.logger import setup_logger

logger = setup_logger("category_classifier")

_CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "keyword_category_cache.json"

# 사용 가능한 전체 카테고리 목록
VALID_CATEGORIES: list[str] = [
    # 건강/생활
    "건강", "피곤", "수면", "운동", "피부", "음식", "다이어트", "영양제",
    "봄", "알레르기", "미세먼지", "의료", "정부지원", "금융", "사무",
    # IT 세부
    "IT_laptop", "IT_audio", "IT_phone", "IT_keyboard", "IT_coding",
    "IT_monitor", "IT_ai", "IT_watch", "IT_gaming", "IT_general",
]

_CATEGORY_GUIDE = """
카테고리 선택 기준:
- 춘곤증/피로/졸음 → 피곤
- 수면/불면/잠 → 수면
- 운동/스트레칭/홈트/근육/관절/허리 → 운동
- 피부/스킨케어/주름/탈모/자외선/미백 → 피부
- 음식/식단/레시피/요리/영양 → 음식
- 다이어트/체중/칼로리/비만 → 다이어트
- 비타민/영양제/아연/마그네슘/프로바이오틱스 → 영양제
- 봄/봄나물/꽃가루/환절기 → 봄
- 알레르기/비염 → 알레르기
- 미세먼지/황사 → 미세먼지
- 병원/건강검진/진료/질환/증상 → 의료
- 지원금/복지/연금/정부/신청 → 정부지원
- 보험/적금/금융 → 금융
- 면역/혈압/혈당/당뇨/콜레스테롤/혈관/간/장 → 건강
- 노트북/컴퓨터/PC/맥북/데스크탑 → IT_laptop
- 이어폰/헤드폰/스피커/음향/노이즈캔슬링 → IT_audio
- 스마트폰/아이폰/갤럭시/핸드폰 → IT_phone
- 키보드/마우스/게이밍 → IT_keyboard
- 코딩/소프트웨어/앱/프로그램/윈도우/크롬/PDF/클라우드 → IT_coding
- 모니터/디스플레이/웹캠/화면/액션캠 → IT_monitor
- AI/인공지능/ChatGPT/GPT → IT_ai
- 스마트워치/워치/웨어러블 → IT_watch
- 게이밍/게임 → IT_gaming
- SSD/RAM/하드/그래픽카드/USB/와이파이/배터리/충전기/보조배터리 → IT_general
"""


def _load_cache() -> dict[str, list[str]]:
    if _CACHE_FILE.exists():
        with open(_CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict[str, list[str]]) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def classify_keyword(keyword: str) -> list[str]:
    """키워드에 맞는 이미지 카테고리 1~2개를 반환한다.

    캐시에 있으면 즉시 반환, 없으면 GPT로 분류 후 캐시에 저장.
    """
    cache = _load_cache()

    # 캐시 히트
    if keyword in cache:
        logger.debug("캐시 히트: '%s' → %s", keyword, cache[keyword])
        return cache[keyword]

    # GPT 분류
    categories = _classify_with_gpt(keyword)

    # 캐시 저장
    cache[keyword] = categories
    _save_cache(cache)
    logger.info("GPT 분류: '%s' → %s", keyword, categories)
    return categories


def _classify_with_gpt(keyword: str) -> list[str]:
    """GPT-4.1-mini로 카테고리 분류. 실패 시 ['건강'] 반환."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        prompt = f"""블로그 포스트 키워드를 보고 가장 적합한 이미지 카테고리를 1~2개 골라주세요.

키워드: "{keyword}"

선택 가능 카테고리: {", ".join(VALID_CATEGORIES)}

{_CATEGORY_GUIDE}

규칙:
- 반드시 위 카테고리 목록에 있는 값만 사용
- JSON 배열 형식으로만 응답 (예: ["피곤"] 또는 ["IT_audio", "IT_general"])
- 설명 없이 JSON만"""

        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=40,
        )
        raw = resp.choices[0].message.content.strip()
        # JSON 파싱
        parsed = json.loads(raw)
        valid = [c for c in parsed if c in VALID_CATEGORIES]
        return valid if valid else ["건강"]

    except Exception as e:
        logger.warning("GPT 분류 실패 ('%s'): %s → 기본값 사용", keyword, e)
        return ["건강"]
