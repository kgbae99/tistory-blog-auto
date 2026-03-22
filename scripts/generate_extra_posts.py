"""특정 키워드 또는 GPT 추천으로 추가 포스트를 생성한다."""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

import openai

from src.analytics.dashboard import register_post
from src.content.dedup_checker import check_keyword_duplicate, check_title_duplicate, register_published
from src.core.logger import setup_logger

# generate_daily_posts의 함수들 재사용
from scripts.generate_daily_posts import (
    generate_content,
    search_coupang_products,
    build_full_html,
    build_tool_page,
    _load_all_used_keywords,
    filter_unique_keywords,
)

logger = setup_logger("extra_posts")


def get_gpt_keywords(count: int = 3, exclude: list[str] | None = None) -> list[str]:
    """GPT로 새 키워드를 추천받는다."""
    used = _load_all_used_keywords()
    if exclude:
        used.extend(exclude)
    recent = used[-100:] if len(used) > 100 else used

    prompt = f"""당신은 건강/생활/뷰티 블로그 키워드 전문가입니다.

아래는 이미 발행된 블로그 글 제목/키워드 목록입니다:
{json.dumps(recent, ensure_ascii=False)}

위 목록과 겹치지 않는 새로운 블로그 포스트 키워드 {count + 3}개를 추천해주세요.

조건:
- 주제: 건강/질병, 음식/영양, 뷰티/생활 중에서 골고루
- 20~60대 관심사 (건강관리, 영양제, 생활습관, 피부, 다이어트 등)
- 검색량이 있는 실용적인 주제
- 이미 발행된 글과 유사하거나 겹치는 주제 절대 금지
- JSON 형식으로만 출력

반드시 아래 JSON 형식으로만 출력:
{{"keywords": ["키워드1", "키워드2", "키워드3"]}}"""

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=300,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    keywords = data.get("keywords", [])
    logger.info("GPT 추천 키워드: %s", keywords)
    return keywords


def main(count: int = 2, extra_exclude: list[str] | None = None):
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(__file__).parent.parent / "output" / "posts" / today
    output_dir.mkdir(parents=True, exist_ok=True)

    # 기존 오늘 파일 번호 파악
    existing = list(output_dir.glob("post_*.html"))
    next_num = len(existing) + 1

    # GPT 키워드 추천
    exclude = extra_exclude or []
    raw = get_gpt_keywords(count, exclude=exclude)

    # 중복 필터
    keywords = filter_unique_keywords(raw)[:count]
    if len(keywords) < count:
        logger.warning("%d개 요청했지만 %d개만 통과", count, len(keywords))

    results = []
    for i, keyword in enumerate(keywords):
        num = next_num + i
        logger.info("[%d/%d] 키워드: '%s'", i + 1, len(keywords), keyword)

        products = search_coupang_products(keyword)
        data = generate_content(keyword, products)
        logger.info("  제목: %s", data.get("title", ""))

        title = data.get("title", keyword)
        dup = check_title_duplicate(title)
        if dup:
            logger.warning("  제목 중복 감지: %s", dup["existing_title"][:30])

        blog_html = build_full_html(data, products, post_index=num, keyword=keyword)
        tool_html = build_tool_page(title, data.get("tags", []), blog_html, data.get("meta_description", ""))

        safe_kw = keyword.replace(" ", "_").replace("/", "_")
        filename = f"post_{num}_{safe_kw}.html"
        filepath = output_dir / filename
        filepath.write_text(tool_html, encoding="utf-8")
        logger.info("  저장: %s", filepath)

        register_published(title=title, keyword=keyword, date=today)
        register_post(
            title=title, keyword=keyword, category="건강정보",
            tags=data.get("tags", []), coupang_products=len(products), adsense_slots=3,
        )

        results.append({"keyword": keyword, "title": title, "file": str(filepath)})

        if i < len(keywords) - 1:
            time.sleep(3)

    print("\n=== 생성 완료 ===")
    for r in results:
        print(f"  {r['title']} → {Path(r['file']).name}")

    return results


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    # 오늘 이미 있는 포스트 제외
    exclude_today = ["손목터널증후군 자가치료"]
    main(count=count, extra_exclude=exclude_today)
