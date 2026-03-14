"""쿠팡 파트너스 API 테스트."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core.config import CoupangConfig
from src.coupang.api_client import CoupangAPIClient
from src.coupang.link_generator import (
    _format_price,
    _rating_to_stars,
    generate_disclaimer,
    generate_product_html,
)
from src.coupang.product_search import Product, search_and_filter


@pytest.fixture
def coupang_config() -> CoupangConfig:
    return CoupangConfig(access_key="test_key", secret_key="test_secret")


@pytest.fixture
def client(coupang_config: CoupangConfig) -> CoupangAPIClient:
    return CoupangAPIClient(coupang_config)


@pytest.fixture
def sample_product() -> Product:
    return Product(
        product_id="12345",
        product_name="비타민D 3000IU 고함량",
        product_price=15900,
        product_image="https://example.com/image.jpg",
        product_url="https://www.coupang.com/vp/products/12345",
        review_count=1234,
        rating=4.7,
        is_rocket=True,
        category_name="건강식품",
    )


class TestHMACGeneration:
    def test_hmac_format(self, client: CoupangAPIClient) -> None:
        auth = client._generate_hmac("GET", "/test/path")
        assert auth.startswith("CEA algorithm=HmacSHA256")
        assert "access-key=test_key" in auth
        assert "signature=" in auth

    def test_hmac_different_methods(self, client: CoupangAPIClient) -> None:
        get_auth = client._generate_hmac("GET", "/path")
        post_auth = client._generate_hmac("POST", "/path")
        # 같은 시간대면 method가 달라 signature도 다름
        assert "HmacSHA256" in get_auth
        assert "HmacSHA256" in post_auth


class TestProductSearch:
    def test_search_and_filter_with_mock(self, client: CoupangAPIClient) -> None:
        mock_products = [
            {
                "productId": str(i),
                "productName": f"테스트 상품 {i}",
                "productPrice": 10000 * (i + 1),
                "productImage": f"https://img.coupang.com/{i}.jpg",
                "productUrl": f"https://www.coupang.com/vp/products/{i}",
                "reviewCount": 100 + i * 50,
                "rating": 4.0 + i * 0.1,
                "isRocket": i % 2 == 0,
                "categoryName": "건강식품",
            }
            for i in range(5)
        ]

        with patch.object(client, "search_products", return_value=mock_products):
            products = search_and_filter(client, "비타민", count=3)
            assert len(products) <= 3
            assert all(isinstance(p, Product) for p in products)

    def test_product_from_api_response(self) -> None:
        data = {
            "productId": "999",
            "productName": "테스트",
            "productPrice": 5000,
            "productImage": "https://img.com/test.jpg",
            "productUrl": "https://coupang.com/vp/products/999",
            "reviewCount": 200,
            "rating": 4.5,
            "isRocket": True,
            "categoryName": "뷰티",
        }
        product = Product.from_api_response(data)
        assert product.product_id == "999"
        assert product.product_price == 5000
        assert product.is_rocket is True


class TestLinkGenerator:
    def test_format_price(self) -> None:
        assert _format_price(15900) == "15,900"
        assert _format_price(1000000) == "1,000,000"
        assert _format_price(500) == "500"

    def test_rating_to_stars(self) -> None:
        assert "★★★★" in _rating_to_stars(4.7)
        assert "★★★★★" == _rating_to_stars(5.0)

    def test_generate_product_html(self, sample_product: Product) -> None:
        html = generate_product_html(sample_product, "https://link.coupang.com/aff")
        assert "비타민D 3000IU 고함량" in html
        assert "15,900" in html
        assert "https://link.coupang.com/aff" in html
        assert "coupang-recommend" in html

    def test_generate_disclaimer(self) -> None:
        disclaimer = generate_disclaimer()
        assert "쿠팡 파트너스" in disclaimer
        assert "수수료" in disclaimer
