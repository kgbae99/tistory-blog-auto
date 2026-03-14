"""쿠팡 파트너스 API 클라이언트 - HMAC 인증."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any
from urllib.parse import urlencode

import requests

from src.core.config import CoupangConfig
from src.core.logger import setup_logger

logger = setup_logger("coupang_api")

API_BASE = "https://api-gateway.coupang.com"


class CoupangAPIClient:
    """쿠팡 파트너스 Open API 클라이언트."""

    def __init__(self, config: CoupangConfig) -> None:
        self.access_key = config.access_key
        self.secret_key = config.secret_key
        self.session = requests.Session()

    def _generate_hmac(
        self, method: str, path: str, query: str = ""
    ) -> str:
        """HMAC-SHA256 서명을 생성한다.

        쿠팡 공식 문서 기준:
        message = datetime + method + path + query (? 없이 연결)
        """
        os.environ["TZ"] = "GMT+0"
        datetime_str = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
        message = datetime_str + method + path + query
        signature = hmac.new(
            bytes(self.secret_key, "utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return (
            f"CEA algorithm=HmacSHA256, access-key={self.access_key}, "
            f"signed-date={datetime_str}, signature={signature}"
        )

    def _request(
        self, method: str, path: str, params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict[str, Any]:
        """API 요청을 수행한다."""
        if params:
            query = urlencode(params)
            authorization = self._generate_hmac(method, path, query)
            url = f"{API_BASE}{path}?{query}"
        else:
            authorization = self._generate_hmac(method, path)
            url = f"{API_BASE}{path}"

        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
        }

        try:
            if method == "GET":
                resp = self.session.get(url, headers=headers, timeout=10)
            else:
                resp = self.session.post(
                    url, headers=headers, json=json_body, timeout=10
                )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(
                "쿠팡 API 요청 실패: %s %s - %s", method, path, e
            )
            raise

    def search_products(
        self, keyword: str, limit: int = 10, sub_id: str = "blog"
    ) -> list[dict[str, Any]]:
        """키워드로 쿠팡 상품을 검색한다."""
        path = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
        params = {"keyword": keyword, "limit": limit, "subId": sub_id}
        result = self._request("GET", path, params=params)
        data = result.get("data", {})
        # 응답 구조: data.productData 배열에 상품 목록
        if isinstance(data, dict):
            products = data.get("productData", [])
        else:
            products = data if isinstance(data, list) else []
        logger.info(
            "쿠팡 검색 '%s': %d개 상품 발견", keyword, len(products)
        )
        return products

    def get_deeplink(self, coupang_urls: list[str],
                     sub_id: str = "blog") -> list[dict[str, str]]:
        """쿠팡 URL을 수익 딥링크로 변환한다."""
        path = "/v2/providers/affiliate_open_api/apis/openapi/deeplink"
        body = {"coupangUrls": coupang_urls, "subId": sub_id}
        result = self._request("POST", path, json_body=body)
        links = result.get("data", [])
        logger.info("%d개 딥링크 생성 완료", len(links))
        return links

    def get_recommended_products(self, category_id: int = 0,
                                 limit: int = 10) -> list[dict[str, Any]]:
        """추천 상품 목록을 가져온다."""
        path = "/v2/providers/affiliate_open_api/apis/openapi/products/reco"
        params = {"categoryId": category_id, "limit": limit}
        result = self._request("GET", path, params=params)
        return result.get("data", [])
