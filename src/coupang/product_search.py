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
    is_rocket: bool
    is_free_shipping: bool
    category_name: str
    keyword: str
    rank: int

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> Product:
        """API 응답에서 Product 객체를 생성한다."""
        return cls(
            product_id=str(data.get("productId", "")),
            product_name=data.get("productName", ""),
            product_price=int(data.get("productPrice", 0)),
            product_image=data.get("productImage", ""),
            product_url=data.get("productUrl", ""),
            is_rocket=data.get("isRocket", False),
            is_free_shipping=data.get("isFreeShipping", False),
            category_name=data.get("categoryName", ""),
            keyword=data.get("keyword", ""),
            rank=int(data.get("rank", 0)),
        )


def search_and_filter(
    client: CoupangAPIClient,
    keyword: str,
    count: int = 3,
) -> list[Product]:
    """키워드로 상품을 검색하고 상위 상품을 반환한다."""
    raw_products = client.search_products(keyword, limit=count * 3)

    products = [Product.from_api_response(p) for p in raw_products]

    # 로켓배송 우선, rank 순 정렬
    products.sort(key=lambda p: (not p.is_rocket, p.rank))

    # 가격대 다양화: 저가/중가/고가 선택
    if len(products) >= count:
        products.sort(key=lambda p: p.product_price)
        step = max(1, len(products) // count)
        selected = [
            products[i * step]
            for i in range(count)
            if i * step < len(products)
        ]
    else:
        selected = products[:count]

    logger.info(
        "검색 '%s': %d개 중 %d개 선택",
        keyword, len(products), len(selected),
    )
    return selected
