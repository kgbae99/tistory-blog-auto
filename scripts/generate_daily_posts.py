"""매일 블로그 포스트 3개를 자동 생성하여 output/posts/ 에 저장한다."""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

from src.analytics.dashboard import register_post
from src.content.dedup_checker import check_keyword_duplicate, check_title_duplicate, register_published, filter_unique_keywords
from src.content.image_downloader import download_post_images, get_unique_images
from src.content.image_search import get_header_image, get_images_for_keyword
from src.content.internal_links import find_related_posts, generate_internal_link_html
from src.core.config import load_config
from src.core.logger import setup_logger
from src.coupang.api_client import CoupangAPIClient
from src.coupang.product_search import Product, search_and_filter

logger = setup_logger("daily_posts")

# 블로그 스타일 프롬프트 템플릿
BLOG_STYLE_PROMPT = """당신은 "건강온도사(행복++)" 티스토리 블로그의 전문 콘텐츠 작가입니다.

## 기존 글 스타일 (반드시 따르세요)
- 제목: 클릭을 부르는 호기심 유발형 (15~30자). 아래 패턴 중 하나를 반드시 사용:
  * 궁금증형: "이것만 먹으면 달라진다?", "왜 아무도 안 알려줄까?"
  * 경험형: "직접 해보고 알았다", "한 달 먹어보니 이렇게 바뀌었다"
  * 문제해결형: "아침마다 피곤하다면?", "이 증상 무시하면 큰일납니다"
  * 반전형: "몸에 좋다던 이것, 사실은 독?"
  * 절대 "총정리", "TOP5", "완벽 가이드" 같은 밋밋한 제목 금지
  * 절대 연도(2024, 2025, 2026) 넣지 않기
- H2 섹션 6~7개, H3 사용 안 함
- 각 섹션 300~500자, 문단 4~6문장 (구체적 수치, 예시 포함)
- 문체: ~합니다/~세요/~요 존댓말, 친근하고 실용적
- 각 섹션에 테이블 또는 불릿 포인트 활용
- 내부링크 2개 본문 중간에 삽입
- 마지막 섹션은 "마무리"
- 태그 6~7개

## 글쓰기 규칙
1. 각 H2 섹션에 핑크톤 스타일 테이블 포함 (아래 HTML 형식)
2. 각 섹션 내용은 topic-content div로 감쌈
3. 절대로 목차(TOC)를 생성하지 마세요. 목차, 바로가기, 이동 링크, 목차 테이블 모두 금지. 목차는 시스템이 자동으로 추가합니다.
4. 핵심 요약 카드 5개 (flexbox)
5. FAQ 3개
6. 내부링크: 본문 중간에 자연스럽게 2개 삽입 (아래 제공된 링크 사용)
   {internal_links}

## 테이블 HTML 형식 (중요: 헤더는 반드시 주제에 맞는 실제 항목명을 사용. "항목1/항목2/항목3" 금지!)
## 테이블 데이터는 최소 3행 이상 채울 것
<div class="table-section" style="margin: 20px 0;">
<table style="width: 100%; border-collapse: collapse;">
<thead><tr>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">구분</th>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">핵심 내용</th>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">추천/효과</th>
</tr></thead>
<tbody>
<tr><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">항목A</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">설명</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">효과</td></tr>
<tr><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">항목B</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">설명</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">효과</td></tr>
<tr><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">항목C</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">설명</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">효과</td></tr>
</tbody></table></div>

## 섹션 내용 형식
<div class="topic-content" style="background-color: #fff5f6; padding: 20px; border-radius: 8px; border-left: 4px solid #FFB6C1;">
<p style="color: #333; line-height: 1.8;">내용</p>
</div>

## 이번 글 요청
- 키워드: "{keyword}"
- 카테고리: 건강 & 웰빙
- 쿠팡 추천 상품 (본문에서 자연스럽게 언급): {products}

## 중요 금지사항
- 테이블 헤더에 "항목1", "항목2", "항목3" 절대 사용 금지. 반드시 주제에 맞는 실제 항목명 사용
- 쿠팡 추천 상품 언급 시 본문 맥락과 자연스럽게 연결
- "바꾸하고" 같은 비문 사용 금지

## 출력: 반드시 JSON만
{{"title":"제목","meta_description":"155자이내 SEO 설명","sections":[{{"heading":"H2제목","content":"HTML본문(300자이상)"}}],"summary_cards":["요약1","요약2","요약3","요약4","요약5"],"faq":[{{"q":"질문","a":"답변"}}],"tags":["태그1","태그2"]}}"""

# 이미지 매핑 (Unsplash 검증된 URL)
SECTION_IMAGES = [
    "https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1550572017-edd951b55104?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=486&h=315&fit=crop",
]

HEADER_IMAGES = [
    "https://images.unsplash.com/photo-1522748906645-95d8adfd52c7?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1516575334481-f85287c2c82d?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=486&h=315&fit=crop",
]

SUMMARY_COLORS = [
    ("#ffebee", "#FFCDD2"),
    ("#fce4ec", "#F8BBD0"),
    ("#f3e5f5", "#E1BEE7"),
    ("#e1f5fe", "#B3E5FC"),
    ("#e8f5e9", "#C8E6C9"),
]

FAQ_COLORS = [
    ("#FAE3E3", "#FFB3B3"),
    ("#FDE2E2", "#FF9999"),
    ("#FCE5E5", "#FF8080"),
]


def get_trending_keywords() -> list[str]:
    """카테고리별 1개씩 3개 키워드를 반환한다. 중복 철저 방지."""
    month = datetime.now().month
    day = datetime.now().day

    # 3개 카테고리 로테이션 (매일 다른 조합)
    CATEGORY_POOLS = {
        "건강/질병": [
            "면역력 높이는 생활습관", "혈압 낮추는 방법", "당뇨 예방 식습관",
            "간 건강에 좋은 음식", "관절 건강 지키는 방법", "눈 건강 관리법",
            "장 건강 개선법", "수면 질 높이는 방법", "스트레스 해소법",
            "비타민D 부족 증상", "프로바이오틱스 효능", "탈모 예방법",
            "빈혈 증상과 예방법", "갑상선 기능 저하 관리", "골다공증 예방법",
            "건강검진 필수 항목", "종합보험 건강 혜택", "실비보험 청구 방법",
            "치과 임플란트 비용", "라식 라섹 비교", "건강기능식품 선택 가이드",
            "암보험 가입 전 체크리스트", "의료실비 보장 범위",
            "허리 디스크 예방법", "손목터널증후군 자가치료", "역류성 식도염 원인",
            "대상포진 예방접종 시기", "통풍 원인과 관리법", "어지러움 원인 총정리",
            "만성피로 원인과 해결법", "손발 저림 원인", "이명 원인과 치료",
            "편두통 예방법", "과민성 대장증후군 관리", "요산 수치 낮추는 법",
            "혈액순환 개선법", "갱년기 증상 완화법", "치질 예방과 관리법",
            "위염 원인과 식이요법", "고지혈증 관리법", "족저근막염 치료법",
            "어깨 오십견 운동법", "눈 피로 해소법", "입냄새 원인과 해결법",
        ],
        "음식/영양": [
            "아침 공복에 좋은 음식", "피로 회복에 좋은 음식", "봄나물 효능과 종류",
            "다이어트에 좋은 음식", "면역력 높이는 음식 BEST", "혈관에 좋은 음식",
            "항산화 식품 추천", "단백질 풍부한 식단", "비타민 많은 과일",
            "장 건강에 좋은 발효식품", "해독에 좋은 차", "콜레스테롤 낮추는 음식",
            "눈에 좋은 영양소", "뼈에 좋은 음식", "간에 좋은 음식",
            "다이어트 보조제 추천", "단백질 보충제 비교", "혈당 관리 식단",
            "체중감량 식이요법", "키토제닉 다이어트 식단",
            "오메가3 효능과 복용법", "마그네슘 부족 증상", "아연 효능 총정리",
            "루테인 지아잔틴 효능", "코엔자임Q10 효능", "밀크씨슬 간건강 효과",
            "콜라겐 보충제 효과", "비오틴 탈모 효과", "칼슘 흡수 높이는 법",
            "철분 많은 음식 TOP10", "식이섬유 많은 음식", "저탄수화물 식단 가이드",
            "글루텐 프리 식단", "지중해 식단 효과", "항염증 음식 TOP7",
            "슈퍼푸드 종류와 효능", "견과류 효능 비교", "녹차 카테킨 효능",
            "생강 효능과 부작용", "양배추즙 효능", "석류 효능과 먹는법",
        ],
        "뷰티/생활": [
            "봄 스킨케어 루틴", "자외선 차단제 추천", "보습 크림 고르는 법",
            "봄철 다이어트 식단", "홈트레이닝 추천 운동", "환절기 피부 관리",
            "꽃가루 알레르기 예방법", "미세먼지 건강관리", "춘곤증 극복 방법",
            "체력 키우는 방법", "스트레칭 효과", "물 많이 마시면 좋은 점",
            "아침 루틴 만드는 법", "숙면 취하는 방법", "노화 방지 습관",
            "피부과 시술 비교", "탈모 치료 비용", "치아 미백 방법",
            "홈트 운동기구 추천", "공기청정기 추천",
            "다크서클 없애는 법", "모공 줄이는 방법", "여드름 흉터 관리법",
            "목주름 예방법", "손톱 건강 관리법", "두피 케어 방법",
            "발 각질 제거법", "건조한 피부 관리법", "눈밑 주름 개선법",
            "체형 교정 운동", "플랭크 올바른 자세", "스쿼트 무릎 보호법",
            "필라테스 효과", "요가 초보 시작법", "런닝 올바른 자세",
            "하루 만보 걷기 효과", "아침 운동 vs 저녁 운동", "점프로프 다이어트",
        ],
    }

    categories = list(CATEGORY_POOLS.keys())
    # 날짜 기반 카테고리 순서 변경 (매일 다른 조합)
    cat_offset = day % len(categories)
    ordered_cats = categories[cat_offset:] + categories[:cat_offset]

    # 유입 데이터 기반 추천 키워드 반영
    recommended = []
    try:
        trend_file = Path(__file__).parent.parent / "data" / "trend_insights.json"
        if trend_file.exists():
            insights = json.loads(trend_file.read_text(encoding="utf-8"))
            recommended = insights.get("recommended_keywords", [])
    except Exception:
        pass

    result = []
    for cat in ordered_cats:
        pool = CATEGORY_POOLS[cat]

        # 유입 추천 키워드 중 이 카테고리에 해당하는 것 우선
        selected = None
        for rec in recommended:
            if rec in pool and rec not in result:
                selected = rec
                break

        if not selected:
            # 날짜 기반 순환 선택
            idx = (day + len(result)) % len(pool)
            selected = pool[idx]

        result.append(selected)

    logger.info("카테고리별 키워드: %s", list(zip(ordered_cats, result)))
    return result


# 세션 내 사용된 상품 ID 추적 (포스트 간 중복 방지)
_used_product_ids: set = set()
_used_product_names: set = set()


def search_coupang_products(keyword: str) -> list:
    """쿠팡에서 키워드 관련 상품을 검색한다. 스마트 매처 + 캐시 폴백."""
    cache_file = Path(__file__).parent.parent / "data" / "coupang_cache.json"

    def _load_cache() -> dict:
        if cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))
        return {}

    def _save_cache(cache: dict) -> None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        from src.coupang.smart_matcher import get_search_queries

        config = load_config()
        client = CoupangAPIClient(config.coupang)

        # 1차: 키워드에서 핵심 단어 1~2개로 검색 (긴 키워드 → 짧게)
        short_keyword = " ".join(keyword.split()[:2])
        products = search_and_filter(client, short_keyword, count=3)

        # 2차: 결과 부족 시 스마트 매처 검색어로 재시도
        if len(products) < 3:
            queries = get_search_queries(keyword, count=3)
            for q in queries:
                if len(products) >= 3:
                    break
                extra = search_and_filter(client, q, count=3 - len(products))
                existing_ids = {p.product_id for p in products}
                for p in extra:
                    if p.product_id not in existing_ids and len(products) < 3:
                        products.append(p)
                        existing_ids.add(p.product_id)

            if products:
                logger.info("스마트 매처 보충: '%s' → %d개", keyword, len(products))

        # 캐시 저장 (성공 시)
        if products:
            cache = _load_cache()
            cache[keyword] = [
                {
                    "product_id": p.product_id,
                    "product_name": p.product_name,
                    "product_price": p.product_price,
                    "product_image": p.product_image,
                    "product_url": p.product_url,
                    "is_rocket": p.is_rocket,
                    "is_free_shipping": p.is_free_shipping,
                    "category_name": p.category_name,
                    "keyword": p.keyword,
                    "rank": p.rank,
                }
                for p in products
            ]
            _save_cache(cache)
            # 세션 중복 필터 (포스트 간 동일 상품 방지)
            unique = []
            for p in products:
                pid = str(p.product_id or "")
                pname = str(p.product_name or "")
                if pid and pid in _used_product_ids:
                    continue
                if pname and pname in _used_product_names:
                    continue
                unique.append(p)
                if pid:
                    _used_product_ids.add(pid)
                if pname:
                    _used_product_names.add(pname)
            return unique[:3]

        # 3차: 캐시 폴백 (API 실패 시) - 키워드별 다른 캐시 사용
        cache = _load_cache()
        if not cache:
            return []

        def _pick_from_cache(candidates: list) -> list:
            """캐시 상품 목록에서 세션 내 중복 제거 후 반환."""
            result = []
            for p_data in candidates:
                # 캐시는 camelCase, Product 객체는 snake_case
                pid = str(p_data.get("productId") or p_data.get("product_id") or "")
                pname = str(p_data.get("productName") or p_data.get("product_name") or "")
                if not pid and not pname:
                    continue
                if pid and pid in _used_product_ids:
                    continue
                if pname and pname in _used_product_names:
                    continue
                result.append(Product.from_api_response(p_data))
                if pid:
                    _used_product_ids.add(pid)
                if pname:
                    _used_product_names.add(pname)
                if len(result) >= 3:
                    break
            return result

        # 같은 키워드 캐시
        if keyword in cache and cache[keyword]:
            logger.info("쿠팡 캐시 사용: '%s' → %d개", keyword, len(cache[keyword]))
            return _pick_from_cache(cache[keyword])

        # 키워드-캐시 카테고리 연관성 매핑 (주제에 맞는 상품 우선 선택)
        KEYWORD_CACHE_MAP = {
            "다이어트": ["체중계", "운동"],
            "운동": ["운동", "체중계"],
            "스트레칭": ["운동", "요가매트"],
            "홈트": ["운동"],
            "피부": ["크림"],
            "스킨케어": ["크림"],
            "뷰티": ["크림"],
            "숙면": ["베개", "차"],
            "수면": ["베개", "차"],
            "면역": ["비타민", "영양제", "유산균"],
            "비타민": ["비타민", "영양제"],
            "혈압": ["오메가3", "영양제", "차"],
            "혈당": ["영양제", "비타민", "차"],
            "콜레스테롤": ["오메가3", "영양제", "차"],
            "관절": ["영양제", "운동"],
            "간": ["영양제", "비타민", "차"],
            "해독": ["차", "유산균"],
            "차": ["차"],
            "알레르기": ["마스크", "비타민"],
            "미세먼지": ["마스크"],
            "장건강": ["유산균", "영양제"],
            "보험": ["비타민", "영양제"],
            "임플란트": ["비타민", "영양제"],
        }

        # 키워드에서 매칭되는 캐시 카테고리 우선 선택
        preferred_keys = []
        kw_lower = keyword.lower()
        for kw_part, cache_cats in KEYWORD_CACHE_MAP.items():
            if kw_part in kw_lower:
                preferred_keys.extend(cache_cats)

        import hashlib
        kw_hash = int(hashlib.md5(keyword.encode()).hexdigest(), 16)
        cache_keys = list(cache.keys())

        # 연관 카테고리를 앞에, 나머지를 뒤에 배치
        if preferred_keys:
            matched = [k for k in preferred_keys if k in cache_keys]
            remaining = [k for k in cache_keys if k not in matched]
            cache_keys = matched + remaining
        if cache_keys:
            # 여러 캐시 키를 순회하며 중복 없는 상품 모으기
            idx = kw_hash % len(cache_keys)
            collected = []
            for offset_i in range(len(cache_keys)):
                selected_key = cache_keys[(idx + offset_i) % len(cache_keys)]
                cached_products = cache[selected_key]
                if cached_products:
                    collected.extend(cached_products)
                if len(collected) >= 9:
                    break
            if collected:
                logger.info("쿠팡 캐시 대체: '%s' → %d개 후보", keyword, len(collected))
                return _pick_from_cache(collected)

        return []
    except Exception as e:
        logger.warning("쿠팡 검색 실패 '%s': %s", keyword, e)
        return []


def generate_content(keyword: str, products: list) -> dict:
    """Gemini로 블로그 콘텐츠를 생성한다."""
    product_names = ", ".join(p.product_name[:30] for p in products) if products else "관련 건강제품"

    # 내부 링크 자동 매칭
    related = find_related_posts(keyword, max_results=2)
    if related:
        link_lines = "\n   ".join(
            f'- <a style="color: #c0392b; text-decoration: underline;" href="{r["url"]}">{r["title"]}</a>'
            for r in related
        )
    else:
        link_lines = '- <a style="color: #c0392b; text-decoration: underline;" href="https://kgbae2369.tistory.com/16">관절에 좋은 음식 BEST 7</a>\n   - <a style="color: #c0392b; text-decoration: underline;" href="https://kgbae2369.tistory.com/28">혈압 낮추는 식단 가이드</a>'

    prompt = BLOG_STYLE_PROMPT.format(keyword=keyword, products=product_names, internal_links=link_lines)

    # GPT-5 Mini 우선, Gemini 폴백
    text = ""
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
            )
            text = response.choices[0].message.content or ""
            logger.info("  GPT-5 Mini 생성 완료")
        except Exception as e:
            logger.warning("  GPT-5 Mini 실패: %s → Gemini 폴백", e)

    if not text and os.getenv("GEMINI_API_KEY"):
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = response.text
        logger.info("  Gemini 폴백 생성 완료")
    if "```json" in text:
        json_str = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        json_str = text.split("```")[1].split("```")[0]
    else:
        json_str = text

    return json.loads(json_str.strip())


def build_coupang_html(products: list) -> str:
    """쿠팡 상품 HTML을 생성한다."""
    if not products:
        return ""

    items = []
    for p in products[:3]:
        items.append(f"""<div style="margin-bottom: 20px; padding: 18px; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa;">
<a href="{p.product_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: #333;">
<div style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap;">
<img src="{p.product_image}" alt="{p.product_name}" style="width: 130px; height: 130px; object-fit: contain; border-radius: 6px; background: #fff; border: 1px solid #eee;" loading="lazy" />
<div style="flex: 1; min-width: 200px;">
<p style="font-size: 17px; font-weight: bold; color: #2c3e50; margin: 0 0 8px 0;">{p.product_name}</p>
<p style="font-size: 20px; font-weight: bold; color: #e44d26; margin: 0 0 6px 0;">{p.product_price:,}원</p>
<p style="font-size: 13px; color: #888; margin: 0 0 10px 0;">{"🚀 로켓배송" if p.is_rocket else "일반배송"}</p>
<span style="display: inline-block; padding: 8px 24px; background: #e44d26; color: white; border-radius: 4px; font-size: 14px; font-weight: bold;">최저가 확인하기</span>
</div></div></a></div>""")

    return "\n".join(items)


def build_adsense_ad(slot_id: str, ad_format: str = "auto") -> str:
    """애드센스 광고 코드를 생성한다."""
    pub_id = os.getenv("ADSENSE_PUB_ID", "")
    if not pub_id or not slot_id:
        return ""
    if ad_format == "infeed":
        return f"""<div style="margin: 25px 0; text-align: center; clear: both;">
<ins class="adsbygoogle" style="display:block" data-ad-format="fluid" data-ad-layout-key="-fb+5w+4e-db+86" data-ad-client="{pub_id}" data-ad-slot="{slot_id}"></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>"""
    return f"""<div style="margin: 25px 0; text-align: center; clear: both;">
<ins class="adsbygoogle" style="display:block" data-ad-client="{pub_id}" data-ad-slot="{slot_id}" data-ad-format="auto" data-full-width-responsive="true"></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>"""


def build_full_html(data: dict, products: list, post_index: int, keyword: str = "") -> str:
    """전체 블로그 포스트 HTML을 조립한다."""
    # 키워드 기반 이미지 자동 매칭 (중복 완전 방지)
    if keyword:
        all_images = get_unique_images(keyword, count=8)
        header_img = all_images[0] if all_images else HEADER_IMAGES[0]
        section_images = all_images[1:] if len(all_images) > 1 else all_images
        # 이미지 다운로드
        downloaded = download_post_images(keyword, all_images)
        if downloaded:
            logger.info("  이미지 %d개 다운로드 완료", len(downloaded))
    else:
        header_img = HEADER_IMAGES[post_index % len(HEADER_IMAGES)]
        section_images = SECTION_IMAGES
    sections = data.get("sections", [])
    tags = data.get("tags", [])
    summary_cards = data.get("summary_cards", [])
    faqs = data.get("faq", [])
    coupang_html = build_coupang_html(products)

    # 애드센스 광고 슬롯
    ad_top = build_adsense_ad(os.getenv("ADSENSE_SLOT_TOP", ""))
    ad_mid = build_adsense_ad(os.getenv("ADSENSE_SLOT_MID", ""), "infeed")
    ad_bottom = build_adsense_ad(os.getenv("ADSENSE_SLOT_BOTTOM", ""))

    parts = []

    # 대표 이미지 (키워드 alt 삽입)
    img_alt = keyword if keyword else data.get("title", "건강정보")
    parts.append(f'<figure style="text-align: center; margin: 0 0 20px 0;"><img src="{header_img}" alt="{img_alt}" style="max-width:100%; height:auto; border-radius:8px;" width="486" /></figure>')
    parts.append('<p>&nbsp;</p>')

    # H1 제목 + 도입부
    intro = sections[0]["content"] if sections else ""
    toc_items = "".join(
        f'<p style="margin: 8px 0;"><a style="color: #2c3e50; text-decoration: none;" href="#sec{i}">{i}. {s["heading"]}</a></p>'
        for i, s in enumerate(sections[1:], 1) if s["heading"] != "마무리"
    )

    parts.append(f"""<div style="background-color: #ffffff; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
<h1 style="color: #2c3e50; border-bottom: 2px solid #FFE4E8; padding-bottom: 10px;">{data.get("title","")}</h1>
<div class="topic-content" style="background-color: #fff5f6; padding: 20px; border-radius: 8px; border-left: 4px solid #FFB6C1; margin-top: 20px;">
{intro}
</div>
<div style="background-color: #fff5f6; padding: 20px; border-radius: 8px; border-left: 4px solid #FFB6C1; margin-top: 20px;">
<h3 style="color: #2c3e50;">목차</h3>
{toc_items}
</div>
</div>""")

    # 본문 섹션
    for i, section in enumerate(sections[1:], 1):
        if section["heading"] == "마무리":
            continue
        img = section_images[(i - 1) % len(section_images)]
        parts.append(f"""<div id="sec{i}" style="background-color: #ffffff; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
<h2 style="color: #2c3e50; border-bottom: 2px solid #FFE4E8; padding-bottom: 10px;">{section["heading"]}</h2>
<figure style="text-align: center; margin: 15px 0;"><img src="{img}" alt="{img_alt}" style="max-width:100%; height:auto; border-radius:8px;" width="486" /></figure>
{section["content"]}
</div>""")

        # 광고 삽입: 1번째 H2 뒤 (상단), 3번째 H2 뒤 (중간 인피드)
        if i == 1 and ad_top:
            parts.append(ad_top)
        elif i == 3 and ad_mid:
            parts.append(ad_mid)

    # 핵심 요약 카드
    if summary_cards:
        cards = ""
        for j, card in enumerate(summary_cards[:5]):
            bg, border = SUMMARY_COLORS[j % len(SUMMARY_COLORS)]
            cards += f'<div style="width: 250px; background-color: {bg}; padding: 20px; border-radius: 8px; border-left: 4px solid {border};"><p style="font-weight: bold; margin: 0;">{card}</p></div>\n'
        parts.append(f"""<div style="background-color: #ffffff; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center;">
<h2 style="color: #2c3e50; border-bottom: 2px solid #FFE4E8; padding-bottom: 10px;">핵심 요약</h2>
<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px;">
{cards}</div></div>""")

    # FAQ
    if faqs:
        faq_items = ""
        for j, faq in enumerate(faqs[:3]):
            bg, border = FAQ_COLORS[j % len(FAQ_COLORS)]
            faq_items += f"""<div style="background: {bg}; padding: 15px; border-radius: 8px; border-left: 4px solid {border}; margin-bottom: 10px;">
<h3 style="font-size: 17px;">{faq["q"]}</h3>
<p style="margin: 0; padding: 8px 0;">{faq["a"]}</p></div>\n"""
        parts.append(f"""<div style="background-color: #ffffff; border-radius: 8px; padding: 10px 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
<h2 style="color: #2c3e50; border-bottom: 2px solid #FFE4E8; padding-bottom: 8px;">자주 묻는 질문</h2>
<div style="padding: 10px; margin-top: 20px;">
{faq_items}</div></div>""")

    # 결론 전 광고
    if ad_bottom:
        parts.append(ad_bottom)

    # 마무리
    conclusion = ""
    for s in sections:
        if s["heading"] == "마무리":
            conclusion = s["content"]
            break

    parts.append(f"""<div style="background-color: #ffffff; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
<h2 style="color: #2c3e50; border-bottom: 2px solid #FFE4E8; padding-bottom: 10px;">마무리</h2>
<div class="topic-content" style="background-color: #fff5f6; padding: 20px; border-radius: 8px; border-left: 4px solid #FFB6C1;">
{conclusion}
</div>
<p style="color: #888; font-size: 13px; margin-top: 15px; line-height: 1.6;">※ 본 글은 건강 정보를 요약한 것이며, 질병 치료 목적이 아닙니다.</p>
</div>""")

    # 쿠팡 추천 상품
    if coupang_html:
        parts.append(f"""<div style="background-color: #ffffff; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
<h2 style="color: #2c3e50; border-bottom: 2px solid #FFE4E8; padding-bottom: 10px;">건강온도사 추천 제품</h2>
<p style="color: #666; font-size: 14px; margin-bottom: 20px;">이 글의 주제에 도움이 될 수 있는 제품들을 선별했습니다.</p>
{coupang_html}
<p style="color: #999; font-size: 12px; margin-top: 15px;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
</div>""")

    # 태그
    tag_str = ", ".join(tags)
    parts.append(f'<div style="margin-bottom: 30px;"><p>{tag_str}</p></div>')

    # 쿠팡 배너 (최하단)
    parts.append("""<div style="text-align: center; margin: 20px 0 30px 0;">
<a href="https://link.coupang.com/a/d4YwkD" target="_blank" referrerpolicy="unsafe-url"><img src="https://ads-partners.coupang.com/banners/882911?subId=&traceId=V0-301-879dd1202e5c73b2-I882911&w=728&h=90" alt="" style="max-width:100%; height:auto;" /></a>
</div>""")

    result = "\n\n".join(parts)

    # 후처리: 이미지 alt 속성에 키워드 삽입 (빈 alt → SEO 최적화)
    alt_text = keyword if keyword else data.get("title", "건강정보")
    result = re.sub(r'alt=""', f'alt="{alt_text}"', result)
    result = re.sub(r'<a[^>]*href="#(?!sec\d)[^"]*"[^>]*>(.*?)</a>', r'\1', result)  # GPT 앵커 제거 (시스템 #sec 유지)

    # GPT가 생성한 중복 목차 제거 (시스템 목차만 유지)
    # "목차" 제목을 가진 섹션 중 시스템이 만든 것(h3) 외의 것 제거
    result = re.sub(
        r'<h2[^>]*>[^<]*목차[^<]*</h2>\s*(?:<[^>]+>[\s\S]*?</(?:div|table|ul|ol)>)',
        '',
        result,
        flags=re.IGNORECASE,
    )

    return result


def build_tool_page(title: str, tags: list, blog_html: str, meta_desc: str = "") -> str:
    """복사 도구 페이지 HTML을 생성한다."""
    tag_str = ", ".join(tags)
    meta_tag = f'<meta name="description" content="{meta_desc}">' if meta_desc else ""
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
{meta_tag}
<title>{title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:'Malgun Gothic',sans-serif;background:#f0f2f5;color:#333}}
.tool-panel{{position:sticky;top:0;z-index:1000;background:#2c3e50;color:#fff;padding:20px 30px;box-shadow:0 4px 12px rgba(0,0,0,0.3)}}
.tool-panel h2{{font-size:18px;margin-bottom:15px;color:#FFB6C1}}
.field-row{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
.field-label{{min-width:70px;font-weight:bold;font-size:13px;color:#FFE4E8}}
.field-value{{flex:1;background:#34495e;color:#fff;padding:10px 14px;border-radius:6px;font-size:14px;border:1px solid #4a6274;user-select:all}}
.copy-btn{{padding:8px 16px;border:none;border-radius:6px;font-size:13px;font-weight:bold;cursor:pointer;transition:all 0.2s}}
.btn-small{{background:#FFB6C1;color:#2c3e50}}.btn-small:hover{{background:#FF9EAE}}
.btn-html{{background:linear-gradient(135deg,#e44d26,#f16529);color:#fff;padding:12px 30px;font-size:15px}}
.btn-row{{display:flex;gap:10px;align-items:center;margin-top:5px}}
.copy-toast{{display:none;background:#27ae60;color:#fff;padding:6px 14px;border-radius:4px;font-size:13px}}
.copy-toast.show{{display:inline-block}}
.preview-area{{max-width:760px;margin:30px auto;padding:0 20px}}
.preview-label{{text-align:center;color:#999;font-size:13px;margin-bottom:15px;padding:8px;border:1px dashed #ccc;border-radius:6px}}
</style></head><body>
<div class="tool-panel">
<h2>티스토리 발행 도구</h2>
<div class="field-row"><span class="field-label">제목</span><div class="field-value" id="t">{title}</div><button class="copy-btn btn-small" onclick="c('t',this)">복사</button></div>
<div class="field-row"><span class="field-label">카테고리</span><div class="field-value" id="cat">건강 &amp; 웰빙</div><button class="copy-btn btn-small" onclick="c('cat',this)">복사</button></div>
<div class="field-row"><span class="field-label">태그</span><div class="field-value" id="tag">{tag_str}</div><button class="copy-btn btn-small" onclick="c('tag',this)">복사</button></div>
<div class="btn-row"><button class="copy-btn btn-html" onclick="ch(this)">HTML 전체 복사 (티스토리 붙여넣기용)</button><span class="copy-toast" id="toast">복사 완료!</span></div>
</div>
<div class="preview-area">
<div class="preview-label">아래는 미리보기입니다. 위 버튼으로 복사 후 티스토리 HTML 모드에 붙여넣으세요.<br/><strong>💡 이미지 교체 팁:</strong> 발행 후 각 이미지를 클릭 → 삭제 → 같은 위치에 원하는 이미지를 드래그&드롭으로 업로드하면 티스토리 첨부파일로 등록됩니다.</div>
<div id="blog-html">{blog_html}</div>
</div>
<script>
function c(id,btn){{navigator.clipboard.writeText(document.getElementById(id).innerText).then(()=>{{const o=btn.innerText;btn.innerText='완료!';btn.style.background='#27ae60';btn.style.color='#fff';setTimeout(()=>{{btn.innerText=o;btn.style.background='';btn.style.color=''}},1500)}})}}
function ch(btn){{navigator.clipboard.writeText(document.getElementById('blog-html').innerHTML).then(()=>{{document.getElementById('toast').classList.add('show');btn.style.background='linear-gradient(135deg,#27ae60,#2ecc71)';btn.innerText='복사 완료!';setTimeout(()=>{{document.getElementById('toast').classList.remove('show');btn.style.background='';btn.innerText='HTML 전체 복사 (티스토리 붙여넣기용)'}},2000)}})}}
</script></body></html>"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.environ["TZ"] = "GMT+0"

    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(__file__).parent.parent / "output" / "posts" / today
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_keywords = get_trending_keywords()
    keywords = filter_unique_keywords(raw_keywords)

    # 중복 제거 후 부족하면 같은 카테고리에서 대체 키워드 선택
    if len(keywords) < 3:
        all_pools = [
            "면역력 높이는 생활습관", "혈압 낮추는 방법", "당뇨 예방 식습관",
            "아침 공복에 좋은 음식", "피로 회복에 좋은 음식", "봄나물 효능과 종류",
            "봄 스킨케어 루틴", "자외선 차단제 추천", "홈트레이닝 추천 운동",
            "간 건강에 좋은 음식", "관절 건강 지키는 방법", "장 건강 개선법",
            "항산화 식품 추천", "콜레스테롤 낮추는 음식", "해독에 좋은 차",
            "환절기 피부 관리", "스트레칭 효과", "숙면 취하는 방법",
        ]
        for kw in all_pools:
            if kw not in keywords and not check_keyword_duplicate(kw):
                dup = check_title_duplicate(kw, threshold=0.5)
                if not dup:
                    keywords.append(kw)
            if len(keywords) >= 3:
                break
    keywords = keywords[:3]
    logger.info("=== %s 일일 포스트 생성 시작 (키워드: %s) ===", today, keywords)

    results = []

    for i, keyword in enumerate(keywords):
        logger.info("[%d/3] 키워드: '%s'", i + 1, keyword)

        # 1. 쿠팡 상품 검색
        products = search_coupang_products(keyword)
        logger.info("  쿠팡: %d개 상품", len(products))

        # 2. Gemini 콘텐츠 생성
        logger.info("  Gemini 생성 중...")
        data = generate_content(keyword, products)
        logger.info("  제목: %s", data.get("title", ""))

        # 3. 전체 HTML 조립
        blog_html = build_full_html(data, products, i, keyword=keyword)

        # 4. 도구 페이지 생성
        tool_html = build_tool_page(
            data.get("title", keyword),
            data.get("tags", [keyword]),
            blog_html,
            meta_desc=data.get("meta_description", ""),
        )

        # 5. 파일 저장
        safe_name = keyword.replace(" ", "_")[:20]
        filename = f"post_{i + 1}_{safe_name}.html"
        filepath = output_dir / filename
        filepath.write_text(tool_html, encoding="utf-8")
        logger.info("  저장: %s", filepath)

        # 제목 중복 체크
        title = data.get("title", keyword)
        dup = check_title_duplicate(title)
        if dup:
            logger.warning("  제목 중복! '%s' (유사도: %.0f%%) → 제목 수정 필요", dup["existing_title"][:30], dup["similarity"] * 100)

        # 발행 DB에 등록 (중복 추적용)
        register_published(title=title, keyword=keyword, date=today)

        # 대시보드에 포스트 등록
        register_post(
            title=data.get("title", keyword),
            keyword=keyword,
            category="건강정보",
            tags=data.get("tags", []),
            coupang_products=len(products),
            adsense_slots=3,
        )

        results.append({
            "keyword": keyword,
            "title": data.get("title", ""),
            "tags": data.get("tags", []),
            "file": str(filepath),
        })

        # API 속도 제한 방지
        if i < len(keywords) - 1:
            time.sleep(3)

    # 결과 요약 저장
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info("=== 완료: %d개 포스트 생성 → %s ===", len(results), output_dir)

    # 텔레그램 알림
    try:
        from src.notify.telegram import notify_posts_generated
        notify_posts_generated(results)
    except Exception as e:
        logger.warning("텔레그램 알림 실패: %s", e)

    # 콘솔 출력
    print(f"\n{'='*50}")
    print(f"  {today} 블로그 포스트 {len(results)}개 생성 완료")
    print(f"{'='*50}")
    for r in results:
        print(f"  [{r['keyword']}]")
        print(f"    제목: {r['title']}")
        print(f"    파일: {r['file']}")
    print(f"\n  저장 경로: {output_dir}")


if __name__ == "__main__":
    main()
