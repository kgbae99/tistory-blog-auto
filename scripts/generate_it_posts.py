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
- 제목: 클릭을 부르는 호기심 유발형 (15~30자). 아래 패턴 중 하나를 반드시 사용:
  * 궁금증형: "이 가격에 이 성능?", "뭐가 다를까?", "뭘 사야 후회 안 할까?"
  * 경험형: "직접 써보고 고른", "3개 비교해봤더니"
  * 문제해결형: "느려졌다면?", "고민된다면 이것만 보세요"
  * 반전형: "싼 게 비지떡? 아닌 경우도 있다", "비싼 게 다 좋은 건 아닙니다"
  * 절대 "완벽 가이드", "총정리", "TOP5" 같은 밋밋한 제목 금지
  * 절대 연도(2024, 2025, 2026) 넣지 않기
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
- 연도: 제목이나 본문에 연도를 넣지 마세요 (불필요)
- 쿠팡 추천 상품 (본문에서 자연스럽게 언급): {products}

## 출력: 반드시 JSON만
{{"title":"제목","meta_description":"155자이내 SEO 설명","sections":[{{"heading":"H2제목","content":"HTML본문(300자이상)"}}],"summary_cards":["요약1","요약2","요약3","요약4","요약5"],"faq":[{{"q":"질문","a":"답변"}}],"tags":["태그1","태그2"]}}"""

# IT 이미지 (Unsplash)
_IMAGES_DEVICES = [
    "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1468495244123-6c6c332eeece?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1484788984921-03950022c38b?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1593642634315-48f5414c3ad9?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1547394765-185e1e68f34e?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1587614382346-4ec70e388b28?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1555680202-c86f0e12f086?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1563206767-5b18f218e8de?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1504707748692-419802cf939d?w=486&h=315&fit=crop",
]

_IMAGES_MOBILE = [
    "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1512499617640-c74ae3a79d37?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1546054454-aa26e2b734c7?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1604754742629-3e5728249d73?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1585386959984-a4155224a1ad?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1523206489230-c012c64b2b48?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1509395062183-a6ef2f5b0e23?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1608042314453-ae338d80c427?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1583394293253-4a19f579b3f3?w=486&h=315&fit=crop",
]

_IMAGES_SOFTWARE = [
    "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1484417894907-623942c8ee29?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1533750349088-cd871a92f312?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1509966756634-9c23dd6e6815?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1619410283995-43d9134e7656?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1624953587687-daf255b6b80a?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1593642634367-d91a135587b5?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1602576666092-bf6447a729fc?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1607706189992-eae578626c86?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1542744095-291d1f67b221?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1537432376769-00f5c2f4c8d2?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=486&h=315&fit=crop",
]

_IMAGES_AI = [
    "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1676277791608-ac54525aa94d?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1639322537228-f710d846310a?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1593376893114-1aed528d80cf?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1568952433726-3896e3881c65?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1507146153580-69a1fe6d8aa1?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1673187434899-5b77b8f91d8f?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1666597107756-ef489e9f1f09?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1655720828018-edd2daec9349?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1676274158576-8cc0db049a7f?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1680016861993-901f34a3d9e2?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1664575602554-2087b04935a5?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1675557009875-436f7a7da264?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1657639200000-e8a69b938f5d?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1702149996318-72c5a3c7e5fb?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1686191128892-3b37add4c844?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1694577511043-f9f9a52b6b2c?w=486&h=315&fit=crop",
]

SECTION_IMAGES = _IMAGES_DEVICES + _IMAGES_MOBILE + _IMAGES_SOFTWARE + _IMAGES_AI


def _load_used_images() -> set[str]:
    """최근 사용된 이미지 URL 집합을 반환한다."""
    path = Path(__file__).parent.parent / "data" / "used_images.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {item["url"] for item in data if "url" in item}
        return set()
    except Exception:
        return set()


def _save_used_image(url: str, keyword: str) -> None:
    """사용된 이미지를 기록한다. 90일 이상 된 항목은 삭제."""
    from datetime import date, timedelta
    path = Path(__file__).parent.parent / "data" / "used_images.json"
    data = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    data = [item for item in data if item.get("date", "") >= cutoff]
    data.append({"url": url, "date": date.today().isoformat(), "keyword": keyword})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _pick_image(keyword: str, index: int) -> str:
    """최근 사용 이미지를 제외하고 이미지를 선택한다."""
    import hashlib
    from datetime import date
    used = _load_used_images()
    unused = [img for img in SECTION_IMAGES if img not in used]
    candidates = unused if unused else SECTION_IMAGES
    seed = f"{date.today().isoformat()}-{keyword}-{index}"
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(candidates)
    selected = candidates[idx]
    _save_used_image(selected, keyword)
    return selected

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
            text = re.sub(r"```", "", text)
            text = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', "", text)
            # JSON 블록 추출
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                text = match.group(0)
            # 제어 문자 제거
            text = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
            text = text.replace('\n', ' ').replace('\r', ' ')
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # HTML 내 이스케이프 안 된 따옴표 수정
                text = re.sub(r'style="([^"]*)"', lambda m: 'style=\'' + m.group(1) + '\'', text)
                # content 필드에서 HTML 추출 후 재조립
                sections = []
                for sm in re.finditer(r'"heading"\s*:\s*"([^"]*)"[^}]*"content"\s*:\s*"((?:[^"\\]|\\.)*)?"', text):
                    sections.append({"heading": sm.group(1), "content": sm.group(2).replace('\\"', '"') if sm.group(2) else ""})
                title_m = re.search(r'"title"\s*:\s*"([^"]*)"', text)
                meta_m = re.search(r'"meta_description"\s*:\s*"([^"]*)"', text)
                tags_m = re.findall(r'"tags"\s*:\s*\[(.*?)\]', text)
                faq_list = []
                for fm in re.finditer(r'"q"\s*:\s*"([^"]*)"[^}]*"a"\s*:\s*"([^"]*)"', text):
                    faq_list.append({"q": fm.group(1), "a": fm.group(2)})
                cards_m = re.search(r'"summary_cards"\s*:\s*\[(.*?)\]', text)

                if title_m and sections:
                    tags = [t.strip().strip('"') for t in tags_m[0].split(',')] if tags_m else []
                    cards = [c.strip().strip('"') for c in cards_m.group(1).split(',')] if cards_m else []
                    logger.info("JSON 수동 파싱 성공 (섹션 %d개)", len(sections))
                    return {
                        "title": title_m.group(1),
                        "meta_description": meta_m.group(1) if meta_m else "",
                        "sections": sections,
                        "summary_cards": cards[:5],
                        "faq": faq_list[:3],
                        "tags": tags[:7],
                    }
                raise json.JSONDecodeError("수동 파싱도 실패", text[:100], 0)
        except json.JSONDecodeError as e:
            logger.warning("JSON 파싱 에러 (시도 %d/3): %s", attempt + 1, str(e)[:50])
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


def build_full_html(data: dict, keyword: str, products: list, post_date: str, post_index: int = 0) -> str:
    """완성된 HTML 페이지를 조립한다."""
    title = data.get("title", keyword)
    meta_desc = data.get("meta_description", "")
    sections = data.get("sections", [])
    summary_cards = data.get("summary_cards", [])
    faq = data.get("faq", [])
    tags = data.get("tags", [])

    # GitHub 호스팅 이미지 사용 (136개 풀)
    from src.content.image_search import get_images_for_keyword as _get_imgs
    all_images = _get_imgs(keyword, count=8, post_index=post_index)
    header_img = all_images[0] if all_images else _pick_image(keyword, 0)
    section_img_pool = all_images[1:] if len(all_images) > 1 else all_images

    # 섹션 HTML
    sections_html = ""
    for i, sec in enumerate(sections):
        heading = sec.get("heading", "")
        content = sec.get("content", "")
        img = section_img_pool[i % len(section_img_pool)] if section_img_pool else _pick_image(keyword, i + 1)
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

    # 쿠팡 배너
    coupang_banner = '<div style="text-align: center; margin: 20px 0 30px 0;"><a href="https://link.coupang.com/a/d4YwkD" target="_blank" rel="noopener"><img style="max-width: 100%; height: auto;" src="https://ads-partners.coupang.com/banners/882911?subId=&amp;traceId=V0-301-879dd1202e5c73b2-I882911&amp;w=728&amp;h=90" alt="" /></a></div>'

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
{coupang_banner}
{tags_html}

</article>
</body>
</html>"""


def build_tool_page(title: str, tags: list, blog_html: str, meta_desc: str = "") -> str:
    """IT 블로그용 복사 도구 페이지 HTML을 생성한다."""
    tag_str = ", ".join(tags)
    meta_tag = f'<meta name="description" content="{meta_desc}">' if meta_desc else ""
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
{meta_tag}
<title>{title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:'Malgun Gothic',sans-serif;background:#f0f2f5;color:#333}}
.tool-panel{{position:sticky;top:0;z-index:1000;background:#1a237e;color:#fff;padding:20px 30px;box-shadow:0 4px 12px rgba(0,0,0,0.3)}}
.tool-panel h2{{font-size:18px;margin-bottom:15px;color:#90CAF9}}
.field-row{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
.field-label{{min-width:70px;font-weight:bold;font-size:13px;color:#BBDEFB}}
.field-value{{flex:1;background:#283593;color:#fff;padding:10px 14px;border-radius:6px;font-size:14px;border:1px solid #3949AB;user-select:all}}
.copy-btn{{padding:8px 16px;border:none;border-radius:6px;font-size:13px;font-weight:bold;cursor:pointer;transition:all 0.2s}}
.btn-small{{background:#90CAF9;color:#1a237e}}.btn-small:hover{{background:#64B5F6}}
.btn-html{{background:linear-gradient(135deg,#1565C0,#42A5F5);color:#fff;padding:12px 30px;font-size:15px}}
.btn-row{{display:flex;gap:10px;align-items:center;margin-top:5px}}
.copy-toast{{display:none;background:#27ae60;color:#fff;padding:6px 14px;border-radius:4px;font-size:13px}}
.copy-toast.show{{display:inline-block}}
.preview-area{{max-width:760px;margin:30px auto;padding:0 20px}}
.preview-label{{text-align:center;color:#999;font-size:13px;margin-bottom:15px;padding:8px;border:1px dashed #ccc;border-radius:6px}}
</style></head><body>
<div class="tool-panel">
<h2>🖥️ 테크온도 발행 도구</h2>
<div class="field-row"><span class="field-label">제목</span><div class="field-value" id="t">{title}</div><button class="copy-btn btn-small" onclick="c('t',this)">복사</button></div>
<div class="field-row"><span class="field-label">카테고리</span><div class="field-value" id="cat">IT / 가젯</div><button class="copy-btn btn-small" onclick="c('cat',this)">복사</button></div>
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
        html = build_full_html(data, keyword, products, today, post_index=i)
        safe_name = re.sub(r"[^\w가-힣]", "_", keyword)[:30]

        # 발행 도구 페이지만 생성 (post 파일은 불필요)
        blog_body = re.search(r"<article[^>]*>(.*?)</article>", html, re.DOTALL)
        blog_html_content = blog_body.group(1) if blog_body else html
        tags = data.get("tags", [])
        if not tags:
            # 태그가 비어있으면 키워드에서 자동 생성
            tags = [w.strip() for w in keyword.split() if len(w.strip()) >= 2]
            tags.extend(["IT추천", "테크온도", "가성비"])
            logger.info("태그 자동 생성: %s", tags)
        tool_html = build_tool_page(title, tags, blog_html_content, data.get("meta_description", ""))
        tool_path = output_dir / f"tool_{i}_{safe_name}.html"
        tool_path.write_text(tool_html, encoding="utf-8")
        logger.info("저장: %s (%d자)", tool_path.name, len(tool_html))

        register_published(title, keyword)
        results.append({"keyword": keyword, "title": title, "tags": data.get("tags", []), "file": str(tool_path)})
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
