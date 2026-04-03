"""STEP 1 -- 롱테일 키워드 20개 자동 생성 (매일 1회).

실행:
    python scripts/step1_keywords.py
    python scripts/step1_keywords.py --blog it
    python scripts/step1_keywords.py --count 20

출력:
    data/pipeline/keywords_YYYY-MM-DD_{blog}.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

from src.core.logger import setup_logger

logger = setup_logger("step1_keywords")

PIPELINE_DIR = Path(__file__).parent.parent / "data" / "pipeline"
PIPELINE_DIR.mkdir(parents=True, exist_ok=True)

# -- 프롬프트 ------------------------------------------------------

HEALTH_KEYWORD_PROMPT = """당신은 한국 건강/다이어트 블로그 SEO 전문가입니다.

## 목표
구글 검색에서 실제로 유입되는 롱테일 키워드 {count}개를 생성하세요.

## 핵심 조건
1. **검색 의도가 명확**: 읽는 사람이 "정보 탐색" 또는 "구매 결정" 중 하나여야 함
2. **경쟁 낮은 키워드**: 포털 1페이지에 대형 사이트(네이버 지식인, 나무위키)만 있는 주제 피하기
   - 4~6단어 이상의 구체적 구문 사용
   - 특정 대상(40대 여성, 직장인, 50대 남성, 갱년기 등) + 구체적 상황 조합
3. **자연 검색 형태**: 실제 사람이 구글에 입력하는 방식 그대로
4. **"방법/이유/추천/후기/비교" 중 하나 반드시 포함**
5. **숫자·수치·기간 포함 우선** (예: 3개월, 5kg, 50대, 2주)

## 키워드 유형별 배분
- 수익형 (revenue) {revenue_count}개: 구매 의도 -- 영양제·보조제·식품 추천/비교/후기
  예: "50대 여성 마그네슘 영양제 추천 직접 비교", "다이어트 단백질 보충제 3개 먹어본 후기"
- 정보형 (info) {info_count}개: 탐색 의도 -- 원인·이유·방법 깊이 있는 정보
  예: "갱년기 여성 복부비만 생기는 진짜 이유", "혈당 스파이크 식후 30분 증상 놓치는 원인"

## 주제 풀 (골고루 사용)
- 다이어트: 간헐적 단식, 저탄고지, 공복, 체중 감량, 복부지방, 체지방
- 영양제: 마그네슘, 비타민D, 오메가3, 유산균, 콜라겐, 루테인, 아연, 철분, 코엔자임Q10
- 혈당/혈압: 공복혈당, 혈당 스파이크, 고혈압, 당뇨 전단계
- 관절/근육: 무릎 통증, 관절염, 근감소증, 허리 통증
- 수면/피로: 만성피로, 수면 장애, 불면증, 갱년기 수면
- 피부/탈모: 스트레스성 탈모, 피부 건조, 기미, 콜라겐
- 장 건강: 과민성 대장, 변비, 장누수, 유산균

## 이미 발행된 키워드 (겹치면 절대 안 됨)
{used_keywords}

## 출력 형식 (JSON만, 다른 텍스트 없음)
{{
  "keywords": [
    {{"keyword": "키워드", "type": "revenue", "intent": "구매 의도 한 줄 설명"}},
    {{"keyword": "키워드", "type": "info",    "intent": "탐색 의도 한 줄 설명"}},
    ...
  ]
}}"""

IT_KEYWORD_PROMPT = """당신은 한국 IT/테크 블로그 SEO 전문가입니다.

## 목표
구글 검색에서 실제로 유입되는 IT 롱테일 키워드 {count}개를 생성하세요.

## 핵심 조건
1. **검색 의도 명확**: 정보 탐색 또는 구매 결정 중 하나
2. **경쟁 낮은 키워드**: 4~6단어 이상, 특정 상황+제품 조합
3. **자연 검색 형태**: 실제 사람이 입력하는 방식
4. **"방법/이유/추천/후기/비교" 중 하나 반드시 포함**
5. **숫자·가격대·기간 포함 우선**

## 키워드 유형별 배분
- 수익형 (revenue) {revenue_count}개: 구매 의도 -- 제품 추천/비교/후기
  예: "3만원대 무선이어폰 직접 써본 솔직 후기", "재택근무 노트북 3개 비교해봤더니"
- 정보형 (info) {info_count}개: 탐색 의도 -- 원인·차이·방법
  예: "노트북 발열 심해지는 진짜 원인", "SSD vs HDD 실제 속도 차이 얼마나 날까"

## 주제 풀
- 음향: 무선이어폰, 노이즈캔슬링, 블루투스 스피커, 헤드셋
- 입력장치: 기계식 키보드, 무선 마우스, 트랙패드
- 컴퓨터: 노트북, SSD, RAM, 그래픽카드, 미니PC
- 모바일: 스마트폰 배터리, 보조배터리, 충전기
- 디스플레이: 모니터, 해상도, 블루라이트
- 생산성: 재택근무 세팅, 클라우드, AI 도구

## 이미 발행된 키워드 (겹치면 절대 안 됨)
{used_keywords}

## 출력 형식 (JSON만)
{{
  "keywords": [
    {{"keyword": "키워드", "type": "revenue", "intent": "의도 설명"}},
    ...
  ]
}}"""


# -- 핵심 함수 -----------------------------------------------------

def _load_used_keywords() -> list[str]:
    """기존 발행된 키워드 로드."""
    try:
        from src.content.dedup_checker import _load_published
        published = _load_published()
        return [p.get("keyword", p.get("title", "")) for p in published][-100:]
    except Exception:
        return []


def generate_keywords(blog: str, count: int) -> list[dict]:
    """GPT로 롱테일 키워드 {count}개를 생성한다."""
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    used = _load_used_keywords()
    used_str = json.dumps(used[-50:], ensure_ascii=False) if used else "[]"

    revenue_count = round(count * 0.6)  # 60% 수익형
    info_count    = count - revenue_count  # 40% 정보형

    template = HEALTH_KEYWORD_PROMPT if blog == "health" else IT_KEYWORD_PROMPT
    prompt = template.format(
        count=count,
        revenue_count=revenue_count,
        info_count=info_count,
        used_keywords=used_str,
    )

    client = openai.OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o",            # 키워드 품질이 핵심이므로 4o 사용
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content
    data = json.loads(raw)
    return data.get("keywords", [])


def deduplicate(keywords: list[dict]) -> list[dict]:
    """기존 발행 글과 중복 제거."""
    try:
        from src.content.dedup_checker import check_keyword_duplicate, check_title_duplicate
        result = []
        for item in keywords:
            kw = item["keyword"]
            if check_keyword_duplicate(kw):
                logger.debug("중복 키워드 제외: %s", kw)
                continue
            if check_title_duplicate(kw, threshold=0.6):
                logger.debug("유사 제목 제외: %s", kw)
                continue
            result.append(item)
        return result
    except Exception:
        return keywords


def save_keywords(today: str, blog: str, keywords: list[dict]) -> Path:
    """키워드 리스트를 파이프라인 파일로 저장한다."""
    # 수익형 / 정보형 분리
    revenue = [k for k in keywords if k.get("type") == "revenue"]
    info    = [k for k in keywords if k.get("type") == "info"]

    # 발행 순서 플랜 (수익형:정보형 = 2:1 반복)
    plan = []
    ri, ii = 0, 0
    slot = 0
    while len(plan) < len(keywords):
        if slot % 3 == 1 and ii < len(info):      # 2번째 슬롯 = 정보형
            plan.append({"keyword": info[ii]["keyword"], "post_type": "info",    "intent": info[ii].get("intent", "")})
            ii += 1
        elif ri < len(revenue):
            plan.append({"keyword": revenue[ri]["keyword"], "post_type": "revenue", "intent": revenue[ri].get("intent", "")})
            ri += 1
        elif ii < len(info):
            plan.append({"keyword": info[ii]["keyword"], "post_type": "info", "intent": info[ii].get("intent", "")})
            ii += 1
        else:
            break
        slot += 1

    result = {
        "date":        today,
        "blog":        blog,
        "total":       len(keywords),
        "revenue_cnt": len(revenue),
        "info_cnt":    len(info),
        "all_keywords": keywords,   # 전체 풀 (나중에 수동 선택 가능)
        "plan":        plan,        # 발행 순서 플랜
    }

    out_path = PIPELINE_DIR / f"keywords_{today}_{blog}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def print_report(keywords: list[dict], out_path: Path, blog: str) -> None:
    revenue = [k for k in keywords if k.get("type") == "revenue"]
    info    = [k for k in keywords if k.get("type") == "info"]

    print("\n" + "=" * 60)
    print("  [OK] STEP 1 완료 -- 키워드 생성 결과")
    print("=" * 60)
    print(f"  블로그  : {'건강온도사 (health)' if blog == 'health' else '테크온도 (IT)'}")
    print(f"  총 키워드: {len(keywords)}개  (수익형 {len(revenue)}개 / 정보형 {len(info)}개)")
    print(f"  저장 위치: {out_path}")
    print()

    print("  [money] 수익형 키워드 (구매 의도)")
    print("  " + "-" * 54)
    for i, k in enumerate(revenue, 1):
        print(f"  {i:>2}. {k['keyword']}")
        print(f"      └ {k.get('intent', '')}")
    print()

    print("  [info] 정보형 키워드 (탐색 의도)")
    print("  " + "-" * 54)
    for i, k in enumerate(info, 1):
        print(f"  {i:>2}. {k['keyword']}")
        print(f"      └ {k.get('intent', '')}")

    print()
    print(f"  >> 다음 단계: python scripts/step2_generate.py --blog {blog}")
    print("=" * 60)


# -- 메인 ---------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="STEP 1: 롱테일 키워드 자동 생성")
    parser.add_argument("--blog",  choices=["health", "it"], default="health")
    parser.add_argument("--count", type=int, default=20, help="생성할 키워드 수 (기본 20)")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")

    logger.info("=== STEP 1: 키워드 생성 시작 [%s / %d개] ===", args.blog, args.count)

    # 1. GPT 키워드 생성
    logger.info("GPT 키워드 생성 중...")
    try:
        raw_keywords = generate_keywords(args.blog, args.count)
        logger.info("GPT 생성: %d개", len(raw_keywords))
    except Exception as e:
        logger.error("GPT 생성 실패: %s", e)
        sys.exit(1)

    # 2. 중복 제거
    keywords = deduplicate(raw_keywords)
    logger.info("중복 제거 후: %d개", len(keywords))

    if not keywords:
        logger.error("유효한 키워드가 없습니다.")
        sys.exit(1)

    # 3. 저장
    out_path = save_keywords(today, args.blog, keywords)

    # 4. 결과 출력
    print_report(keywords, out_path, args.blog)


if __name__ == "__main__":
    main()
