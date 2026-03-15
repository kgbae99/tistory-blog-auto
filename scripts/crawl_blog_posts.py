"""블로그 전체 포스트를 크롤링하여 내부 링크 DB를 자동 구축한다."""

import json
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import setup_logger

logger = setup_logger("blog_crawler")

BLOG_URL = "https://kgbae2369.tistory.com"
DATA_DIR = Path(__file__).parent.parent / "data"
POSTS_INDEX_FILE = DATA_DIR / "blog_posts_index.json"


def fetch_sitemap() -> list[str]:
    """사이트맵에서 모든 포스트 URL을 추출한다."""
    try:
        resp = requests.get(f"{BLOG_URL}/sitemap.xml", timeout=10)
        urls = re.findall(r"<loc>(https://kgbae2369\.tistory\.com/(\d+))</loc>", resp.text)
        logger.info("사이트맵에서 %d개 포스트 URL 추출", len(urls))
        return [(url, int(num)) for url, num in urls]
    except Exception as e:
        logger.error("사이트맵 로드 실패: %s", e)
        return []


def extract_post_info(url: str, post_num: int) -> dict | None:
    """포스트 페이지에서 제목과 키워드를 추출한다."""
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = "utf-8"
        html = resp.text

        # 제목 추출
        title_match = re.search(r"<title>([^<]+)</title>", html)
        title = title_match.group(1).strip() if title_match else ""
        # 블로그명 제거
        title = re.sub(r"\s*[-–—|]?\s*건강온도사.*$", "", title).strip()

        if not title:
            return None

        # 카테고리 추출
        cat_match = re.search(r'<a[^>]*class="[^"]*category[^"]*"[^>]*>([^<]+)</a>', html)
        category = cat_match.group(1).strip() if cat_match else ""

        # 태그 추출
        tags = re.findall(r'<a[^>]*rel="tag"[^>]*>([^<]+)</a>', html)

        # 제목에서 키워드 추출 (명사 중심)
        keywords = _extract_keywords_from_title(title)
        keywords.extend(tags[:5])

        return {
            "num": post_num,
            "url": f"/{post_num}",
            "full_url": url,
            "title": title,
            "category": category,
            "tags": tags,
            "keywords": list(set(keywords)),
        }
    except Exception as e:
        logger.debug("포스트 /%d 추출 실패: %s", post_num, e)
        return None


def _extract_keywords_from_title(title: str) -> list[str]:
    """제목에서 키워드를 추출한다."""
    # 불용어 제거
    stopwords = {
        "이", "그", "저", "것", "수", "를", "은", "는", "이", "가",
        "에", "의", "도", "으로", "로", "에서", "와", "과", "하는",
        "위한", "대한", "통한", "있는", "없는", "하면", "되면",
        "꼭", "바로", "지금", "이제", "정말", "매우", "가장",
        "BEST", "TOP", "best", "top",
    }

    # 특수문자 제거 및 분리
    clean = re.sub(r"[^\w\s가-힣]", " ", title)
    words = clean.split()

    keywords = []
    for word in words:
        if len(word) >= 2 and word not in stopwords:
            keywords.append(word)

    # 연속 2~3어절 조합도 추가
    if len(words) >= 2:
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if len(bigram) >= 4:
                keywords.append(bigram)

    return keywords[:10]


def crawl_and_build_index(max_posts: int = 100) -> list[dict]:
    """블로그를 크롤링하여 포스트 인덱스를 구축한다."""
    urls = fetch_sitemap()
    if not urls:
        return []

    # 최신 포스트부터 크롤링
    urls.sort(key=lambda x: x[1], reverse=True)
    urls = urls[:max_posts]

    posts = []
    for i, (url, num) in enumerate(urls):
        info = extract_post_info(url, num)
        if info:
            posts.append(info)

        if (i + 1) % 20 == 0:
            logger.info("크롤링 진행: %d/%d", i + 1, len(urls))
            time.sleep(1)  # 서버 부하 방지

    # 저장
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_INDEX_FILE.write_text(
        json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info("포스트 인덱스 구축 완료: %d개 → %s", len(posts), POSTS_INDEX_FILE)
    return posts


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    import argparse
    parser = argparse.ArgumentParser(description="블로그 포스트 크롤러")
    parser.add_argument("--count", "-n", type=int, default=100, help="크롤링할 포스트 수")
    args = parser.parse_args()

    posts = crawl_and_build_index(max_posts=args.count)

    print(f"\n{'='*50}")
    print(f"  블로그 포스트 인덱스 구축 완료")
    print(f"{'='*50}")
    print(f"  총 {len(posts)}개 포스트 수집")
    print(f"  저장: {POSTS_INDEX_FILE}")

    # 카테고리별 통계
    cats: dict[str, int] = {}
    for p in posts:
        cat = p.get("category", "기타") or "기타"
        cats[cat] = cats.get(cat, 0) + 1

    print(f"\n  카테고리별:")
    for cat, count in sorted(cats.items(), key=lambda x: x[1], reverse=True):
        print(f"    {cat}: {count}개")


if __name__ == "__main__":
    main()
