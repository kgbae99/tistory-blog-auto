"""IT/가젯 블로그(uyoblog) 포스트 3개를 자동 생성한다."""

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

from src.content.dedup_checker import check_title_duplicate, register_published
from src.content.image_downloader import download_post_images
from src.core.logger import setup_logger
from src.coupang.api_client import CoupangAPIClient, CoupangConfig

logger = setup_logger("it_posts")

BLOG_STYLE_PROMPT = """당신은 "테크온도(IT++)" 티스토리 블로그의 IT 전문 리뷰어입니다.

## 글 스타일
- 제목: 짧고 강렬한 호기심 유발형 (15~30자)
- H2 섹션 6~7개, H3 사용 안 함
- 각 섹션 300~500자, 문단 4~6문장 (구체적 스펙, 가격, 비교 포함)
- 문체: ~합니다/~세요/~요 존댓말, 친근하고 실용적
- 각 섹션에 테이블 또는 불릿 포인트 활용
- 마지막 섹션은 "마무리"
- 태그 6~7개

## 글쓰기 규칙
1. 각 H2 섹션에 블루톤 스타일 테이블 포함 (아래 HTML 형식)
2. 각 섹션 내용은 topic-content div로 감쌈
3. 절대로 목차(TOC)를 생성하지 마세요
4. 핵심 요약 카드 5개 (flexbox)
5. FAQ 3개
6. 제품 비교 시 장단점 명확히

## 테이블 HTML 형식
<div class="table-section" style="margin: 20px 0;">
<table style="width: 100%; border-collapse: collapse;">
<thead><tr>
<th style="padding: 12px; border: 1px solid #90CAF9; background-color: #E3F2FD; color: #1565C0;">구분</th>
<th style="padding: 12px; border: 1px solid #90CAF9; background-color: #E3F2FD; color: #1565C0;">스펙/특징</th>
<th style="padding: 12px; border: 1px solid #90CAF9; background-color: #E3F2FD; color: #1565C0;">추천/평가</th>
</tr></thead>
<tbody>
<tr><td style="padding: 12px; border: 1px solid #90CAF9; color: #333;">제품A</td><td style="padding: 12px; border: 1px solid #90CAF9; color: #333;">스펙</td><td style="padding: 12px; border: 1px solid #90CAF9; color: #333;">평가</td></tr>
</tbody></table></div>

## 섹션 내용 형식
<div class="topic-content" style="background-color: #F5F9FF; padding: 20px; border-radius: 8px; border-left: 4px solid #90CAF9;">
<p style="color: #333; line-height: 1.8;">내용</p>
</div>

## 이번 글 요청
- 키워드: "{keyword}"
- 카테고리: IT/가젯
- 쿠팡 추천 상품 (본문에서 자연스럽게 언급): {products}

## 출력: 반드시 JSON만
{{"title":"제목","meta_description":"155자이내 SEO 설명","sections":[{{"heading":"H2제목","content":"HTML본문(300자이상)"}}],"summary_cards":["요약1","요약2","요약3","요약4","요약5"],"faq":[{{"q":"질문","a":"답변"}}],"tags":["태그1","태그2"]}}"""

# IT 이미지 (Unsplash)
SECTION_IMAGES = [
    "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=486&h=315&fit=crop",
]

SUMMARY_COLORS = [
    ("#E3F2FD", "#90CAF9"),
    ("#E1F5FE", "#81D4FA"),
    ("#E8EAF6", "#9FA8DA"),
    ("#F3E5F5", "#CE93D8"),
    ("#E0F7FA", "#80DEEA"),
]

FAQ_COLORS = [
    ("#E3F2FD", "#64B5F6"),
    ("#E1F5FE", "#4FC3F7"),
    ("#E8EAF6", "#7986CB"),
]


def get_it_keywords() -> list[str]:
    """카테고리별 1개씩 3개 키워드를 반환한다."""
    day = datetime.now().day

    CATEGORY_POOLS = {
        "가젯/악세서리": [
            "무선 이어폰 추천 순위", "기계식 키보드 추천", "게이밍 마우스 비교",
            "USB-C 충전기 추천", "보조배터리 추천", "블루투스 스피커 비교",
            "노이즈캔슬링 이어폰 비교", "게이밍 헤드셋 추천", "웹캠 추천 순위",
            "무선 충전 패드 비교", "스마트워치 추천 순위", "액션캠 추천",
        ],
        "노트북/PC/모니터": [
            "2026 가성비 노트북 추천", "4K 모니터 추천", "게이밍 노트북 비교",
            "사무용 노트북 추천", "맥북 vs 윈도우 노트북 비교", "듀얼 모니터 세팅법",
            "SSD 추천 순위", "RAM 업그레이드 가이드", "그래픽카드 비교",
            "조립PC 견적 가이드", "미니PC 추천", "외장하드 vs 외장SSD 비교",
        ],
        "IT꿀팁/앱": [
            "윈도우 11 숨은 기능", "맥북 필수 앱 추천", "크롬 확장 프로그램 추천",
            "스마트폰 저장 공간 확보법", "와이파이 속도 높이는 법", "노트북 발열 해결법",
            "배터리 수명 늘리는 법", "무료 PDF 편집 프로그램", "화면 녹화 프로그램 추천",
            "VPN 추천 비교", "클라우드 스토리지 비교", "AI 생산성 도구 추천",
        ],
    }

    categories = list(CATEGORY_POOLS.keys())
    keywords = []
    for i, cat in enumerate(categories):
        pool = CATEGORY_POOLS[cat]
        idx = (day + i * 7) % len(pool)
        kw = pool[idx]
        keywords.append(kw)

    return keywords


def generate_content(keyword: str, products: list) -> dict | None:
    """OpenAI API로 IT 블로그 콘텐츠를 생성한다."""
    import openai

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    product_names = ", ".join(p.get("productName", "")[:30] for p in products[:3]) if products else "관련 상품 없음"

    prompt = BLOG_STYLE_PROMPT.format(keyword=keyword, products=product_names)

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.7,
            )
            text = resp.choices[0].message.content.strip()
            text = re.sub(r"```json\s*", "", text)
            text = re.sub(r"```\s*$", "", text)
            text = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', "", text)
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 에러 (시도 %d/3)", attempt + 1)
            time.sleep(2)
        except Exception as e:
            logger.error("API 에러: %s", e)
            time.sleep(3)
    return None


def search_coupang_products(keyword: str) -> list:
    """쿠팡에서 IT 제품을 검색한다."""
    config = CoupangConfig()
    client = CoupangAPIClient(config)

    short_kw = keyword.split()[0] if len(keyword) > 10 else keyword
    results = client.search_products(short_kw)

    if not results:
        IT_CACHE = {
            "이어폰": [
                {"productName": "삼성 갤럭시 버즈3 프로", "productPrice": 259000,
                 "productUrl": "https://link.coupang.com/re/AFFSDP?lptag=AF5939135&subid=blog",
                 "productImage": ""},
            ],
            "키보드": [
                {"productName": "로지텍 MX Keys S 무선 키보드", "productPrice": 139000,
                 "productUrl": "https://link.coupang.com/re/AFFSDP?lptag=AF5939135&subid=blog",
                 "productImage": ""},
            ],
            "노트북": [
                {"productName": "LG 그램 17인치 2026", "productPrice": 1890000,
                 "productUrl": "https://link.coupang.com/re/AFFSDP?lptag=AF5939135&subid=blog",
                 "productImage": ""},
            ],
        }
        for cache_kw, prods in IT_CACHE.items():
            if cache_kw in keyword:
                return prods
        return list(IT_CACHE.values())[hash(keyword) % len(IT_CACHE)]

    seen = set()
    unique = []
    for p in results:
        name = p.get("productName", "")
        if name not in seen:
            seen.add(name)
            unique.append(p)
    return unique[:3]


def build_full_html(data: dict, keyword: str, products: list, post_date: str) -> str:
    """완성된 HTML 페이지를 조립한다."""
    title = data.get("title", keyword)
    meta_desc = data.get("meta_description", "")
    sections = data.get("sections", [])
    summary_cards = data.get("summary_cards", [])
    faq = data.get("faq", [])
    tags = data.get("tags", [])

    # 헤더 이미지
    header_img = SECTION_IMAGES[hash(keyword) % len(SECTION_IMAGES)]

    # 섹션 HTML
    sections_html = ""
    for i, sec in enumerate(sections):
        heading = sec.get("heading", "")
        content = sec.get("content", "")
        img = SECTION_IMAGES[i % len(SECTION_IMAGES)]
        sections_html += f"""
<h2 style="font-size: 22px; color: #1565C0; border-bottom: 3px solid #42A5F5; padding-bottom: 10px; margin: 40px 0 20px;">{heading}</h2>
<div style="text-align: center; margin: 15px 0;">
<img src="{img}" alt="{heading}" style="max-width: 100%; height: auto; border-radius: 8px;" loading="lazy" />
</div>
{content}
"""

    # 요약 카드
    cards_html = '<div style="display: flex; flex-wrap: wrap; gap: 12px; margin: 30px 0;">'
    for i, card in enumerate(summary_cards[:5]):
        bg, border = SUMMARY_COLORS[i % len(SUMMARY_COLORS)]
        cards_html += f'<div style="flex: 1; min-width: 150px; padding: 15px; background: {bg}; border-radius: 10px; border-left: 4px solid {border};"><p style="margin: 0; font-size: 14px; color: #333;">{card}</p></div>'
    cards_html += "</div>"

    # FAQ
    faq_html = ""
    if faq:
        faq_html = '<h2 style="font-size: 22px; color: #1565C0; border-bottom: 3px solid #42A5F5; padding-bottom: 10px; margin: 40px 0 20px;">자주 묻는 질문</h2>'
        for i, f in enumerate(faq[:3]):
            bg, border = FAQ_COLORS[i % len(FAQ_COLORS)]
            faq_html += f"""
<div style="margin: 15px 0; padding: 18px; background: {bg}; border-radius: 10px; border-left: 4px solid {border};">
<p style="font-weight: bold; color: #1565C0; margin: 0 0 8px;">Q. {f.get('q','')}</p>
<p style="color: #333; margin: 0; line-height: 1.8;">A. {f.get('a','')}</p>
</div>"""

    # 쿠팡 상품
    coupang_html = ""
    if products:
        coupang_html = '<h2 style="color: #1565C0; border-bottom: 2px solid #E3F2FD; padding-bottom: 10px;">테크온도 추천 제품</h2>\n'
        coupang_html += '<p style="color: #666; font-size: 14px; margin-bottom: 20px;">이 글의 주제와 관련된 제품을 선별했습니다.</p>\n'
        for p in products[:3]:
            name = p.get("productName", "")
            price = int(p.get("productPrice", 0))
            url = p.get("productUrl", "#")
            img = p.get("productImage", "")
            img_tag = f'<img src="{img}" alt="{name[:20]}" style="width: 130px; height: 130px; object-fit: contain; border-radius: 6px; background: #fff; border: 1px solid #eee;" loading="lazy" />' if img else ""
            coupang_html += f"""<div style="margin-bottom: 20px; padding: 18px; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa;">
<a href="{url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: #333;">
<div style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap;">
{img_tag}
<div style="flex: 1; min-width: 200px;">
<p style="font-size: 17px; font-weight: bold; color: #1565C0; margin: 0 0 8px 0;">{name}</p>
<p style="font-size: 20px; font-weight: bold; color: #e44d26; margin: 0 0 6px 0;">{price:,}원</p>
<span style="display: inline-block; padding: 8px 24px; background: #1565C0; color: white; border-radius: 4px; font-size: 14px; font-weight: bold;">최저가 확인하기</span>
</div></div></a></div>\n"""
        coupang_html += '<p style="color: #999; font-size: 12px; margin-top: 15px;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>'

    # 태그
    tags_html = ""
    if tags:
        tags_html = '<div style="margin: 30px 0;">'
        for t in tags:
            tags_html += f'<span style="display: inline-block; padding: 6px 14px; margin: 4px; background: #E3F2FD; border-radius: 20px; font-size: 13px; color: #1565C0;">#{t}</span>'
        tags_html += "</div>"

    # JSON-LD
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "author": {"@type": "Person", "name": "테크온도"},
        "publisher": {"@type": "Organization", "name": "테크온도(IT++)"},
        "datePublished": post_date,
        "description": meta_desc,
    }, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{meta_desc}">
<meta name="keywords" content="{', '.join(tags)}">
<title>{title} :: 테크온도</title>
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{meta_desc}" />
<meta property="og:type" content="article" />
<script type="application/ld+json">{schema}</script>
</head>
<body>
<article style="max-width: 800px; margin: 0 auto; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.8; color: #333;">

<div style="text-align: center; margin-bottom: 30px;">
<img src="{header_img}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 12px;" loading="lazy" />
</div>

{cards_html}
{sections_html}
{faq_html}
{coupang_html}
{tags_html}

</article>
</body>
</html>"""


def main():
    """메인 실행."""
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(f"output/it-posts/{today}")
    output_dir.mkdir(parents=True, exist_ok=True)

    keywords = get_it_keywords()
    logger.info("오늘 IT 키워드: %s", keywords)

    results = []
    for i, keyword in enumerate(keywords, 1):
        logger.info("[%d/3] 키워드: %s", i, keyword)

        # 중복 체크
        if check_title_duplicate(keyword):
            logger.warning("중복 키워드 스킵: %s", keyword)
            continue

        # 쿠팡 상품
        products = search_coupang_products(keyword)
        logger.info("쿠팡 상품: %d개", len(products))

        # 콘텐츠 생성
        data = generate_content(keyword, products)
        if not data:
            logger.error("콘텐츠 생성 실패: %s", keyword)
            continue

        title = data.get("title", keyword)

        # HTML 생성
        html = build_full_html(data, keyword, products, today)
        safe_name = re.sub(r"[^\w가-힣]", "_", keyword)[:30]
        filepath = output_dir / f"post_{i}_{safe_name}.html"
        filepath.write_text(html, encoding="utf-8")
        logger.info("저장: %s (%d자)", filepath.name, len(html))

        register_published(title, keyword)
        results.append({"keyword": keyword, "title": title, "tags": data.get("tags", []), "file": str(filepath)})
        time.sleep(2)

    # summary 저장
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("IT 포스트 %d개 생성 완료", len(results))

    # 텔레그램 알림
    try:
        from src.notify.telegram import send_message
        if results:
            lines = [f"🖥️ IT 블로그 포스트 {len(results)}개 생성!\n"]
            for r in results:
                lines.append(f"• {r['title']}")
            lines.append("\n✅ GitHub 푸시 완료. uyoblog 발행해 주세요.")
            send_message("\n".join(lines))
        else:
            send_message("⚠️ IT 블로그 포스트 생성 실패!")
    except Exception as e:
        logger.warning("텔레그램 알림 실패: %s", e)

    return results


if __name__ == "__main__":
    main()
