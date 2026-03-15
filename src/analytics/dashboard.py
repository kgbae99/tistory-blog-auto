"""수익 대시보드 - 포스트별 성과 추적 및 리포트 생성."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.core.logger import setup_logger

logger = setup_logger("dashboard")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
POSTS_DB = DATA_DIR / "posts_db.json"
REVENUE_LOG = DATA_DIR / "revenue_log.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_json(path: Path, data: list[dict]) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def register_post(
    title: str,
    keyword: str,
    url: str | None = None,
    category: str = "건강정보",
    tags: list[str] | None = None,
    coupang_products: int = 0,
    adsense_slots: int = 0,
) -> dict:
    """새 포스트를 DB에 등록한다."""
    posts = _load_json(POSTS_DB)

    post = {
        "id": len(posts) + 1,
        "title": title,
        "keyword": keyword,
        "url": url or "",
        "category": category,
        "tags": tags or [],
        "coupang_products": coupang_products,
        "adsense_slots": adsense_slots,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "published": url is not None,
        "views": 0,
        "coupang_clicks": 0,
        "adsense_impressions": 0,
        "estimated_revenue": 0.0,
    }

    posts.append(post)
    _save_json(POSTS_DB, posts)
    logger.info("포스트 등록: #%d '%s'", post["id"], title)
    return post


def update_post_stats(
    post_id: int,
    views: int = 0,
    coupang_clicks: int = 0,
    adsense_impressions: int = 0,
    revenue: float = 0.0,
) -> None:
    """포스트 통계를 업데이트한다."""
    posts = _load_json(POSTS_DB)
    for post in posts:
        if post["id"] == post_id:
            post["views"] += views
            post["coupang_clicks"] += coupang_clicks
            post["adsense_impressions"] += adsense_impressions
            post["estimated_revenue"] += revenue
            break
    _save_json(POSTS_DB, posts)


def log_daily_revenue(
    date: str | None = None,
    adsense_revenue: float = 0.0,
    coupang_revenue: float = 0.0,
    total_views: int = 0,
    posts_published: int = 0,
) -> None:
    """일일 수익을 기록한다."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    logs = _load_json(REVENUE_LOG)

    entry = {
        "date": date,
        "adsense_revenue": adsense_revenue,
        "coupang_revenue": coupang_revenue,
        "total_revenue": adsense_revenue + coupang_revenue,
        "total_views": total_views,
        "posts_published": posts_published,
    }

    # 같은 날짜 업데이트
    for i, log in enumerate(logs):
        if log["date"] == date:
            logs[i] = entry
            _save_json(REVENUE_LOG, logs)
            return

    logs.append(entry)
    _save_json(REVENUE_LOG, logs)
    logger.info("수익 기록: %s (총 ₩%.0f)", date, entry["total_revenue"])


def generate_revenue_report(days: int = 30) -> dict:
    """수익 리포트를 생성한다."""
    posts = _load_json(POSTS_DB)
    logs = _load_json(REVENUE_LOG)

    total_posts = len(posts)
    published_posts = sum(1 for p in posts if p.get("published"))
    total_views = sum(p.get("views", 0) for p in posts)
    total_coupang_clicks = sum(p.get("coupang_clicks", 0) for p in posts)

    # 최근 N일 수익
    recent_logs = sorted(logs, key=lambda x: x["date"], reverse=True)[:days]
    total_adsense = sum(l.get("adsense_revenue", 0) for l in recent_logs)
    total_coupang = sum(l.get("coupang_revenue", 0) for l in recent_logs)

    # 카테고리별 포스트 수
    category_counts: dict[str, int] = {}
    for p in posts:
        cat = p.get("category", "기타")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # 키워드별 성과 (상위 10개)
    keyword_perf = sorted(
        posts, key=lambda p: p.get("views", 0), reverse=True
    )[:10]

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "period_days": days,
        "summary": {
            "total_posts": total_posts,
            "published_posts": published_posts,
            "total_views": total_views,
            "total_coupang_clicks": total_coupang_clicks,
            "ctr_coupang": (
                f"{(total_coupang_clicks / total_views * 100):.1f}%"
                if total_views > 0
                else "0%"
            ),
        },
        "revenue": {
            "adsense_total": total_adsense,
            "coupang_total": total_coupang,
            "total": total_adsense + total_coupang,
            "daily_average": (
                (total_adsense + total_coupang) / len(recent_logs)
                if recent_logs
                else 0
            ),
        },
        "categories": category_counts,
        "top_posts": [
            {
                "title": p["title"],
                "keyword": p["keyword"],
                "views": p.get("views", 0),
                "revenue": p.get("estimated_revenue", 0),
            }
            for p in keyword_perf
        ],
    }

    logger.info(
        "리포트 생성: %d일간 총 수익 ₩%.0f, %d개 포스트",
        days, report["revenue"]["total"], total_posts,
    )
    return report


def print_dashboard() -> None:
    """콘솔에 대시보드를 출력한다."""
    report = generate_revenue_report()
    s = report["summary"]
    r = report["revenue"]

    print("\n" + "=" * 55)
    print("  건강온도사(행복++) 수익 대시보드")
    print("=" * 55)
    print(f"  생성일: {report['generated_at']}")
    print(f"  기간: 최근 {report['period_days']}일")
    print("-" * 55)
    print(f"  총 포스트: {s['total_posts']}개 (발행: {s['published_posts']}개)")
    print(f"  총 조회수: {s['total_views']:,}회")
    print(f"  쿠팡 클릭: {s['total_coupang_clicks']:,}회 (CTR: {s['ctr_coupang']})")
    print("-" * 55)
    print(f"  애드센스 수익: ₩{r['adsense_total']:,.0f}")
    print(f"  쿠팡 수익:     ₩{r['coupang_total']:,.0f}")
    print(f"  총 수익:       ₩{r['total']:,.0f}")
    print(f"  일평균:        ₩{r['daily_average']:,.0f}")
    print("-" * 55)

    if report["top_posts"]:
        print("  TOP 포스트:")
        for i, p in enumerate(report["top_posts"][:5], 1):
            print(f"    {i}. {p['title'][:30]}... ({p['views']:,}뷰)")

    print("=" * 55)
