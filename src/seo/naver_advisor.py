"""네이버 서치어드바이저 연동 모듈 - 사이트맵 제출 및 웹마스터 도구 활용."""

from __future__ import annotations

import requests

from src.core.logger import setup_logger

logger = setup_logger("naver_advisor")

BLOG_URL = "https://kgbae2369.tistory.com"


def check_naver_indexing(query: str) -> list[dict]:
    """네이버에서 블로그 검색 결과를 확인한다 (비공식)."""
    try:
        url = "https://ac.search.naver.com/nx/ac"
        params = {
            "q": f"site:kgbae2369.tistory.com {query}",
            "con": 1,
            "frm": "nv",
            "ans": 2,
            "r_format": "json",
            "r_enc": "UTF-8",
        }
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        items = data.get("items", [])
        logger.info("네이버 검색 '%s': %d개 결과", query, len(items))
        return items
    except Exception as e:
        logger.warning("네이버 검색 실패: %s", e)
        return []


def submit_sitemap_to_naver(api_key: str) -> bool:
    """네이버 서치어드바이저에 사이트맵을 제출한다.

    네이버 서치어드바이저 API는 공식적으로 제공되지 않으므로,
    수동으로 제출해야 합니다.
    """
    logger.info(
        "네이버 서치어드바이저 사이트맵 제출은 수동으로 진행해주세요:\n"
        "1. https://searchadvisor.naver.com 접속\n"
        "2. 사이트 등록: %s\n"
        "3. 소유권 확인 (HTML 메타태그 또는 파일 업로드)\n"
        "4. 요청 > 사이트맵 제출: %s/sitemap.xml\n"
        "5. 요청 > RSS 제출: %s/rss",
        BLOG_URL, BLOG_URL, BLOG_URL,
    )
    return False


def get_naver_setup_guide() -> str:
    """네이버 서치어드바이저 설정 가이드를 반환한다."""
    return """
═══════════════════════════════════════════════════
  네이버 서치어드바이저 설정 가이드
═══════════════════════════════════════════════════

[1단계] 사이트 등록
  • https://searchadvisor.naver.com 접속
  • 로그인 → 웹마스터 도구 → 사이트 추가
  • URL: https://kgbae2369.tistory.com

[2단계] 소유권 확인
  • HTML 메타태그 방식 추천
  • 제공된 메타태그를 복사
  • 티스토리 관리자 > 꾸미기 > 스킨 편집 > HTML 편집
  • <head> 안에 메타태그 붙여넣기 → 저장
  • 서치어드바이저에서 확인 클릭

[3단계] 사이트맵 제출
  • 요청 > 사이트맵 제출
  • URL: https://kgbae2369.tistory.com/sitemap.xml

[4단계] RSS 제출
  • 요청 > RSS 제출
  • URL: https://kgbae2369.tistory.com/rss

[5단계] 웹 페이지 수집 요청
  • 요청 > 웹 페이지 수집
  • 최근 주요 포스트 URL 입력하여 수집 요청

═══════════════════════════════════════════════════
"""
