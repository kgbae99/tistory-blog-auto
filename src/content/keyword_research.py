"""키워드 리서치 자동화 - 네이버/구글 자동완성 기반 롱테일 키워드 발굴."""

from __future__ import annotations

import requests

from src.core.logger import setup_logger

logger = setup_logger("keyword_research")


def get_naver_suggestions(keyword: str) -> list[str]:
    """네이버 자동완성에서 관련 키워드를 가져온다."""
    try:
        url = "https://ac.search.naver.com/nx/ac"
        params = {
            "q": keyword,
            "con": 1,
            "frm": "nv",
            "ans": 2,
            "r_format": "json",
            "r_enc": "UTF-8",
            "r_unicode": 0,
            "t_koreng": 1,
            "run": 2,
            "rev": 4,
            "q_enc": "UTF-8",
        }
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()

        suggestions = []
        for item_group in data.get("items", []):
            for item in item_group:
                if isinstance(item, list) and item:
                    suggestions.append(item[0])

        logger.info("네이버 자동완성 '%s': %d개", keyword, len(suggestions))
        return suggestions[:10]
    except Exception as e:
        logger.warning("네이버 자동완성 실패: %s", e)
        return []


def get_google_suggestions(keyword: str) -> list[str]:
    """구글 자동완성에서 관련 키워드를 가져온다."""
    try:
        url = "https://suggestqueries.google.com/complete/search"
        params = {
            "client": "firefox",
            "q": keyword,
            "hl": "ko",
        }
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()

        suggestions = data[1] if len(data) > 1 else []
        logger.info("구글 자동완성 '%s': %d개", keyword, len(suggestions))
        return suggestions[:10]
    except Exception as e:
        logger.warning("구글 자동완성 실패: %s", e)
        return []


def expand_keywords(seed_keyword: str) -> list[dict[str, str]]:
    """시드 키워드에서 롱테일 키워드를 확장한다."""
    naver = get_naver_suggestions(seed_keyword)
    google = get_google_suggestions(seed_keyword)

    # 중복 제거 + 합치기
    seen: set[str] = set()
    expanded: list[dict[str, str]] = []

    for kw in naver:
        if kw not in seen and kw != seed_keyword:
            seen.add(kw)
            expanded.append({"keyword": kw, "source": "네이버"})

    for kw in google:
        if kw not in seen and kw != seed_keyword:
            seen.add(kw)
            expanded.append({"keyword": kw, "source": "구글"})

    logger.info("키워드 확장: '%s' → %d개 롱테일", seed_keyword, len(expanded))
    return expanded


def score_keyword(keyword: str) -> dict:
    """키워드의 블로그 적합도를 평가한다."""
    naver_count = len(get_naver_suggestions(keyword))
    google_count = len(get_google_suggestions(keyword))

    # 적합도 점수 (자동완성 많으면 검색량 높음)
    search_volume = "높음" if (naver_count + google_count) > 12 else (
        "중간" if (naver_count + google_count) > 6 else "낮음"
    )

    # 경쟁도 (글자수 짧으면 경쟁 높음)
    word_count = len(keyword.split())
    competition = "높음" if word_count <= 2 else (
        "중간" if word_count <= 4 else "낮음"
    )

    # 롱테일 추천 (검색량 중간 + 경쟁 낮음이 최적)
    is_recommended = search_volume in ("중간", "높음") and competition in ("중간", "낮음")

    return {
        "keyword": keyword,
        "naver_suggestions": naver_count,
        "google_suggestions": google_count,
        "search_volume": search_volume,
        "competition": competition,
        "recommended": is_recommended,
    }


def research_topic(seed: str, max_results: int = 10) -> list[dict]:
    """주제에 대한 종합 키워드 리서치를 수행한다."""
    expanded = expand_keywords(seed)

    results = []
    for item in expanded[:max_results]:
        score = score_keyword(item["keyword"])
        score["source"] = item["source"]
        results.append(score)

    # 추천 키워드 우선 정렬
    results.sort(key=lambda x: (x["recommended"], x["naver_suggestions"]), reverse=True)

    recommended = [r for r in results if r["recommended"]]
    logger.info(
        "키워드 리서치 완료: '%s' → %d개 중 %d개 추천",
        seed, len(results), len(recommended),
    )
    return results
