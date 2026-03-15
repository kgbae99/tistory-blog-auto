"""미색인 페이지를 자동으로 찾아 Google 색인 요청을 보낸다."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import setup_logger

logger = setup_logger("auto_indexing")

SITE_URL = "https://kgbae2369.tistory.com/"


def run_auto_indexing(check_count: int = 30) -> dict:
    """최근 포스트를 검사하고 미색인 페이지에 색인 요청을 보낸다."""
    from src.seo.search_console import get_service, request_indexing

    service = get_service()

    # 최신 포스트 번호 범위 추정 (sitemap에서 가져올 수도 있음)
    import requests
    try:
        resp = requests.get(f"{SITE_URL}sitemap.xml", timeout=10)
        # 사이트맵에서 최신 포스트 번호 추출
        import re
        numbers = re.findall(r"/(\d+)</loc>", resp.text)
        if numbers:
            latest = max(int(n) for n in numbers)
            start = latest
        else:
            start = 535
    except Exception:
        start = 535

    logger.info("최근 %d개 포스트 색인 상태 검사 (/%d ~ /%d)", check_count, start, start - check_count + 1)

    not_indexed = []
    indexed_count = 0
    checked = 0

    for num in range(start, start - check_count, -1):
        url = f"{SITE_URL}{num}"
        try:
            resp = service.urlInspection().index().inspect(
                body={"inspectionUrl": url, "siteUrl": SITE_URL}
            ).execute()
            verdict = resp.get("inspectionResult", {}).get("indexStatusResult", {}).get("verdict", "")
            state = resp.get("inspectionResult", {}).get("indexStatusResult", {}).get("coverageState", "")

            checked += 1
            if verdict == "PASS":
                indexed_count += 1
            else:
                not_indexed.append({"num": num, "url": url, "state": state})
                logger.info("  미색인: /%d → %s", num, state)
        except Exception:
            pass  # 존재하지 않는 URL

    logger.info("검사 완료: %d개 중 색인 %d, 미색인 %d", checked, indexed_count, len(not_indexed))

    # 미색인 페이지 색인 요청
    success = 0
    failed = 0
    for page in not_indexed:
        if request_indexing(page["url"]):
            success += 1
        else:
            failed += 1
        time.sleep(1)

    result = {
        "checked": checked,
        "indexed": indexed_count,
        "not_indexed": len(not_indexed),
        "index_requested": success,
        "request_failed": failed,
    }

    logger.info(
        "색인 요청 완료: %d 성공, %d 실패",
        success, failed,
    )
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    import argparse
    parser = argparse.ArgumentParser(description="Google 색인 자동 요청")
    parser.add_argument("--count", "-n", type=int, default=30, help="검사할 포스트 수")
    args = parser.parse_args()

    result = run_auto_indexing(check_count=args.count)

    print(f"\n{'='*50}")
    print(f"  Google 색인 자동 요청 결과")
    print(f"{'='*50}")
    print(f"  검사: {result['checked']}개")
    print(f"  색인됨: {result['indexed']}개")
    print(f"  미색인: {result['not_indexed']}개")
    print(f"  요청 성공: {result['index_requested']}개")
    print(f"  요청 실패: {result['request_failed']}개")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
