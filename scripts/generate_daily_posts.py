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
from src.coupang.product_search import search_and_filter

logger = setup_logger("daily_posts")

# 블로그 스타일 프롬프트 템플릿
BLOG_STYLE_PROMPT = """당신은 "건강온도사(행복++)" 티스토리 블로그의 전문 콘텐츠 작가입니다.

## 기존 글 스타일 (반드시 따르세요)
- 제목: 짧고 강렬한 호기심 유발형 (15~30자)
- H2 섹션 6~7개, H3 사용 안 함
- 각 섹션 150~300자, 짧은 문단 2~3문장
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

## 테이블 HTML 형식
<div class="table-section" style="margin: 20px 0;">
<table style="width: 100%; border-collapse: collapse;">
<thead><tr>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">항목1</th>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">항목2</th>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">항목3</th>
</tr></thead>
<tbody>
<tr><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">내용</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">내용</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">내용</td></tr>
</tbody></table></div>

## 섹션 내용 형식
<div class="topic-content" style="background-color: #fff5f6; padding: 20px; border-radius: 8px; border-left: 4px solid #FFB6C1;">
<p style="color: #333; line-height: 1.8;">내용</p>
</div>

## 이번 글 요청
- 키워드: "{keyword}"
- 카테고리: 건강 & 웰빙
- 쿠팡 추천 상품 (본문에서 자연스럽게 언급): {products}

## 출력: 반드시 JSON만
{{"title":"제목","meta_description":"155자이내","sections":[{{"heading":"H2제목","content":"HTML본문"}}],"summary_cards":["요약1","요약2","요약3","요약4","요약5"],"faq":[{{"q":"질문","a":"답변"}}],"tags":["태그1","태그2"]}}"""

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
        ],
        "음식/영양": [
            "아침 공복에 좋은 음식", "피로 회복에 좋은 음식", "봄나물 효능과 종류",
            "다이어트에 좋은 음식", "면역력 높이는 음식 BEST", "혈관에 좋은 음식",
            "항산화 식품 추천", "단백질 풍부한 식단", "비타민 많은 과일",
            "장 건강에 좋은 발효식품", "해독에 좋은 차", "콜레스테롤 낮추는 음식",
            "눈에 좋은 영양소", "뼈에 좋은 음식", "간에 좋은 음식",
        ],
        "뷰티/생활": [
            "봄 스킨케어 루틴", "자외선 차단제 추천", "보습 크림 고르는 법",
            "봄철 다이어트 식단", "홈트레이닝 추천 운동", "환절기 피부 관리",
            "꽃가루 알레르기 예방법", "미세먼지 건강관리", "춘곤증 극복 방법",
            "체력 키우는 방법", "스트레칭 효과", "물 많이 마시면 좋은 점",
            "아침 루틴 만드는 법", "숙면 취하는 방법", "노화 방지 습관",
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


def search_coupang_products(keyword: str) -> list:
    """쿠팡에서 키워드 관련 상품을 검색한다."""
    try:
        config = load_config()
        client = CoupangAPIClient(config.coupang)
        products = search_and_filter(client, keyword, count=3)
        return products
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

    # 상단 고지문
    parts.append("""<div style="background-color: #fff5f6; border: 1px solid #FFB6C1; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px;">
<p style="color: #555; font-size: 14px; line-height: 1.7; margin: 0;">📌 <strong>이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</strong><br />본 글은 건강 정보를 요약한 것이며, 특정 제품의 효능을 보장하지 않습니다. 건강 관련 결정은 반드시 전문의와 상담하세요.</p>
</div>""")

    # 대표 이미지
    parts.append(f'<figure style="text-align: center; margin: 0 0 20px 0;"><img src="{header_img}" alt="" style="max-width:100%; height:auto; border-radius:8px;" width="486" /></figure>')
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
<figure style="text-align: center; margin: 15px 0;"><img src="{img}" alt="" style="max-width:100%; height:auto; border-radius:8px;" width="486" /></figure>
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
<p style="color: #888; font-size: 13px; margin-top: 15px; text-align: center;">📌 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
</div>""")

    # 태그
    tag_str = ", ".join(tags)
    parts.append(f'<div style="margin-bottom: 30px;"><p>{tag_str}</p></div>')

    result = "\n\n".join(parts)

    # 후처리
    result = re.sub(r'alt="[^"]*"', 'alt=""', result)  # img alt 제거
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


def build_tool_page(title: str, tags: list, blog_html: str) -> str:
    """복사 도구 페이지 HTML을 생성한다."""
    tag_str = ", ".join(tags)
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
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
