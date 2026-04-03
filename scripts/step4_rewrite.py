"""STEP 4 -- 수익형 리라이팅 + 최종 HTML 조립.

이 단계 없으면 돈 안 됨.

리라이팅 4가지 강화:
  1. 광고 클릭 유도 문맥 -- 광고 앞뒤로 "지금 필요한 상황" 감정 연결
  2. CTA 2개 이상 -- 중간 CTA(문제 공감 직후) + 최종 CTA(결론 직전)
  3. 감정 유도 문장 -- 공감·불안·기대·안도 감정 트리거 강화
  4. 체류시간 구조 -- 궁금증 유발 → 답을 늦게 줌 → 다음 섹션 예고

정보형 포스트는 리라이팅 없이 조립.

실행:
    python scripts/step4_rewrite.py
    python scripts/step4_rewrite.py --blog it
    python scripts/step4_rewrite.py --draft data/pipeline/drafts_날짜/post_1.json  (단일 파일)

입력:  data/pipeline/drafts_YYYY-MM-DD_{blog}/post_*.json
출력:  output/posts/YYYY-MM-DD/*.html
"""

from __future__ import annotations

import argparse
import json
import os
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

logger = setup_logger("step4_rewrite")

PIPELINE_DIR = Path(__file__).parent.parent / "data" / "pipeline"

# -- 리라이팅 프롬프트 ---------------------------------------------

REWRITE_PROMPT = """## 핵심 지시 (정보글이 아니라 돈 되는 글을 만들어라)
너는 구글 SEO와 애드센스 수익 구조를 이해하는 블로그 전문가다.
검색 유입 → 체류 → 클릭 → 수익까지 이어지는 글을 만든다.
글의 구조·제목·도입부·키워드는 절대 변경하지 않는다. 수익 흐름만 강화한다.

## 아래 초안을 8가지 기준으로 리라이팅하세요

---

### ① 광고 클릭 유도 문맥 (가장 중요)
광고는 그냥 삽입하면 아무도 안 클릭합니다.
광고 바로 위에 독자가 "지금 당장 필요하다"고 느끼게 하는 문장이 있어야 합니다.

**문제 인식 직후 광고 앞** → 이런 문장 삽입:
  - "저도 이 문제로 몇 달을 고생했어요. 그때 이걸 알았더라면 훨씬 빨랐을 텐데요."
  - "혼자 해결하기 어렵다면, 이미 효과를 본 사람들이 선택한 방법이 있어요."

**해결책 직후 광고 앞** → 이런 문장 삽입:
  - "방법을 알아도 실천이 어렵다면, 이걸 함께 쓰면 훨씬 수월해집니다."
  - "제가 직접 써봤을 때 3주 만에 차이가 났어요. 아래에서 확인해보세요."

**결론 직전 광고 앞** → 이런 문장 삽입:
  - "지금 바로 시작하고 싶다면, 제가 추천하는 방법이 아래에 있어요."
  - "오늘 읽은 내용을 내일부터 실천할 수 있어요. 딱 하나만 챙겨가세요."

---

### ② CTA 2개 이상 삽입
**중간 CTA** (해결책 섹션 끝에 삽입):
```html
<div style="background:linear-gradient(135deg,#fff5f6,#ffe4e8);border-radius:12px;padding:22px;margin:28px 0;border-left:5px solid #e44d26;text-align:center;">
<p style="font-size:15px;color:#444;margin:0 0 6px 0;font-style:italic;">"이렇게 해봤는데도 잘 안 된다면?"</p>
<p style="font-size:18px;font-weight:bold;color:#2c3e50;margin:0 0 14px 0;">[구체적 대안 한 줄] 이 더 빠를 수 있어요</p>
<a href="[내부링크]" style="display:inline-block;padding:13px 34px;background:#e44d26;color:white;border-radius:8px;text-decoration:none;font-size:15px;font-weight:bold;box-shadow:0 3px 8px rgba(228,77,38,0.3);">지금 바로 확인하기 →</a>
</div>
```

**최종 CTA** (마무리 섹션 맨 끝에 삽입):
```html
<div style="background:linear-gradient(135deg,#fff5f6,#ffe4e8);border-radius:12px;padding:25px;margin:30px 0;text-align:center;border:2px solid #FFB6C1;">
<p style="font-size:13px;color:#888;margin:0 0 6px 0;">이 글을 읽고 나서 같이 보면 좋은 글</p>
<p style="font-size:18px;font-weight:bold;color:#2c3e50;margin:0 0 16px 0;">[pin] [다음 글 주제 -- 이 글의 자연스러운 다음 단계]</p>
<a href="[내부링크]" style="display:block;max-width:400px;margin:0 auto;padding:14px;background:#fff;border-radius:8px;text-decoration:none;color:#e44d26;font-weight:bold;font-size:15px;border:2px solid #FFB6C1;">👉 [다음 글 제목 한 줄] →</a>
</div>
```

---

### ③ 감정 유도 문장 강화
독자가 글을 끝까지 읽으려면 감정이 움직여야 합니다.
아래 4가지 감정 트리거를 글 전체에 분산 배치하세요.

**공감** (도입부·문제 섹션):
  - "저도 그랬어요", "많은 분들이 같은 실수를 해요", "이거 나만 그런 게 아니었어요"
  - [X] 금지: "많은 사람들이 고민합니다" (너무 평범)

**불안·긴박감** (원인 섹션):
  - "이걸 그냥 지나치면 나중에 더 힘들어질 수 있어요"
  - "모르고 계속 하면 오히려 역효과가 날 수 있습니다"

**기대** (해결책 섹션 직전):
  - "다행히 생각보다 간단한 방법이 있어요"
  - "저도 처음엔 몰랐는데, 이걸 알고 나서 완전히 달라졌어요"

**안도·확신** (경험 섹션):
  - "실제로 해보니까 [수치] 만에 [변화]가 있었어요"
  - "처음엔 반신반의했는데, [구체적 결과]가 나왔을 때 진짜라고 확신했어요"

---

### ④ 체류시간 증가 구조
독자가 다음 섹션으로 넘어가게 만드는 장치를 추가하세요.

**궁금증 유발** (각 섹션 끝에 한 줄):
  - "그런데 여기서 대부분이 놓치는 게 있어요. 다음 내용이 핵심입니다."
  - "이것만 알면 될 것 같지만, 사실 더 중요한 게 있어요."
  - "제가 3번 실패하고 나서야 알게 된 진짜 이유가 다음 섹션에 있어요."

**답을 늦게 주기** (해결책 섹션):
  - 결론을 바로 말하지 말고 "왜 이 방법이 효과적인지" 먼저 설명 후 방법 제시
  - 섹션 분량 300~500자 유지 (너무 짧으면 바로 이탈)

---

### ⑤ 제품 추천 타이밍 (전환율 핵심)
제품은 반드시 **문제 → 해결 → 경험 → 결과** 흐름을 거친 후에만 배치하세요.

**잘못된 순서** (금지):
  - 문제 설명 → 바로 제품 링크 (독자가 아직 공감 안 됨)
  - 해결책 나열 → 제품 링크 (신뢰 형성 전)

**올바른 순서** (필수):
  1. 문제 제기 + 공감 유도
  2. 혼자 해결하기 어려운 이유 설명
  3. "저도 [기간] 동안 [방법]을 써봤어요" 경험 서술
  4. "[수치] 만에 [변화]가 생겼어요" 결과 제시
  5. **이 시점에서만** 제품 블록 배치

**정보→구매 브릿지 문장 필수** (제품 블록 바로 위):
  - "음식만으로는 한계가 있었어요. 그래서 저는 이걸 함께 쓰기 시작했어요."
  - "방법은 알았지만 매일 챙기기 어렵더라고요. 이게 그 문제를 해결해줬어요."
  - "혼자 하기 힘들다면, 이미 많은 분들이 선택한 방법이 있어요."

---

### ⑥ 제품 가격 순서 + 선택 구조
**가격 순서**: 저가 → 중가 → 고가 순서로 배치 (부담감 최소화)

**선택 구조 카드 삽입** (제품 블록 앞에):
```html
<div style="display:flex;gap:12px;margin:20px 0;flex-wrap:wrap;">
  <div style="flex:1;min-width:200px;background:#f8f9fa;border-radius:8px;padding:16px;border-left:4px solid #e44d26;">
    <p style="font-size:13px;color:#666;margin:0 0 6px 0;">이런 분께 추천</p>
    <p style="font-size:15px;font-weight:bold;color:#2c3e50;margin:0;">[조건 A] → [저가 제품명]</p>
  </div>
  <div style="flex:1;min-width:200px;background:#f8f9fa;border-radius:8px;padding:16px;border-left:4px solid #2980b9;">
    <p style="font-size:13px;color:#666;margin:0 0 6px 0;">이런 분께 추천</p>
    <p style="font-size:15px;font-weight:bold;color:#2c3e50;margin:0;">[조건 B] → [고가 제품명]</p>
  </div>
</div>
```

---

### ⑦ 이미지 규칙
- 이미지는 **최대 3개** (글 전체 기준)
- 각 이미지의 alt 텍스트는 **모두 다르게** 작성 (중복 금지)
- alt 형식: "[주제 키워드] [구체적 상황 설명]" (예: "직장인 다이어트 식단 준비하는 모습")
- 같은 이미지 URL 두 번 이상 사용 금지

---

### ⑧ 스크롤 피로도 개선
- 박스(div 강조 블록) 연속 2개 이상 금지 — 박스 사이에 반드시 **텍스트 문단** 1개 이상 삽입
- 각 섹션의 첫 100자는 **순수 텍스트** 시작 (박스·리스트·표 금지)
- 리스트 3개 이상 연속 시 → 1~2개는 문단으로 풀어 쓸 것
- "핵심 요약", "한눈에 보기" 같은 중복 요약 박스 삽입 금지

---

## 리라이팅 대상 초안 JSON
{draft_json}

## 리라이팅 결과 점수 기준 (자체 평가)
리라이팅 후 아래를 확인하세요:
- [ ] 광고 앞에 감정 연결 문장이 있는가?
- [ ] CTA가 2개 이상인가?
- [ ] 각 섹션 끝에 다음 섹션으로 유도하는 문장이 있는가?
- [ ] 감정 트리거(공감/불안/기대/안도) 4가지가 모두 들어갔는가?
- [ ] 뻔한 내용("규칙적 운동", "충분한 수면")을 모두 제거했는가?

## 출력 규칙
- 수정된 JSON만 출력 (```json 블록, 다른 텍스트 없음)
- 원본 구조 유지: title, meta_description, sections, summary_cards, faq, tags
- sections[].content는 완전한 HTML (인라인 CSS 포함)
- 수정 불필요한 항목은 그대로 유지
"""


# -- 리라이팅 실행 -------------------------------------------------

def rewrite_revenue_post(draft: dict) -> dict:
    """GPT-4o로 수익형 초안을 리라이팅한다."""
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY 없음 -- 리라이팅 건너뜀")
        return draft["data"]

    # 섹션 content 길이 제한 (토큰 절약: 각 2000자)
    data_for_gpt = dict(draft["data"])
    data_for_gpt["sections"] = [
        {"heading": s.get("heading", ""), "content": s.get("content", "")[:2000]}
        for s in data_for_gpt.get("sections", [])
    ]

    prompt = REWRITE_PROMPT.format(
        draft_json=json.dumps(data_for_gpt, ensure_ascii=False, indent=2)
    )

    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o",           # 리라이팅 품질이 수익의 핵심 → 4o 사용
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=6000,
        )
        text = resp.choices[0].message.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        rewritten = json.loads(text.strip())

        before = draft["data"].get("title", "")
        after  = rewritten.get("title", "")
        logger.info("  제목 변경: '%s' → '%s'", before, after)
        return rewritten

    except Exception as e:
        logger.warning("  리라이팅 실패 (%s) -- 원본 사용", e)
        return draft["data"]


def score_rewrite(data: dict) -> dict[str, bool]:
    """리라이팅 결과 자체 점수 체크."""
    all_content = " ".join(s.get("content", "") for s in data.get("sections", []))

    cta_count = all_content.count("바로 확인하기") + all_content.count("읽으면 좋은 글") + \
                all_content.count("지금 바로") + all_content.count("확인하기 →")

    checks = {
        "광고 앞 감정 문장": any(x in all_content for x in [
            # 건강
            "몇 달을 고생", "훨씬 빨랐을", "3주 만에", "함께 쓰면",
            # IT
            "직접 써보니", "구매하고 나서", "실제로 사용해보니", "써본 결과",
            "이 제품 하나로", "바꾸고 나서",
        ]),
        "CTA 2개 이상":     cta_count >= 2,
        "섹션 유도 문장":   any(x in all_content for x in [
            "다음 내용이 핵심", "더 중요한 게", "진짜 이유가",
            "여기서 끝이 아닙니다", "그런데 더 중요한", "이게 전부가 아니에요",
        ]),
        "감정 트리거":      any(x in all_content for x in [
            # 건강
            "저도 그랬어요", "역효과", "완전히 달라졌", "확신했어요",
            # IT
            "후회했어요", "살걸 그랬어요", "진작 살걸", "이걸 왜 이제야",
            "돈이 아깝지 않았", "가성비가 맞았", "실망하지 않았",
        ]),
        "뻔한 내용 제거":   "규칙적인 운동" not in all_content and "충분한 수면" not in all_content,
    }
    return checks


# -- HTML 빌더 -----------------------------------------------------

def build_html_health(data: dict, products_raw: list, post_index: int, keyword: str, post_type: str) -> str:
    from scripts.generate_daily_posts import build_full_html
    from src.coupang.product_search import Product

    products = []
    for p in products_raw:
        try:
            products.append(Product(**{k: v for k, v in p.items() if k in Product.__dataclass_fields__}))
        except Exception:
            pass
    return build_full_html(data, products, post_index, keyword=keyword, post_type=post_type)


def build_html_it(data: dict, products_raw: list, keyword: str, post_date: str, post_index: int, post_type: str) -> str:
    from scripts.generate_it_posts import build_full_html
    return build_full_html(data, keyword, products_raw, post_date, post_index=post_index, post_type=post_type)


def build_tool_page_health(title: str, tags: list, html: str, meta_desc: str) -> str:
    from scripts.generate_daily_posts import build_tool_page
    return build_tool_page(title, tags, html, meta_desc)


def build_tool_page_it(title: str, tags: list, html: str, meta_desc: str) -> str:
    from scripts.generate_it_posts import build_tool_page
    return build_tool_page(title, tags, html, meta_desc)


# -- 단일 포스트 처리 ----------------------------------------------

def process_draft(draft_path: Path, blog: str, today: str, output_dir: Path) -> dict | None:
    draft     = json.loads(draft_path.read_text(encoding="utf-8"))
    keyword   = draft["keyword"]
    post_type = draft["post_type"]
    post_index = draft["index"]
    tag = "[money] 수익형" if post_type == "revenue" else "[info] 정보형"
    logger.info("[%d] %s  '%s'", post_index, tag, keyword)

    # 수익형만 리라이팅
    if post_type == "revenue":
        logger.info("  리라이팅 중... (GPT-4o)")
        data = rewrite_revenue_post(draft)

        # 자체 점수 체크
        checks = score_rewrite(data)
        passed = sum(checks.values())
        total  = len(checks)
        logger.info("  품질 체크: %d/%d 통과", passed, total)
        for item, ok in checks.items():
            logger.debug("    [%s] %s", "[OK]" if ok else "[X]", item)
    else:
        logger.info("  정보형 -- 리라이팅 건너뜀")
        data   = draft["data"]
        checks = {}

    products_raw = draft.get("products", [])
    title     = data.get("title", keyword)
    tags      = data.get("tags", [keyword])
    meta_desc = data.get("meta_description", "")

    # HTML 조립
    if blog == "health":
        blog_html = build_html_health(data, products_raw, post_index, keyword, post_type)
        tool_html = build_tool_page_health(title, tags, blog_html, meta_desc)
    else:
        blog_html = build_html_it(data, products_raw, keyword, today, post_index, post_type)
        tool_html = build_tool_page_it(title, tags, blog_html, meta_desc)

    safe_name = re.sub(r'[\\/:*?"<>|]', '', keyword).replace(" ", "_")[:30]
    filepath  = output_dir / f"post_{post_index}_{safe_name}.html"
    filepath.write_text(tool_html, encoding="utf-8")
    logger.info("  저장: %s", filepath)

    return {
        "index":    post_index,
        "type":     post_type,
        "keyword":  keyword,
        "title":    title,
        "file":     str(filepath),
        "checks":   checks,
        "word_count": len(" ".join(s.get("content","") for s in data.get("sections",[]))),
    }


# -- 결과 출력 -----------------------------------------------------

def print_report(results: list[dict], output_dir: Path) -> None:
    print("\n" + "=" * 64)
    print("  [OK] STEP 4 완료 -- 수익형 리라이팅 결과")
    print("=" * 64)
    for r in results:
        tag = "[money] 수익형" if r["type"] == "revenue" else "[info] 정보형"
        print(f"\n  [{r['index']}] {tag}")
        print(f"       키워드   : {r['keyword']}")
        print(f"       최종 제목: {r['title']}")
        print(f"       분량     : 약 {r['word_count']:,}자")
        print(f"       파일     : {r['file']}")

        if r.get("checks"):
            passed = sum(r["checks"].values())
            total  = len(r["checks"])
            print(f"       품질 점수: {passed}/{total}")
            for item, ok in r["checks"].items():
                print(f"                  {'[OK]' if ok else '[X]'} {item}")

    print(f"\n  출력 위치: {output_dir}")
    print("=" * 64)


# -- 메인 ---------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="STEP 4: 수익형 리라이팅 + HTML 조립")
    parser.add_argument("--blog",  choices=["health", "it"], default="health")
    parser.add_argument("--draft", type=str, default=None, help="단일 초안 파일 직접 지정 (예: data/pipeline/drafts_.../post_1.json)")
    args = parser.parse_args()

    today      = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(__file__).parent.parent / "output" / "posts" / today
    output_dir.mkdir(parents=True, exist_ok=True)

    # 단일 파일 모드
    if args.draft:
        draft_path = Path(args.draft)
        if not draft_path.exists():
            print(f"파일 없음: {draft_path}")
            sys.exit(1)
        blog = json.loads(draft_path.read_text(encoding="utf-8")).get("blog", args.blog)
        result = process_draft(draft_path, blog, today, output_dir)
        if result:
            print_report([result], output_dir)
        return

    # 파이프라인 모드
    draft_dir = PIPELINE_DIR / f"drafts_{today}_{args.blog}"
    if not draft_dir.exists():
        print(f"초안 디렉토리 없음: {draft_dir}")
        print("먼저 step3_generate.py 를 실행하세요.")
        sys.exit(1)

    draft_files = sorted(draft_dir.glob("post_*.json"))
    logger.info("=== STEP 4: 리라이팅 + HTML 조립 [%s] %d개 ===", args.blog, len(draft_files))

    results = []
    for draft_path in draft_files:
        r = process_draft(draft_path, args.blog, today, output_dir)
        if r:
            results.append(r)

    print_report(results, output_dir)


if __name__ == "__main__":
    main()
