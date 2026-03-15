"""Google Search Console API 연동 모듈."""

from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.core.logger import setup_logger

logger = setup_logger("search_console")

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "gsc_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/indexing",
]
SITE_URL = "https://kgbae2369.tistory.com/"


def get_credentials() -> Credentials:
    """OAuth2 인증을 수행하고 Credentials를 반환한다."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("토큰 갱신 완료")
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json이 없습니다. {CREDENTIALS_FILE} 경로에 저장해주세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
            logger.info("OAuth2 인증 완료")

        TOKEN_FILE.write_text(creds.to_json())
        logger.info("토큰 저장: %s", TOKEN_FILE)

    return creds


def get_service():
    """Search Console API 서비스를 생성한다."""
    creds = get_credentials()
    return build("searchconsole", "v1", credentials=creds)


def get_index_status() -> dict:
    """사이트의 색인 현황을 조회한다."""
    service = get_service()

    # 사이트 목록 확인
    sites = service.sites().list().execute()
    site_list = sites.get("siteEntry", [])

    our_site = None
    for site in site_list:
        if "kgbae2369" in site.get("siteUrl", ""):
            our_site = site
            break

    if not our_site:
        logger.warning("Search Console에서 사이트를 찾을 수 없습니다")
        return {"error": "사이트 미등록", "registered_sites": [s["siteUrl"] for s in site_list]}

    logger.info("사이트 확인: %s (권한: %s)", our_site["siteUrl"], our_site.get("permissionLevel"))
    return {
        "site_url": our_site["siteUrl"],
        "permission": our_site.get("permissionLevel", ""),
    }


def get_search_performance(days: int = 28) -> dict:
    """검색 실적 데이터를 조회한다."""
    service = get_service()

    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "rowLimit": 25,
    }

    response = service.searchanalytics().query(
        siteUrl=SITE_URL, body=request
    ).execute()

    rows = response.get("rows", [])

    results = {
        "period": f"{start_date} ~ {end_date}",
        "total_clicks": sum(r.get("clicks", 0) for r in rows),
        "total_impressions": sum(r.get("impressions", 0) for r in rows),
        "avg_ctr": 0.0,
        "avg_position": 0.0,
        "top_queries": [],
    }

    if rows:
        results["avg_ctr"] = sum(r.get("ctr", 0) for r in rows) / len(rows)
        results["avg_position"] = sum(r.get("position", 0) for r in rows) / len(rows)
        results["top_queries"] = [
            {
                "query": r["keys"][0],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": f"{r.get('ctr', 0) * 100:.1f}%",
                "position": f"{r.get('position', 0):.1f}",
            }
            for r in rows[:15]
        ]

    logger.info(
        "검색 실적: %d클릭, %d노출, CTR %.1f%%, 평균순위 %.1f",
        results["total_clicks"], results["total_impressions"],
        results["avg_ctr"] * 100, results["avg_position"],
    )
    return results


def get_page_performance(days: int = 28) -> list[dict]:
    """페이지별 검색 실적을 조회한다."""
    service = get_service()

    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page"],
        "rowLimit": 50,
    }

    response = service.searchanalytics().query(
        siteUrl=SITE_URL, body=request
    ).execute()

    pages = []
    for row in response.get("rows", []):
        pages.append({
            "url": row["keys"][0],
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": f"{row.get('ctr', 0) * 100:.1f}%",
            "position": f"{row.get('position', 0):.1f}",
        })

    logger.info("페이지별 실적: %d개 페이지", len(pages))
    return pages


def get_index_coverage() -> dict:
    """색인 범위 보고서를 조회한다 (URL 검사 API)."""
    service = get_service()

    # URL 검사 API로 최신 포스트 색인 상태 확인
    test_urls = [
        f"{SITE_URL}530",
        f"{SITE_URL}528",
        f"{SITE_URL}527",
        f"{SITE_URL}526",
        f"{SITE_URL}525",
    ]

    results = []
    for url in test_urls:
        try:
            response = service.urlInspection().index().inspect(
                body={
                    "inspectionUrl": url,
                    "siteUrl": SITE_URL,
                }
            ).execute()

            result = response.get("inspectionResult", {})
            index_status = result.get("indexStatusResult", {})

            results.append({
                "url": url,
                "verdict": index_status.get("verdict", "UNKNOWN"),
                "coverage_state": index_status.get("coverageState", "UNKNOWN"),
                "indexing_state": index_status.get("indexingState", "UNKNOWN"),
                "last_crawl": index_status.get("lastCrawlTime", ""),
                "crawled_as": index_status.get("crawledAs", ""),
            })
        except Exception as e:
            results.append({
                "url": url,
                "verdict": "ERROR",
                "error": str(e),
            })

    indexed = sum(1 for r in results if r.get("verdict") == "PASS")
    logger.info("색인 검사: %d/%d 페이지 색인됨", indexed, len(results))
    return {
        "checked": len(results),
        "indexed": indexed,
        "pages": results,
    }


def request_indexing(url: str) -> bool:
    """URL 색인 요청을 보낸다 (Indexing API)."""
    try:
        creds = get_credentials()
        service = build("indexing", "v3", credentials=creds)
        body = {"url": url, "type": "URL_UPDATED"}
        response = service.urlNotifications().publish(body=body).execute()
        logger.info("색인 요청 성공: %s → %s", url, response.get("urlNotificationMetadata", {}).get("latestUpdate", {}).get("type", ""))
        return True
    except Exception as e:
        logger.warning("색인 요청 실패: %s → %s", url, e)
        return False


def batch_request_indexing(urls: list[str]) -> dict:
    """여러 URL에 대해 색인 요청을 보낸다."""
    results = {"success": [], "failed": []}
    for url in urls:
        if request_indexing(url):
            results["success"].append(url)
        else:
            results["failed"].append(url)
    logger.info("색인 요청 완료: %d 성공, %d 실패", len(results["success"]), len(results["failed"]))
    return results


def print_full_report() -> None:
    """전체 Search Console 리포트를 출력한다."""
    print("\n" + "=" * 60)
    print("  Google Search Console 리포트")
    print("=" * 60)

    # 1. 사이트 상태
    status = get_index_status()
    if "error" in status:
        print(f"\n  ⚠ {status['error']}")
        if status.get("registered_sites"):
            print(f"  등록된 사이트: {status['registered_sites']}")
        return

    print(f"\n  사이트: {status['site_url']}")
    print(f"  권한: {status['permission']}")

    # 2. 검색 실적
    print("\n" + "-" * 60)
    perf = get_search_performance()
    print(f"  기간: {perf['period']}")
    print(f"  총 클릭: {perf['total_clicks']:,}회")
    print(f"  총 노출: {perf['total_impressions']:,}회")
    print(f"  평균 CTR: {perf['avg_ctr'] * 100:.1f}%")
    print(f"  평균 순위: {perf['avg_position']:.1f}위")

    if perf["top_queries"]:
        print(f"\n  TOP 검색어:")
        for i, q in enumerate(perf["top_queries"][:10], 1):
            print(f"    {i}. {q['query']} ({q['clicks']}클릭, {q['impressions']}노출, {q['position']}위)")

    # 3. 색인 상태
    print("\n" + "-" * 60)
    coverage = get_index_coverage()
    print(f"  색인 검사: {coverage['indexed']}/{coverage['checked']} 페이지")
    for p in coverage["pages"]:
        status_icon = "✓" if p.get("verdict") == "PASS" else "✗"
        print(f"    {status_icon} {p['url'].split('/')[-1]} → {p.get('coverage_state', p.get('error', ''))}")

    print("\n" + "=" * 60)
