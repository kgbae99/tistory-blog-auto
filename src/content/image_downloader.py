"""이미지 다운로드 모듈 - Unsplash에서 직접 다운로드하여 로컬 파일로 저장."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests

from src.core.logger import setup_logger

logger = setup_logger("image_downloader")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
IMAGES_DIR = Path(__file__).parent.parent.parent / "output" / "images"
USED_IMAGES_FILE = DATA_DIR / "used_images.json"


def _load_used_images() -> dict[str, list[str]]:
    """사용된 이미지 기록을 로드한다. {url: [post_keywords]}"""
    if USED_IMAGES_FILE.exists():
        return json.loads(USED_IMAGES_FILE.read_text(encoding="utf-8"))
    return {}


def _save_used_images(data: dict[str, list[str]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USED_IMAGES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def is_image_used(url: str, keyword: str) -> bool:
    """이미지가 같은 키워드의 다른 포스트에서 이미 사용되었는지 확인한다."""
    used = _load_used_images()
    if url in used:
        # 같은 키워드가 아닌 다른 포스트에서 사용된 경우만 중복으로 판단
        past_keywords = used[url]
        if len(past_keywords) >= 2:  # 2번 이상 사용된 이미지
            return True
    return False


def mark_image_used(url: str, keyword: str) -> None:
    """이미지 사용 기록을 저장한다."""
    used = _load_used_images()
    if url not in used:
        used[url] = []
    if keyword not in used[url]:
        used[url].append(keyword)
    _save_used_images(used)


def download_image(url: str, keyword: str, index: int) -> Path | None:
    """이미지를 다운로드하여 로컬 파일로 저장한다.

    Args:
        url: 이미지 URL
        keyword: 포스트 키워드 (파일명에 사용)
        index: 이미지 순서 번호

    Returns:
        저장된 파일 경로 또는 None
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # 파일명 생성 (키워드 + 순서 + URL 해시)
    safe_keyword = keyword.replace(" ", "_")[:20]
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    ext = "jpg"
    if ".png" in url:
        ext = "png"
    elif ".webp" in url:
        ext = "webp"

    filename = f"{safe_keyword}_{index}_{url_hash}.{ext}"
    filepath = IMAGES_DIR / filename

    # 이미 다운로드된 경우 스킵
    if filepath.exists():
        logger.debug("이미지 캐시 히트: %s", filename)
        return filepath

    try:
        resp = requests.get(url, timeout=15, stream=True)
        if resp.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("이미지 다운로드: %s (%.1fKB)", filename, filepath.stat().st_size / 1024)
            return filepath
        else:
            logger.warning("이미지 다운로드 실패: %s (HTTP %d)", url[:50], resp.status_code)
            return None
    except Exception as e:
        logger.warning("이미지 다운로드 오류: %s → %s", url[:50], e)
        return None


def download_post_images(
    keyword: str, image_urls: list[str]
) -> list[dict[str, str]]:
    """포스트에 사용할 이미지를 모두 다운로드한다.

    Returns:
        [{"url": "원본URL", "local_path": "로컬경로", "filename": "파일명"}, ...]
    """
    results = []

    for i, url in enumerate(image_urls):
        # 중복 체크
        if is_image_used(url, keyword):
            logger.info("이미지 중복 스킵: %s", url[:50])
            continue

        filepath = download_image(url, keyword, i)
        if filepath:
            mark_image_used(url, keyword)
            results.append({
                "url": url,
                "local_path": str(filepath),
                "filename": filepath.name,
            })

    logger.info("이미지 다운로드 완료: %d/%d개", len(results), len(image_urls))
    return results


def get_unique_images(keyword: str, count: int = 7) -> list[str]:
    """중복되지 않은 이미지 URL을 반환한다."""
    from src.content.image_search import IMAGE_POOL, KEYWORD_CATEGORY_MAP

    keyword_lower = keyword.lower()
    used = _load_used_images()

    # 카테고리별 이미지 수집
    matched_cats: list[str] = []
    for term, cats in KEYWORD_CATEGORY_MAP.items():
        if term in keyword_lower:
            matched_cats.extend(cats)
    if not matched_cats:
        matched_cats = ["기본", "건강"]

    all_images: list[str] = []
    seen: set[str] = set()
    for cat in matched_cats:
        for img in IMAGE_POOL.get(cat, []):
            if img not in seen:
                seen.add(img)
                all_images.append(img)
    for img in IMAGE_POOL.get("기본", []):
        if img not in seen:
            seen.add(img)
            all_images.append(img)

    # 사용 횟수가 적은 이미지 우선 선택
    scored = []
    for img in all_images:
        use_count = len(used.get(img, []))
        scored.append((use_count, img))

    scored.sort(key=lambda x: x[0])

    result = [img for _, img in scored[:count]]
    logger.info("고유 이미지 선택: '%s' → %d개 (최소 사용 우선)", keyword, len(result))
    return result
