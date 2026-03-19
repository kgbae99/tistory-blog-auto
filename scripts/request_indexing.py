"""미색인 페이지를 Indexing API로 대량 색인 요청한다."""

import json
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import setup_logger

logger = setup_logger("auto_indexing")

SITE_URL = "https://kgbae2369.tistory.com"
INDEXED_FILE = Path(__file__).parent.parent / "data" / "indexed_urls.json"


def get_all_post_numbers() -> list[int]:
    """사이트맵에서 전체 포스트 번호를 가져온다."""
    try:
        resp = requests.get(f"{SITE_URL}/sitemap.xml", timeout=10)
        numbers = re.findall(r"/(\d+)</loc>", resp.text)
        return sorted(set(int(n) for n in numbers))
    except Exception:
        return list(range(1, 530))


def load_indexed_urls() -> set[str]:
    """이미 색인 요청한 URL 목록을 로드한다."""
    if INDEXED_FILE.exists():
        return set(json.loads(INDEXED_FILE.read_text(encoding="utf-8")))
    return set()


def save_indexed_urls(urls: set[str]) -> None:
    """색인 요청 완료 URL 목록을 저장한다."""
    INDEXED_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEXED_FILE.write_text(
        json.dumps(sorted(urls), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_auto_indexing(max_count: int = 200) -> dict:
    """미색인 페이지에 Indexing API로 색인 요청을 보낸다."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_path = Path(__file__).parent.parent / "config" / "gsc_token.json"
    token = json.loads(token_path.read_text(encoding="utf-8"))
    creds = Credentials(
        token=token["token"],
        refresh_token=token["refresh_token"],
        token_uri=token["token_uri"],
        client_id=token["client_id"],
        client_secret=token["client_secret"],
        scopes=token["scopes"],
    )
    indexing_service = build("indexing", "v3", credentials=creds)

    # 전체 포스트 번호
    all_numbers = get_all_post_numbers()
    all_urls = {f"{SITE_URL}/{n}" for n in all_numbers}

    # 이미 요청한 것 제외
    already = load_indexed_urls()
    remaining = sorted(all_urls - already)

    logger.info("전체: %d개 | 이미 요청: %d개 | 남은: %d개", len(all_urls), len(already), len(remaining))

    if not remaining:
        logger.info("모든 URL 색인 요청 완료!")
        return {"total": len(all_urls), "already": len(already), "remaining": 0, "success": 0, "failed": 0}

    batch = remaining[:max_count]
    success = 0
    failed = 0

    for i, url in enumerate(batch):
        try:
            body = {"url": url, "type": "URL_UPDATED"}
            indexing_service.urlNotifications().publish(body=body).execute()
            success += 1
            already.add(url)
            if (i + 1) % 50 == 0:
                logger.info("진행: %d/%d (성공: %d)", i + 1, len(batch), success)
            time.sleep(0.3)
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                logger.warning("일일 한도 도달 (%d번째)", i + 1)
                break
            failed += 1
            logger.error("에러 (%s): %s", url, err[:80])

    # 저장
    save_indexed_urls(already)

    result = {
        "total": len(all_urls),
        "already": len(already),
        "remaining": len(all_urls) - len(already),
        "success": success,
        "failed": failed,
    }
    logger.info("색인 요청 완료: %d 성공, %d 실패, %d 남음", success, failed, result["remaining"])
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    import argparse
    parser = argparse.ArgumentParser(description="Google 색인 대량 요청")
    parser.add_argument("--count", "-n", type=int, default=200, help="요청할 최대 URL 수 (기본 200)")
    args = parser.parse_args()

    result = run_auto_indexing(max_count=args.count)

    print(f"\n{'='*50}")
    print(f"  Google 색인 자동 요청 결과")
    print(f"{'='*50}")
    print(f"  전체 URL: {result['total']}개")
    print(f"  요청 완료: {result['already']}개")
    print(f"  이번 성공: {result['success']}개")
    print(f"  이번 실패: {result['failed']}개")
    print(f"  남은 URL: {result['remaining']}개")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
