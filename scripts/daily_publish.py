"""일일 자동 발행 스크립트 - 전체 파이프라인 실행."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
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


async def run_daily_publish(keyword: str | None = None, dry_run: bool = False) -> str | None:
    """전체 블로그 자동 발행 파이프라인을 실행한다.

    Args:
        keyword: 특정 키워드 지정 (None이면 자동 선택)
        dry_run: True이면 발행 없이 미리보기만

    Returns:
        발행된 포스트 URL 또는 None
    """
    config = load_config()
    logger.info("=== 일일 자동 발행 시작 (%s) ===", datetime.now().strftime("%Y-%m-%d %H:%M"))

    # 1. 키워드 선정 (트렌드 + 시즌 자동 선택)
    if keyword is None:
        keyword = get_best_keyword_for_today()
    logger.info("[1/7] 키워드 선정: '%s'", keyword)

    # 2. 쿠팡 상품 검색
    logger.info("[2/7] 쿠팡 상품 검색 중...")
    coupang_client = CoupangAPIClient(config.coupang)
    products = search_and_filter(coupang_client, keyword, count=config.coupang.products_per_post)
    product_names = [p.product_name for p in products]
    logger.info("  → %d개 상품 선택", len(products))

    # 3. 콘텐츠 생성
    logger.info("[3/7] Claude API 콘텐츠 생성 중...")
    content_request = ContentRequest(
        keyword=keyword,
        category="건강정보",
        product_names=product_names,
    )
    content = generate_blog_content(content_request, config.content)
    logger.info("  → '%s' (%d자)", content.title, content.word_count)

    # 4. SEO 최적화
    logger.info("[4/7] SEO 최적화 중...")
    content = optimize_content(content)
    seo_score = analyze_seo(content)
    logger.info("  → SEO 점수: %d/100", seo_score.total)
    if seo_score.issues:
        for issue in seo_score.issues:
            logger.warning("  SEO 이슈: %s", issue)

    # 5. 쿠팡 수익 링크 생성 & HTML 위젯
    logger.info("[5/7] 쿠팡 수익 링크 생성 중...")
    product_widgets = []
    if products:
        affiliate_links = generate_affiliate_links(coupang_client, products)
        for product, url in affiliate_links:
            widget_html = generate_product_html(product, url)
            product_widgets.append(widget_html)

    # 6. HTML 렌더링
    logger.info("[6/7] HTML 렌더링 중...")
    ad_slots = [generate_ad_code(config.adsense) for _ in range(3)]
    disclaimer = generate_disclaimer()

    final_html = render_blog_post(
        title=content.title,
        sections=content.sections,
        product_widgets=product_widgets,
        ad_slots=ad_slots,
        disclaimer=disclaimer,
        meta_description=content.meta_description,
        tags=content.tags,
    )

    # 광고 삽입 (추가 위치)
    final_html = insert_ads_into_html(final_html, config.adsense)

    if dry_run:
        logger.info("[DRY RUN] 발행 스킵, HTML 생성 완료 (%d자)", len(final_html))
        output_path = Path(__file__).parent.parent / "output" / f"preview_{keyword}.html"
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(final_html, encoding="utf-8")
        logger.info("미리보기 저장: %s", output_path)
        return None

    # 7. 티스토리 발행
    logger.info("[7/7] 티스토리 발행 중...")
    browser, context = await create_browser_context(headless=True)
    try:
        post = PostData(
            title=content.title,
            content_html=final_html,
            category="건강정보",
            tags=content.tags,
            visibility="public",
        )
        published_url = await publish_post(context, config.tistory, post)
        if published_url:
            logger.info("=== 발행 완료: %s ===", published_url)
        else:
            logger.error("=== 발행 실패 ===")
        return published_url
    finally:
        await save_session(context)
        await browser.close()


def main() -> None:
    """CLI 진입점."""
    import argparse

    parser = argparse.ArgumentParser(description="블로그 자동 발행")
    parser.add_argument("--keyword", "-k", type=str, help="발행할 키워드")
    parser.add_argument("--dry-run", action="store_true", help="발행 없이 미리보기만")
    args = parser.parse_args()

    result = asyncio.run(run_daily_publish(keyword=args.keyword, dry_run=args.dry_run))
    if result:
        print(f"\n발행 완료: {result}")
    elif not args.dry_run:
        print("\n발행 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
