"""STEP 3 -- 키워드별 블로그 초안 생성.

실행 (파이프라인):
    python scripts/step3_generate.py
    python scripts/step3_generate.py --blog it

실행 (단일 키워드 직접 입력):
    python scripts/step3_generate.py --keyword "직장인 다이어트 실패 이유"
    python scripts/step3_generate.py --keyword "직장인 다이어트 실패 이유" --type revenue
    python scripts/step3_generate.py --keyword "SSD 교체 후 속도 비교" --blog it --type revenue

입력:  data/pipeline/keywords_YYYY-MM-DD_{blog}.json  (파이프라인 모드)
출력:  data/pipeline/drafts_YYYY-MM-DD_{blog}/post_*.json
"""

from __future__ import annotations

import argparse
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

from src.core.logger import setup_logger

logger = setup_logger("step3_generate")

PIPELINE_DIR = Path(__file__).parent.parent / "data" / "pipeline"


# -- 키워드 로드 ---------------------------------------------------

def load_plan_from_file(today: str, blog: str) -> list[dict]:
    """파이프라인 파일에서 발행 플랜 로드."""
    path = PIPELINE_DIR / f"keywords_{today}_{blog}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"키워드 파일 없음: {path}\n"
            "먼저 step1_keywords.py → step2_filter.py 를 실행하거나\n"
            "--keyword '키워드' 로 직접 입력하세요."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    plan = data.get("plan", [])
    if not plan:
        raise ValueError("발행 플랜이 비어 있습니다. step2_filter.py 를 먼저 실행하세요.")
    source = "필터링된" if "filtered" in data else "원본"
    logger.info("키워드 플랜 로드 (%s): %d개", source, len(plan))
    return plan


# -- 생성 함수 -----------------------------------------------------

def generate_health(keyword: str, post_type: str, products: list) -> dict:
    from scripts.generate_daily_posts import generate_content
    return generate_content(keyword, products, post_type=post_type)


def generate_it(keyword: str, post_type: str, products: list) -> dict | None:
    from scripts.generate_it_posts import generate_content
    return generate_content(keyword, products, post_type=post_type)


def search_products_health(keyword: str) -> list:
    from scripts.generate_daily_posts import search_coupang_products
    return search_coupang_products(keyword)


def search_products_it(keyword: str) -> list:
    from scripts.generate_it_posts import search_coupang_products
    return search_coupang_products(keyword)


def serialize_products(products: list) -> list[dict]:
    result = []
    for p in products:
        if hasattr(p, "__dict__"):
            result.append(vars(p))
        elif isinstance(p, dict):
            result.append(p)
    return result


# -- 단일 포스트 생성 ----------------------------------------------

def generate_one(
    keyword: str,
    post_type: str,
    blog: str,
    index: int,
    draft_dir: Path,
) -> dict | None:
    """키워드 1개로 초안을 생성하고 저장한다."""
    tag = "[money] 수익형" if post_type == "revenue" else "[info] 정보형"
    logger.info("[%d] %s  '%s'", index, tag, keyword)

    # 쿠팡 상품 (수익형만)
    products = []
    if post_type == "revenue":
        logger.info("  쿠팡 상품 검색 중...")
        products = search_products_health(keyword) if blog == "health" else search_products_it(keyword)
        logger.info("  쿠팡 상품: %d개", len(products))

    # 콘텐츠 생성
    logger.info("  콘텐츠 생성 중...")
    data = generate_health(keyword, post_type, products) if blog == "health" else generate_it(keyword, post_type, products)

    if not data:
        logger.error("  생성 실패: %s", keyword)
        return None

    draft = {
        "index":    index,
        "keyword":  keyword,
        "post_type": post_type,
        "blog":     blog,
        "title":    data.get("title", ""),
        "data":     data,
        "products": serialize_products(products),
    }

    out_path = draft_dir / f"post_{index}.json"
    out_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("  제목: %s", data.get("title", ""))
    logger.info("  저장: %s", out_path)
    return draft


# -- 결과 출력 -----------------------------------------------------

def print_report(results: list[dict], draft_dir: Path, blog: str) -> None:
    print("\n" + "=" * 60)
    print("  [OK] STEP 3 완료 -- 초안 생성 결과")
    print("=" * 60)
    for r in results:
        tag = "[money] 수익형" if r["post_type"] == "revenue" else "[info] 정보형"
        word_count = len(" ".join(
            s.get("content", "") for s in r["data"].get("sections", [])
        ))
        sections = len(r["data"].get("sections", []))
        print(f"  [{r['index']}] {tag}")
        print(f"       키워드: {r['keyword']}")
        print(f"       제목  : {r['title']}")
        print(f"       섹션  : {sections}개 / 약 {word_count:,}자")
        print(f"       상품  : {len(r['products'])}개")
        print()
    print(f"  초안 위치: {draft_dir}")
    print(f"  >> 다음 단계: python scripts/step4_rewrite.py --blog {blog}")
    print("=" * 60)


# -- 메인 ---------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="STEP 3: 블로그 초안 생성")
    parser.add_argument("--blog",    choices=["health", "it"], default="health")
    parser.add_argument("--keyword", type=str, default=None,   help="단일 키워드 직접 입력 (파이프라인 파일 불필요)")
    parser.add_argument("--type",    choices=["revenue", "info"], default="revenue", help="포스트 유형 (--keyword 사용 시)")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    draft_dir = PIPELINE_DIR / f"drafts_{today}_{args.blog}"
    # 이전 실행 잔여 초안 제거 (누적 방지 — step4가 불필요한 파일 처리하는 문제 방지)
    if draft_dir.exists():
        import shutil
        shutil.rmtree(draft_dir)
    draft_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== STEP 3: 초안 생성 [%s] ===", args.blog)

    # -- 단일 키워드 직접 모드 --------------------------------------
    if args.keyword:
        # step2_filter 기준 사전 검사
        from scripts.step2_filter import is_too_short, is_blacklisted, has_intent, score_keyword
        kw = args.keyword.strip()

        print(f"\n🔍 키워드 품질 검사: '{kw}'")
        if is_too_short(kw):
            print(f"  ⚠️  경고: 키워드가 짧습니다 ({len(kw.split())}단어). 계속 진행합니다.")
        elif is_blacklisted(kw):
            print(f"  ⚠️  경고: 범용 키워드입니다. 계속 진행합니다.")
        elif not has_intent(kw):
            print(f"  ⚠️  경고: 검색 의도 신호가 없습니다. 계속 진행합니다.")
        else:
            score, reasons = score_keyword(kw)
            print(f"  [OK] 품질 점수: {score:+d}점  ({' / '.join(reasons)})")

        # 기존 초안 번호 이어받기
        existing = sorted(draft_dir.glob("post_*.json"))
        index = len(existing) + 1

        result = generate_one(kw, args.type, args.blog, index, draft_dir)
        if result:
            print_report([result], draft_dir, args.blog)
        return

    # -- 파이프라인 모드 --------------------------------------------
    try:
        plan = load_plan_from_file(today, args.blog)
    except (FileNotFoundError, ValueError) as e:
        print(f"\n[X] {e}")
        sys.exit(1)

    results = []
    for i, item in enumerate(plan, 1):
        r = generate_one(item["keyword"], item["post_type"], args.blog, i, draft_dir)
        if r:
            results.append(r)

    if results:
        print_report(results, draft_dir, args.blog)


if __name__ == "__main__":
    main()
