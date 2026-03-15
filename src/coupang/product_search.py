"""쿠팡 상품 검색 및 필터링."""

from __future__ import annotations

import re
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


def _normalize_name(name: str) -> str:
    """상품명을 정규화한다 (비교용)."""
    name = re.sub(r"\d+[gG개정입팩박스세트]+", "", name)  # 수량/용량 제거
    name = re.sub(r"[^\w가-힣\s]", "", name)  # 특수문자 제거
    name = re.sub(r"\s+", " ", name).strip().lower()
    return name


def _is_duplicate(new_product: Product, selected: list[Product], threshold: float = 0.5) -> bool:
    """상품이 이미 선택된 상품과 중복인지 검사한다."""
    new_name = _normalize_name(new_product.product_name)
    new_words = set(new_name.split())

    for existing in selected:
        existing_name = _normalize_name(existing.product_name)
        existing_words = set(existing_name.split())

        if not new_words or not existing_words:
            continue

        # Jaccard 유사도
        intersection = new_words & existing_words
        union = new_words | existing_words
        similarity = len(intersection) / len(union)

        if similarity >= threshold:
            logger.info(
                "상품 중복 제거: '%s' ↔ '%s' (유사도: %.0f%%)",
                new_product.product_name[:25], existing.product_name[:25], similarity * 100,
            )
            return True

        # 같은 product_id
        if new_product.product_id == existing.product_id:
            return True

    return False


def search_and_filter(
    client: CoupangAPIClient,
    keyword: str,
    count: int = 3,
) -> list[Product]:
    """키워드로 상품을 검색하고 중복 없는 상위 상품을 반환한다."""
    raw_products = client.search_products(keyword, limit=count * 5)

    products = [Product.from_api_response(p) for p in raw_products]

    # 로켓배송 우선, rank 순 정렬
    products.sort(key=lambda p: (not p.is_rocket, p.rank))

    # 중복 제거 + 가격대 다양화
    unique: list[Product] = []
    for p in products:
        if not _is_duplicate(p, unique):
            unique.append(p)

    # 가격대 다양화: 저가/중가/고가 선택
    if len(unique) >= count:
        unique.sort(key=lambda p: p.product_price)
        step = max(1, len(unique) // count)
        selected = [
            unique[i * step]
            for i in range(count)
            if i * step < len(unique)
        ]
    else:
        selected = unique[:count]

    logger.info(
        "검색 '%s': %d개 → 중복제거 %d개 → %d개 선택",
        keyword, len(products), len(unique), len(selected),
    )
    return selected
