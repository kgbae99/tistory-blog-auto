"""일일 자동 발행 스크립트 - 매일 3개 포스트 생성 파이프라인."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adsense.ad_inserter import generate_ad_code, insert_ads_into_html
from src.content.generator import ContentRequest, generate_blog_content
from src.content.seo_optimizer import analyze_seo, optimize_content
from src.content.trend_analyzer import get_best_keyword_for_today
from src.core.config import load_config
from src.core.logger import setup_logger
from src.coupang.api_client import CoupangAPIClient
from src.coupang.link_generator import (
    generate_affiliate_links,
    generate_disclaimer,
    generate_product_html,
)
from src.coupang.product_search import search_and_filter
from src.tistory.auth import create_browser_context, save_session
from src.tistory.publisher import PostData, publish_post
from src.tistory.template import render_blog_post

logger = setup_logger("daily_publish")


async def generate_single_post(
    keyword: str,
    post_index: int,
    config: object,
    coupang_client: CoupangAPIClient,
    dry_run: bool = False,
) -> dict:
    """단일 포스트를 생성한다.

    Returns:
        {"keyword": str, "title": str, "html": str, "tags": list, "success": bool}
    """
    logger.info("--- 포스트 #%d 생성 시작: '%s' ---", post_index, keyword)

    try:
        # 1. 쿠팡 상품 검색
        products = search_and_filter(
            coupang_client, keyword, count=config.coupang.products_per_post
        )
        product_names = [p.product_name for p in products]
        logger.info("  [상품] %d개 검색 완료", len(products))

        # 2. 콘텐츠 생성
        content_request = ContentRequest(
            keyword=keyword,
            category="건강정보",
            product_names=product_names,
        )
        content = generate_blog_content(content_request, config.content)
        logger.info("  [콘텐츠] '%s' (%d자)", content.title, content.word_count)

        # 3. SEO 최적화
        content = optimize_content(content)
        seo_score = analyze_seo(content)
        logger.info("  [SEO] %d/100점", seo_score.total)

        # 4. 쿠팡 수익 링크 + HTML 위젯
        product_widgets = []
        if products:
            affiliate_links = generate_affiliate_links(coupang_client, products)
            for product, url in affiliate_links:
                widget_html = generate_product_html(product, url)
                product_widgets.append(widget_html)

        # 5. HTML 렌더링
        ad_slots = [
            generate_ad_code(config.adsense, position_index=i)
            for i in range(3)
        ]
        disclaimer = generate_disclaimer()
        today = datetime.now().strftime("%Y-%m-%d")

        final_html = render_blog_post(
            title=content.title,
            sections=content.sections,
            product_widgets=product_widgets,
            ad_slots=ad_slots,
            disclaimer=disclaimer,
            meta_description=content.meta_description,
            tags=content.tags,
            publish_date=today,
        )

        # 6. 애드센스 광고 삽입
        final_html = insert_ads_into_html(final_html, config.adsense)

        logger.info("  [완료] HTML %d자, 상품 %d개, 광고 삽입 완료", len(final_html), len(product_widgets))

        return {
            "keyword": keyword,
            "title": content.title,
            "html": final_html,
            "tags": content.tags,
            "meta_description": content.meta_description,
            "success": True,
        }

    except Exception as e:
        logger.error("  [실패] 포스트 #%d '%s': %s", post_index, keyword, e)
        return {"keyword": keyword, "title": "", "html": "", "tags": [], "success": False}


async def run_daily_publish(
    keyword: str | None = None,
    dry_run: bool = False,
    post_count: int = 3,
) -> list[str | None]:
    """전체 블로그 자동 발행 파이프라인을 실행한다.

    Args:
        keyword: 특정 키워드 지정 (None이면 자동 선택)
        dry_run: True이면 발행 없이 미리보기만
        post_count: 생성할 포스트 수 (기본 3)

    Returns:
        발행된 포스트 URL 리스트
    """
    config = load_config()
    now = datetime.now()
    logger.info(
        "=== 일일 자동 발행 시작 (%s) — %d개 포스트 ===",
        now.strftime("%Y-%m-%d %H:%M"), post_count,
    )

    # 키워드 선정
    if keyword:
        keywords = [keyword]
    else:
        keywords = []
        for i in range(post_count):
            kw = get_best_keyword_for_today(exclude=keywords)
            keywords.append(kw)
    logger.info("선정 키워드: %s", keywords)

    coupang_client = CoupangAPIClient(config.coupang)
    results = []
    published_urls = []

    # 포스트 순차 생성 (API rate limit 고려)
    for i, kw in enumerate(keywords, 1):
        result = await generate_single_post(
            keyword=kw,
            post_index=i,
            config=config,
            coupang_client=coupang_client,
            dry_run=dry_run,
        )
        results.append(result)

    # 저장 또는 발행
    output_dir = Path(__file__).parent.parent / "output" / "posts" / now.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        for i, result in enumerate(results, 1):
            if result["success"]:
                filepath = output_dir / f"post_{i}_{result['keyword'][:20]}.html"
                filepath.write_text(result["html"], encoding="utf-8")
                logger.info("[DRY RUN] 저장: %s", filepath.name)
                published_urls.append(None)
        logger.info("=== DRY RUN 완료: %d개 포스트 생성 ===", sum(1 for r in results if r["success"]))
    else:
        # 실제 발행
        browser, context = await create_browser_context(headless=True)
        try:
            for i, result in enumerate(results, 1):
                if not result["success"]:
                    published_urls.append(None)
                    continue

                post = PostData(
                    title=result["title"],
                    content_html=result["html"],
                    category="건강정보",
                    tags=result["tags"],
                    visibility="public",
                )
                url = await publish_post(context, config.tistory, post)
                published_urls.append(url)
                if url:
                    logger.info("[발행 완료] #%d: %s", i, url)
                else:
                    logger.error("[발행 실패] #%d: %s", i, result["title"])

                # 발행 간격 (티스토리 rate limit 방지)
                if i < len(results):
                    await asyncio.sleep(30)
        finally:
            await save_session(context)
            await browser.close()

        success_count = sum(1 for u in published_urls if u)
        logger.info("=== 발행 완료: %d/%d개 성공 ===", success_count, len(results))

    # HTML 파일은 항상 저장 (발행 여부 무관)
    for i, result in enumerate(results, 1):
        if result["success"]:
            filepath = output_dir / f"post_{i}_{result['keyword'][:20]}.html"
            if not filepath.exists():
                filepath.write_text(result["html"], encoding="utf-8")

    return published_urls


def main() -> None:
    """CLI 진입점."""
    import argparse

    parser = argparse.ArgumentParser(description="블로그 자동 발행")
    parser.add_argument("--keyword", "-k", type=str, help="발행할 키워드")
    parser.add_argument("--dry-run", action="store_true", help="발행 없이 미리보기만")
    parser.add_argument("--count", "-n", type=int, default=3, help="생성할 포스트 수 (기본 3)")
    args = parser.parse_args()

    results = asyncio.run(
        run_daily_publish(keyword=args.keyword, dry_run=args.dry_run, post_count=args.count)
    )

    success = sum(1 for r in results if r is not None)
    if success:
        print(f"\n발행 완료: {success}개")
    elif not args.dry_run:
        print("\n발행 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
