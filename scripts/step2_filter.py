"""STEP 2 -- 키워드 필터링 및 품질 점수 순위 정렬.

필터링 기준:
  [X] 제거: 단어 3개 미만 / 10자 미만 (너무 짧음)
  [X] 제거: 구매/문제해결 의도 없는 순수 정보성
  [X] 제거: 블랙리스트 단어만 있는 범용 키워드
  [OK] 유지: 롱테일 + 방법/이유/추천/후기/비교 포함
  [OK] 유지: 타겟 대상(40대/직장인) + 구체적 문제/행동

점수 기준:
  +3 구매 의도 (추천, 후기, 비교, 써봤더니, 먹어봤더니)
  +2 숫자·수치 포함 (3개월, 5kg, 50대, 2주)
  +2 타겟 대상 (40대, 직장인, 여성, 갱년기, 남성)
  +1 문제 해결 (방법, 이유, 원인, 해결, 줄이는, 빼는)
  +1 비교·차이 (vs, 차이, 비교, 다른점)
  -2 너무 일반적 (범용 단어만)

실행:
    python scripts/step2_filter.py
    python scripts/step2_filter.py --blog it
    python scripts/step2_filter.py --top 10   (상위 N개만 선택)

입력:  data/pipeline/keywords_YYYY-MM-DD_{blog}.json
출력:  data/pipeline/keywords_YYYY-MM-DD_{blog}.json  (filtered 필드 추가)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

from src.core.logger import setup_logger

logger = setup_logger("step2_filter")

PIPELINE_DIR = Path(__file__).parent.parent / "data" / "pipeline"

# -- 필터 기준 -----------------------------------------------------

# 즉시 제거 -- 단독으로 쓰이면 범용 키워드
BLACKLIST_STANDALONE = {
    "다이어트", "건강", "영양제", "음식", "운동", "식단",
    "피부", "탈모", "비타민", "단백질", "수면", "피로",
    "IT", "노트북", "이어폰", "키보드", "마우스", "스마트폰",
}

# 포함 필수 (최소 1개) -- 검색 의도 신호
INTENT_SIGNALS = [
    "방법", "이유", "원인", "추천", "후기", "비교", "효과",
    "써봤더니", "먹어봤더니", "해봤더니", "직접",
    "줄이는", "빼는", "높이는", "낮추는", "개선",
    "선택", "차이", "해결", "고르는", "골라봤더니",
    "달라진", "결과", "성공", "실패", "경험",
]

# 점수 기준
SCORE_RULES = [
    # (패턴 리스트, 점수, 설명)
    (["추천", "후기", "비교", "써봤더니", "먹어봤더니", "골라봤더니", "달라진"], 3, "구매 의도"),
    (["방법", "이유", "원인", "해결", "줄이는", "빼는", "높이는", "낮추는", "개선"], 1, "문제 해결"),
    (["vs", "차이", "비교", "다른점", "어떤게"], 1, "비교 탐색"),
    (["40대", "50대", "30대", "60대", "직장인", "여성", "남성", "갱년기", "임산부", "중년", "노인"], 2, "타겟 대상"),
    (["만원대", "개월", "주일", "kg", "%", "mg", "iu", "개 비교", "가지", "번"], 2, "숫자·수치"),
    (["솔직", "직접", "실제", "진짜", "경험담"], 1, "신뢰 신호"),
]


# -- 필터 함수 -----------------------------------------------------

def is_too_short(kw: str) -> bool:
    """단어 3개 미만 또는 10자 미만이면 제거."""
    words = kw.strip().split()
    return len(words) < 3 or len(kw.replace(" ", "")) < 10


def is_blacklisted(kw: str) -> bool:
    """블랙리스트 단어만으로 구성된 키워드 제거."""
    words = set(kw.strip().split())
    return words.issubset(BLACKLIST_STANDALONE)


def has_intent(kw: str) -> bool:
    """검색 의도 신호 단어가 하나도 없으면 제거."""
    kw_lower = kw.lower()
    return any(signal in kw_lower for signal in INTENT_SIGNALS)


def score_keyword(kw: str) -> tuple[int, list[str]]:
    """키워드 품질 점수 계산. (점수, 매칭된 이유 리스트) 반환."""
    kw_lower = kw.lower()
    total = 0
    reasons = []
    for patterns, pts, label in SCORE_RULES:
        if any(p in kw_lower for p in patterns):
            total += pts
            reasons.append(f"+{pts} {label}")
    return total, reasons


def filter_keywords(keywords: list[dict]) -> tuple[list[dict], list[dict]]:
    """필터 통과 / 탈락 키워드 분리.

    Returns:
        (passed, rejected)  -- 각각 score 필드 포함
    """
    passed, rejected = [], []

    for item in keywords:
        kw = item["keyword"]
        reject_reason = None

        if is_too_short(kw):
            reject_reason = f"너무 짧음 ({len(kw.split())}단어 / {len(kw)}자)"
        elif is_blacklisted(kw):
            reject_reason = "범용 키워드 (블랙리스트)"
        elif not has_intent(kw):
            reject_reason = "검색 의도 신호 없음"

        if reject_reason:
            rejected.append({**item, "reject_reason": reject_reason})
        else:
            score, reasons = score_keyword(kw)
            passed.append({**item, "score": score, "score_reasons": reasons})

    # 점수 내림차순 정렬
    passed.sort(key=lambda x: x["score"], reverse=True)
    return passed, rejected


def rebuild_plan(passed: list[dict], top_n: int) -> list[dict]:
    """필터 통과 키워드로 발행 플랜을 재구성 (수익형:정보형 = 2:1 반복)."""
    selected = passed[:top_n]
    revenue = [k for k in selected if k.get("type") == "revenue"]
    info    = [k for k in selected if k.get("type") == "info"]

    plan = []
    ri, ii, slot = 0, 0, 0
    while len(plan) < len(selected):
        if slot % 3 == 1 and ii < len(info):
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

    return plan


def print_report(passed: list[dict], rejected: list[dict], top_n: int, out_path: Path) -> None:
    print("\n" + "=" * 64)
    print("  [OK] STEP 2 완료 -- 키워드 필터링 결과")
    print("=" * 64)
    print(f"  입력: {len(passed) + len(rejected)}개  →  통과: {len(passed)}개  /  제거: {len(rejected)}개")
    print(f"  발행 선택: 상위 {min(top_n, len(passed))}개")
    print()

    print("  [OK] 통과 키워드 (점수 순)")
    print("  " + "-" * 60)
    for i, k in enumerate(passed, 1):
        badge = "[money]" if k.get("type") == "revenue" else "[info]"
        score_str = " ".join(k.get("score_reasons", []))
        selected = " << 선택" if i <= top_n else ""
        print(f"  {i:>2}. {badge} [{k['score']:+d}] {k['keyword']}{selected}")
        if score_str:
            print(f"       └ {score_str}")
    print()

    if rejected:
        print("  [X] 제거된 키워드")
        print("  " + "-" * 60)
        for k in rejected:
            print(f"     * {k['keyword']}  ← {k['reject_reason']}")
    print()
    print(f"  저장: {out_path}")
    print(f"  >> 다음 단계: python scripts/step3_generate.py")
    print("=" * 64)


# -- 메인 ---------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="STEP 2: 키워드 필터링")
    parser.add_argument("--blog",  choices=["health", "it"], default="health")
    parser.add_argument("--top",   type=int, default=10, help="발행 플랜에 선택할 상위 N개 (기본 10)")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    kw_path = PIPELINE_DIR / f"keywords_{today}_{args.blog}.json"

    if not kw_path.exists():
        print(f"키워드 파일 없음: {kw_path}")
        print("먼저 step1_keywords.py 를 실행하세요.")
        sys.exit(1)

    data = json.loads(kw_path.read_text(encoding="utf-8"))
    raw = data.get("all_keywords", [])

    logger.info("=== STEP 2: 키워드 필터링 [%s / 입력 %d개] ===", args.blog, len(raw))

    passed, rejected = filter_keywords(raw)
    logger.info("통과: %d개 / 제거: %d개", len(passed), len(rejected))

    if not passed:
        print("통과한 키워드가 없습니다. step1_keywords.py 를 다시 실행해 새 키워드를 생성하세요.")
        sys.exit(1)

    # 발행 플랜 재구성
    plan = rebuild_plan(passed, args.top)

    # 파일 업데이트
    data["filtered"]      = passed
    data["rejected"]      = rejected
    data["plan"]          = plan
    data["filter_top_n"]  = args.top
    kw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print_report(passed, rejected, args.top, kw_path)


if __name__ == "__main__":
    main()
