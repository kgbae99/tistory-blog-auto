"""쿠팡 파트너스 수익 링크 및 HTML 위젯 생성."""

from __future__ import annotations

from src.core.logger import setup_logger
from src.coupang.api_client import CoupangAPIClient
from src.coupang.product_search import Product

logger = setup_logger("coupang_link")

PRODUCT_WIDGET_TEMPLATE = """<div class="coupang-recommend" style="margin: 20px 0; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa;">
  <p style="font-size: 14px; color: #666; margin-bottom: 10px;">건강온도사 추천 제품</p>
  <a href="{affiliate_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: #333;">
    <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
      <img src="{image_url}" alt="{product_name}" style="width: 120px; height: 120px; object-fit: contain;" loading="lazy">
      <div style="flex: 1; min-width: 200px;">
        <h4 style="margin: 0 0 8px 0; font-size: 16px; line-height: 1.4;">{product_name}</h4>
        <p style="margin: 0 0 5px 0; font-size: 18px; font-weight: bold; color: #e44d26;">{price}원</p>
        <p style="margin: 0; font-size: 13px; color: #f5a623;">{stars} ({review_count}개 리뷰)</p>
        <span style="display: inline-block; margin-top: 8px; padding: 8px 20px; background: #e44d26; color: white; border-radius: 4px; font-size: 14px; font-weight: bold;">쿠팡에서 보기</span>
      </div>
    </div>
  </a>
</div>"""

DISCLAIMER_HTML = """<p style="font-size: 12px; color: #999; margin-top: 30px; padding-top: 10px; border-top: 1px solid #eee;">
이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
</p>"""


def _format_price(price: int) -> str:
    """가격을 천 단위 콤마 포맷으로 변환한다."""
    return f"{price:,}"


def _rating_to_stars(rating: float) -> str:
    """평점을 별 문자열로 변환한다."""
    full = int(rating)
    half = 1 if rating - full >= 0.5 else 0
    return "★" * full + "☆" * (5 - full - half)


def generate_affiliate_links(
    client: CoupangAPIClient, products: list[Product]
) -> list[tuple[Product, str]]:
    """상품 목록에서 수익 링크를 추출한다.

    쿠팡 검색 API 응답의 productUrl이 이미 수익 추적 링크이므로
    별도의 deeplink API 호출 없이 바로 사용한다.
    """
    if not products:
        return []

    results = [(p, p.product_url) for p in products]
    logger.info("%d개 수익 링크 생성 완료", len(results))
    return results


def generate_product_html(product: Product, affiliate_url: str) -> str:
    """상품 HTML 위젯을 생성한다."""
    rocket_badge = "🚀 로켓배송" if product.is_rocket else ""
    shipping = "무료배송" if product.is_free_shipping else ""
    badge = " | ".join(filter(None, [rocket_badge, shipping]))
    return PRODUCT_WIDGET_TEMPLATE.format(
        affiliate_url=affiliate_url,
        image_url=product.product_image,
        product_name=product.product_name,
        price=_format_price(product.product_price),
        stars=badge if badge else product.category_name,
        review_count=product.category_name,
    )


def generate_disclaimer() -> str:
    """쿠팡 파트너스 고지문 HTML을 반환한다."""
    return DISCLAIMER_HTML
