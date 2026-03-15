"""포스트별 유입 분석 + 인기 주제 기반 트렌드 최신화."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from src.core.logger import setup_logger

logger = setup_logger("traffic_analyzer")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
TREND_CACHE_FILE = DATA_DIR / "trend_insights.json"


def get_top_performing_posts(days: int = 28, limit: int = 20) -> list[dict]:
    """Search Console에서 상위 성과 포스트를 가져온다."""
    try:
        from src.seo.search_console import get_service
        service = get_service()
        site_url = "https://kgbae2369.tistory.com/"

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        response = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["page"],
                "rowLimit": limit,
            },
        ).execute()

        results = []
        for row in response.get("rows", []):
            url = row["keys"][0]
            post_num = url.rstrip("/").split("/")[-1]
            results.append({
                "url": url,
                "post_num": post_num,
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "position": row.get("position", 0),
            })

        results.sort(key=lambda x: x["impressions"], reverse=True)
        logger.info("상위 포스트 %d개 조회 완료", len(results))
        return results

    except Exception as e:
        logger.warning("상위 포스트 조회 실패: %s", e)
        return []


def get_top_queries(days: int = 28, limit: int = 30) -> list[dict]:
    """인기 검색어를 가져온다."""
    try:
        from src.seo.search_console import get_service
        service = get_service()
        site_url = "https://kgbae2369.tistory.com/"

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        response = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": limit,
            },
        ).execute()

        results = []
        for row in response.get("rows", []):
            results.append({
                "query": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "position": row.get("position", 0),
            })

        logger.info("인기 검색어 %d개 조회 완료", len(results))
        return results

    except Exception as e:
        logger.warning("인기 검색어 조회 실패: %s", e)
        return []


def analyze_content_gaps(queries: list[dict], blog_index: list[dict]) -> list[str]:
    """검색어 중 블로그에 없는 주제(콘텐츠 갭)를 찾는다."""
    # 기존 포스트 키워드 모음
    existing_keywords: set[str] = set()
    for post in blog_index:
        for kw in post.get("keywords", []):
            existing_keywords.add(kw.lower())
        existing_keywords.add(post.get("title", "").lower())

    gaps = []
    for q in queries:
        query = q["query"].lower()
        # 기존 포스트에 없는 검색어 = 콘텐츠 갭
        has_content = any(query in kw or kw in query for kw in existing_keywords)
        if not has_content and q["impressions"] >= 1:
            gaps.append(q["query"])

    logger.info("콘텐츠 갭 발견: %d개", len(gaps))
    return gaps


def generate_trend_insights() -> dict:
    """유입 데이터 기반 트렌드 인사이트를 생성한다."""
    top_posts = get_top_performing_posts()
    top_queries = get_top_queries()

    # 블로그 인덱스 로드
    index_file = DATA_DIR / "blog_posts_index.json"
    blog_index = []
    if index_file.exists():
        blog_index = json.loads(index_file.read_text(encoding="utf-8"))

    # 콘텐츠 갭 분석
    gaps = analyze_content_gaps(top_queries, blog_index)

    # 고성과 주제 추출
    high_impression_topics = [
        q["query"] for q in top_queries if q["impressions"] >= 5
    ]

    # 순위 개선 기회 (11~30위 → 1페이지 진입 가능)
    improvement_opportunities = [
        q for q in top_queries
        if 11 <= q["position"] <= 30 and q["impressions"] >= 2
    ]

    insights = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "top_posts": top_posts[:10],
        "top_queries": top_queries[:15],
        "content_gaps": gaps[:10],
        "high_impression_topics": high_impression_topics[:10],
        "improvement_opportunities": [
            {"query": q["query"], "position": f"{q['position']:.0f}위", "impressions": q["impressions"]}
            for q in improvement_opportunities[:10]
        ],
        "recommended_keywords": gaps[:5] + high_impression_topics[:5],
    }

    # 캐시 저장
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TREND_CACHE_FILE.write_text(
        json.dumps(insights, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info(
        "트렌드 인사이트: 갭 %d개, 고노출 %d개, 개선기회 %d개",
        len(gaps), len(high_impression_topics), len(improvement_opportunities),
    )
    return insights


def print_traffic_report() -> None:
    """유입 분석 리포트를 출력한다."""
    insights = generate_trend_insights()

    print("\n" + "=" * 60)
    print("  유입 분석 & 트렌드 리포트")
    print("=" * 60)

    if insights["top_queries"]:
        print("\n  인기 검색어 TOP 10:")
        for i, q in enumerate(insights["top_queries"][:10], 1):
            print(f"    {i}. {q['query']} ({q['impressions']}노출, {q['position']:.0f}위)")

    if insights["content_gaps"]:
        print(f"\n  콘텐츠 갭 (검색되지만 글이 없는 주제):")
        for gap in insights["content_gaps"][:5]:
            print(f"    → {gap}")

    if insights["improvement_opportunities"]:
        print(f"\n  순위 개선 기회 (11~30위 → 1페이지 가능):")
        for opp in insights["improvement_opportunities"][:5]:
            print(f"    → {opp['query']} ({opp['position']}, {opp['impressions']}노출)")

    if insights["recommended_keywords"]:
        print(f"\n  추천 키워드 (다음 포스트 주제):")
        for kw in insights["recommended_keywords"][:5]:
            print(f"    ★ {kw}")

    print("\n" + "=" * 60)
