"""쿠팡 상품 검색 및 필터링."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.logger import setup_logger
from src.coupang.api_client import CoupangAPIClient

logger = setup_logger("coupang_search")


@dataclass
class Product:
    """쿠팡 상품 데이터."""

    product_id: str
    product_name: str
    product_price: int
    product_image: str
    product_url: str
    review_count: int
    rating: float
    is_rocket: bool
    category_name: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> Product:
        """API 응답에서 Product 객체를 생성한다."""
        return cls(
            product_id=str(data.get("productId", "")),
            product_name=data.get("productName", ""),
            product_price=int(data.get("productPrice", 0)),
            product_image=data.get("productImage", ""),
            product_url=data.get("productUrl", ""),
            review_count=int(data.get("reviewCount", 0)),
            rating=float(data.get("rating", 0.0)),
            is_rocket=data.get("isRocket", False),
            category_name=data.get("categoryName", ""),
        )


def search_and_filter(
    client: CoupangAPIClient,
    keyword: str,
    count: int = 3,
    min_reviews: int = 50,
    min_rating: float = 4.0,
) -> list[Product]:
    """키워드로 상품을 검색하고 품질 기준으로 필터링한다."""
    raw_products = client.search_products(keyword, limit=20)

    products = [Product.from_api_response(p) for p in raw_products]

    # 필터링: 리뷰 수, 평점 기준
    filtered = [
        p for p in products
        if p.review_count >= min_reviews and p.rating >= min_rating
    ]

    # 로켓배송 우선, 리뷰수 내림차순 정렬
    filtered.sort(key=lambda p: (not p.is_rocket, -p.review_count))

    # 가격대 다양화: 저가/중가/고가 선택
    if len(filtered) >= count:
        filtered.sort(key=lambda p: p.product_price)
        step = max(1, len(filtered) // count)
        selected = [filtered[i * step] for i in range(count) if i * step < len(filtered)]
    else:
        selected = filtered[:count]

    logger.info(
        "검색 '%s': %d개 중 %d개 선택 (필터 후 %d개)",
        keyword, len(products), len(selected), len(filtered),
    )
    return selected
