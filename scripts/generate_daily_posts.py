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

# ── 핵심 목표 (모든 글에 공통 적용) ─────────────────────────────
_CORE_GOALS = """
## 핵심 지시 (정보글이 아니라 돈 되는 글을 만들어라)
너는 구글 SEO와 애드센스 수익 구조를 이해하는 블로그 전문가다.
검색 유입 → 체류 → 클릭 → 수익까지 이어지는 글을 작성한다.

### 규칙 1: 키워드
- 반드시 롱테일 키워드 사용 (이유/방법/추천/후기 포함)
- 검색 의도가 명확한 키워드만 사용
- 제목에 숫자+결과 1개 이상 포함

### 규칙 2: 글 구조
- 문제 → 공감 → 해결 → 사례/경험 → 행동 순서 필수
- 첫 문단에 실패 경험 포함 (독자 공감 유도)
- 실제 경험처럼 자연스럽게 작성
- 수치 포함 (기간, 변화량 등)

### 규칙 3: 수익 구조 (광고 위치)
- 광고는 3곳에 고정:
  1. 문제 인식 직후
  2. 해결 방법 직후
  3. 결론 직전
- 각 광고 바로 위에 "지금 이게 필요하다"는 감정 연결 문장 삽입

### 규칙 4: CTA
- 중간 CTA 1개 이상: "이 방법이 어렵다면 아래 방법이 더 현실적입니다" 포함
- 마지막 CTA 1개 필수: 다음 관련 글로 연결

### 규칙 5: 제품 추천 순서
- 제품은 바로 추천하지 말고 문제→해결→경험→결과 이후에만 배치
- 제품 블록 바로 위 브릿지 문장 필수 (ex: "음식만으로는 한계가 있었어요. 그래서 이걸 함께 쓰기 시작했어요.")
- 선택 구조: 이런 사람 → A / 저런 사람 → B
- 가격 순서: 저가 → 중가 → 고가

### 규칙 6: 이미지
- 이미지 최대 3개
- 같은 이미지 반복 금지
- alt 텍스트 모두 다르게 작성

### 규칙 7: 금지
- 백과사전식 설명 금지
- 의미 없는 표 반복 금지
- "규칙적인 운동", "충분한 수면" 같은 어디서나 볼 수 있는 일반 정보 금지
- 박스(강조 div) 연속 2개 이상 금지 (사이에 텍스트 문단 1개 이상)
"""

# ── 공통 HTML 형식 ──────────────────────────────────────────────
_TABLE_HTML = """<div class="table-section" style="margin: 20px 0;">
<table style="width: 100%; border-collapse: collapse;">
<thead><tr>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">구분</th>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">핵심 내용</th>
<th style="padding: 12px; border: 1px solid #FFB6C1; background-color: #ffe4e8; color: #2c3e50;">추천/효과</th>
</tr></thead>
<tbody>
<tr><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">항목A</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">설명</td><td style="padding: 12px; border: 1px solid #FFB6C1; color: #333;">효과</td></tr>
</tbody></table></div>"""

_SECTION_HTML = """<div class="topic-content" style="background-color: #fff5f6; padding: 20px; border-radius: 8px; border-left: 4px solid #FFB6C1;">
<p style="color: #333; line-height: 1.8;">내용</p>
</div>"""

_COMMON_RULES = """
## 공통 글쓰기 규칙
- 제목: 롱테일 키워드 형식 (20~35자), [타겟+숫자/결과+주제+방법/이유/후기/추천/비교] 구조
  * 숫자·결과·경험 중 1개 이상 필수: "3개월 5kg 감량 성공 방법", "2주 만에 무릎 통증 줄인 후기"
  * ❌ 연도, "총정리", "완벽 가이드" 금지
- 전체 흐름: 문제 제기 → 공감 → 해결책 → 사례/경험 → 행동 촉구
- 도입부 첫 3줄 안에 문제 제기 필수
- 개인 경험 섹션 필수 (5번째 H2): 실패 → 개선 → 수치 결과 (기간+수치+변화 3요소)
- 전체 최소 3,000자 이상, 각 섹션 300~500자
- 표: 글 전체 최대 1~2개만 (꼭 필요한 비교/수치에만)
- 리스트: 3개 이상 연속이면 문단으로 풀어쓸 것
- ❌ 금지: 반복 요약, "앞서 언급했듯이", "이상으로 알아봤습니다", 의미 없는 문장
- ❌ 금지: "규칙적인 운동", "충분한 수면", "스트레스 관리" 같이 어디서나 볼 수 있는 뻔한 내용
- ✅ 필수: 차별화된 관점 1개 이상 포함 (반직관적 사실 / 간과된 디테일 / 실패 경험 / 수치 근거 / 비교 관점)
- H2 섹션 6~7개, H3 사용 안 함, 목차(TOC) 생성 금지
- 태그 6~7개
- 각 섹션 내용은 topic-content div로 감쌈
- 내부링크 2개 본문 중간에 자연스럽게 삽입: {internal_links}
- 이미지: 최대 3개, alt 텍스트 모두 다르게 (중복 금지), "[키워드] [구체적 상황]" 형식
- 박스(강조 div) 연속 2개 이상 금지 — 박스 사이에 텍스트 문단 1개 이상 삽입
- 각 섹션 첫 100자는 순수 텍스트로 시작 (박스·리스트·표 금지)

## 섹션 내용 형식
""" + _SECTION_HTML + """

## 테이블 형식 (최대 1~2개, 헤더에 "항목1/2/3" 절대 금지, 실제 항목명 사용)
""" + _TABLE_HTML

# ── 수익형 프롬프트 (상품 추천 + CTA 포함) ──────────────────────
REVENUE_PROMPT = """당신은 "건강온도사(행복++)" 티스토리 블로그의 전문 콘텐츠 작가입니다.
""" + _CORE_GOALS + """
## 글 유형: 수익형 (상품 추천 + CTA 중심)
- 목적: 독자의 문제를 해결하면서 관련 상품 구매를 자연스럽게 유도
- 쿠팡 추천 상품을 해결책 맥락에서 자연스럽게 언급 (억지 끼워넣기 금지)
- 제품 배치 순서 (필수): 문제 제기 → 공감 → 해결책 설명 → 개인 경험/결과 → **이 시점에만** 제품 블록
- 제품 블록 바로 위 브릿지 문장 필수: "음식만으로는 한계가 있었어요. 그래서 저는 이걸 함께 쓰기 시작했어요." 형식
- 제품 가격 순서: 저가 → 중가 → 고가 (부담감 최소화)
- 제품 블록 앞에 선택 구조 카드 삽입: "이런 분 → A 제품 / 저런 분 → B 제품" 2열 카드
- CTA 필수:
  * 중간 CTA (해결책 섹션 끝): "이 방법이 어렵다면?" + 내부 링크 버튼
    <div style="background:linear-gradient(135deg,#fff5f6,#ffe4e8);border-radius:10px;padding:20px;margin:25px 0;border-left:4px solid #FFB6C1;text-align:center;"><p style="font-size:15px;color:#555;margin:0 0 8px 0;">이 방법이 어렵다면?</p><p style="font-size:17px;font-weight:bold;color:#2c3e50;margin:0 0 15px 0;">[대안 설명]</p><a href="[내부링크]" style="display:inline-block;padding:12px 30px;background:#e44d26;color:white;border-radius:6px;text-decoration:none;font-weight:bold;">바로 확인하기 →</a></div>
  * 최종 CTA (마무리 끝): 다음 관련 글 연결
    <div style="background:linear-gradient(135deg,#fff5f6,#ffe4e8);border-radius:10px;padding:25px;margin:30px 0;text-align:center;border:2px solid #FFB6C1;"><p style="font-size:18px;font-weight:bold;color:#2c3e50;margin:0 0 10px 0;">📌 다음으로 읽으면 좋은 글</p><a href="[내부링크]" style="display:block;padding:15px;background:#fff;border-radius:8px;text-decoration:none;color:#2c3e50;font-weight:bold;border:1px solid #FFB6C1;margin-top:12px;">👉 [관련 글 제목]</a></div>

## 이번 글 요청
- 키워드: "{keyword}"
- 카테고리: 건강 & 웰빙
- 쿠팡 추천 상품 (본문에서 자연스럽게 언급): {products}
""" + _COMMON_RULES + """

## 출력: 반드시 JSON만
{{"title":"제목(20~35자, 숫자+결과+방법/이유/후기/추천/비교)","meta_description":"155자이내","sections":[{{"heading":"H2제목","content":"HTML본문(300자이상)"}}],"summary_cards":["요약1","요약2","요약3","요약4","요약5"],"faq":[{{"q":"질문","a":"답변"}}],"tags":["태그1","태그2"]}}"""

# ── 정보형 프롬프트 (순수 정보, 상품 언급 없음) ──────────────────
INFO_PROMPT = """당신은 "건강온도사(행복++)" 티스토리 블로그의 전문 콘텐츠 작가입니다.
""" + _CORE_GOALS + """
## 글 유형: 정보형 (순수 정보 제공, 상품 추천 없음)
- 목적: 독자에게 정확하고 깊이 있는 건강 정보를 제공하여 신뢰 구축 및 SEO 트래픽 확보
- ❌ 절대 금지: 상품 추천, 쿠팡 링크 언급, "이 제품이 좋아요" 같은 상업적 표현
- ❌ 절대 금지: "~을 구매하세요", "최저가 확인", 상품 관련 CTA
- 중간 CTA (정보형): 관련 심층 정보 글로 연결
  * "이 내용이 더 궁금하다면?" + 내부 링크
    <div style="background:linear-gradient(135deg,#fff5f6,#ffe4e8);border-radius:10px;padding:20px;margin:25px 0;border-left:4px solid #FFB6C1;text-align:center;"><p style="font-size:15px;color:#555;margin:0 0 8px 0;">이 내용이 더 궁금하다면?</p><a href="[내부링크]" style="display:inline-block;padding:12px 30px;background:#e44d26;color:white;border-radius:6px;text-decoration:none;font-weight:bold;">관련 글 보러가기 →</a></div>
- 최종 CTA (필수): 다음 관련 정보 글 연결
  * "📌 함께 읽으면 좋은 글" 카드
    <div style="background:linear-gradient(135deg,#fff5f6,#ffe4e8);border-radius:10px;padding:25px;margin:30px 0;text-align:center;border:2px solid #FFB6C1;"><p style="font-size:18px;font-weight:bold;color:#2c3e50;margin:0 0 10px 0;">📌 함께 읽으면 좋은 글</p><a href="[내부링크]" style="display:block;padding:15px;background:#fff;border-radius:8px;text-decoration:none;color:#2c3e50;font-weight:bold;border:1px solid #FFB6C1;margin-top:12px;">👉 [관련 글 제목]</a></div>

## 이번 글 요청
- 키워드: "{keyword}"
- 카테고리: 건강 & 웰빙
""" + _COMMON_RULES.replace("- 쿠팡 추천 상품 언급 시 본문 맥락과 자연스럽게 연결\n", "") + """

## 출력: 반드시 JSON만
{{"title":"제목(20~35자, 숫자+결과+방법/이유/후기/추천/비교)","meta_description":"155자이내","sections":[{{"heading":"H2제목","content":"HTML본문(300자이상)"}}],"summary_cards":["요약1","요약2","요약3","요약4","요약5"],"faq":[{{"q":"질문","a":"답변"}}],"tags":["태그1","태그2"]}}"""

# 하위 호환 유지
BLOG_STYLE_PROMPT = REVENUE_PROMPT

# 이미지 풀 (Unsplash 검증된 URL — 카테고리별 다양화)
_IMAGES_HEALTH = [
    "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1530497610245-94d3c16cda28?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1544991875-5dc1b05f1571?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1593811167562-9cef47bfc4d7?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1581595220892-b0739db3ba8c?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1588776814546-1ffbb7d36308?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1559757175-5700dde675bc?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1511688878353-3a2f5be94cd7?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=486&h=315&fit=crop",
]

_IMAGES_FOOD = [
    "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1543339308-43e59d6b73a6?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1547592180-85f173990554?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1467453678174-768ec283a940?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1488459716781-31db52582fe9?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1490818387583-1baba5e638af?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=486&h=315&fit=crop",
]

_IMAGES_BEAUTY = [
    "https://images.unsplash.com/photo-1522748906645-95d8adfd52c7?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1596755389378-c31d21fd1273?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1583241475880-083f84372725?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1601925228008-8c1bcdcf2b6e?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1570194065650-d99fb4bedf0a?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1522338242992-e1a54906a8da?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1523263685509-57c1d050d19b?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1607748862156-7c548e7e98f4?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1552693673-1bf958298935?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1614159102033-7c7cf4a3c5fc?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1609971372250-ae84ab5b3e29?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1519415510236-718bdfcd89c8?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=486&h=315&fit=crop",
]

_IMAGES_FITNESS = [
    "https://images.unsplash.com/photo-1550572017-edd951b55104?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1540497077202-7c8a3999166f?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1549060279-7e168fcee0c2?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1486218119243-13301b7a93a8?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1543362906-acfc16c67564?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1545346315-f4c47e3e1b55?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1526506118085-60ce8714f8c5?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1596357395217-80de13130e92?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1574680178050-55c6a6a96e0a?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1529516548873-9ce57c8f155e?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1607962837359-5e7e89f86776?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=486&h=315&fit=crop",
]

_IMAGES_LIFESTYLE = [
    "https://images.unsplash.com/photo-1516575334481-f85287c2c82d?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1484627147104-f5197bcd6651?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1511988617509-a57c8a288659?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1499209974431-9dddcece7f88?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1545205597-3d9d02c29597?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1528360983277-13d401cdc186?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1494390248081-4e521a5940db?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1543362906-acfc16c67564?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1541199249251-f713e6145474?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1520206183501-b80df61043c2?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1515377905703-c4788e51af15?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1444492417251-9c84a5fa18e0?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1519710164239-da123dc03ef4?w=486&h=315&fit=crop",
    "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=486&h=315&fit=crop",
]

# 전체 풀 합산
SECTION_IMAGES = _IMAGES_HEALTH + _IMAGES_FOOD + _IMAGES_FITNESS + _IMAGES_LIFESTYLE
HEADER_IMAGES = _IMAGES_HEALTH + _IMAGES_BEAUTY + _IMAGES_LIFESTYLE


def _load_used_images() -> set[str]:
    """최근 사용된 이미지 URL 집합을 반환한다."""
    path = Path(__file__).parent.parent / "data" / "used_images.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # [{url, date, keyword}] 형식
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


def _pick_image(pool: list[str], seed: int, keyword: str = "") -> str:
    """최근 사용 이미지를 제외하고 pool에서 이미지를 선택한다."""
    import hashlib
    from datetime import date
    used = _load_used_images()
    # 미사용 이미지 우선
    unused = [img for img in pool if img not in used]
    candidates = unused if unused else pool  # 모두 사용됐으면 전체 풀 사용
    date_str = date.today().isoformat()
    idx = int(hashlib.md5(f"{date_str}-{seed}".encode()).hexdigest(), 16) % len(candidates)
    selected = candidates[idx]
    if keyword:
        _save_used_image(selected, keyword)
    return selected

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


def _load_all_used_keywords() -> list[str]:
    """발행 DB + 블로그 인덱스에서 사용된 키워드/제목을 모두 로드한다."""
    used = []
    data_dir = Path(__file__).parent.parent / "data"

    # 자동화 발행 DB
    titles_file = data_dir / "published_titles.json"
    if titles_file.exists():
        records = json.loads(titles_file.read_text(encoding="utf-8"))
        for r in records:
            if r.get("keyword"):
                used.append(r["keyword"])
            if r.get("title"):
                used.append(r["title"])

    # 블로그 크롤링 인덱스 (기존 수동 발행 글)
    index_file = data_dir / "blog_posts_index.json"
    if index_file.exists():
        posts = json.loads(index_file.read_text(encoding="utf-8"))
        for p in posts:
            if p.get("title"):
                used.append(p["title"])

    return list(set(used))


def get_trending_keywords() -> dict[str, list[str]]:
    """구매 의도(수익형) 1개 + 탐색 의도(정보형) 2개 키워드를 요일별 카테고리로 생성한다.

    Returns:
        {"revenue": ["kw1"], "info": ["kw2", "kw3"]}
    """
    import openai
    from datetime import date

    # 요일별 카테고리 로테이션 (0=월 ~ 6=일)
    WEEKDAY_CATEGORY = {
        0: ("영양제/건강식품", "비타민/오메가3/마그네슘/칼슘/프로바이오틱스/루테인/콜라겐 등 영양제 및 건강식품"),
        1: ("증상/질환 정보",   "피로/두통/관절통/소화불량/불면/혈압/혈당/콜레스테롤 등 증상과 질환"),
        2: ("식단/음식",        "건강식단/저탄고지/지중해식/간헐적 단식/영양 균형/건강 요리 등"),
        3: ("운동/스트레칭",    "홈트레이닝/스트레칭/유산소/근력운동/요가/필라테스 등"),
        4: ("생활습관/수면",    "수면의 질/스트레스 관리/디지털 디톡스/생체리듬/피로 회복 등"),
        5: ("피부/뷰티",        "피부 관리/자외선 차단/주름/탈모/두피/미백/보습 등"),
        6: ("면역/혈관 건강",   "면역력/항산화/혈관 건강/혈액순환/장 건강/간 건강 등"),
    }
    today_weekday = date.today().weekday()
    cat_name, cat_desc = WEEKDAY_CATEGORY[today_weekday]

    used_keywords = _load_all_used_keywords()
    recent_used = used_keywords[-100:] if len(used_keywords) > 100 else used_keywords

    prompt = f"""당신은 건강/생활/뷰티 블로그 수익화 전문가입니다.

오늘의 주제 카테고리: **{cat_name}**
({cat_desc})

이미 발행된 키워드 목록 (겹치면 절대 안 됨):
{json.dumps(recent_used, ensure_ascii=False)}

오늘 카테고리({cat_name}) 에 맞는 키워드만 생성해주세요.

## 수익형 키워드 1개 (구매 의도 — 쿠팡 전환 목적)
- 독자가 "이걸 사야겠다"는 결정 단계에 있는 키워드
- 반드시 포함: 추천/비교/후기/효과/먹어봤더니/써봤더니 중 하나
- 반드시 포함: 숫자(기간·수치·개수) 또는 구체적 대상(40대/직장인/여성 등)
- 예: "40대 여성 마그네슘 영양제 추천 비교", "3개월 먹어봤더니 혈압 낮아진 영양제 후기"

## 정보형 키워드 2개 (탐색 의도 — SEO 트래픽 목적)
- 독자가 원인·이유·방법을 찾는 단계의 키워드
- 깊이 있는 정보를 원하는 주제, 포털에 없는 디테일 포함 가능
- 예: "갱년기 여성 수면 장애 원인 3가지", "혈당 스파이크 식후 증상 놓치는 이유"

반드시 아래 JSON 형식으로만 출력:
{{"revenue": ["수익형1"], "info": ["정보형1", "정보형2"]}}"""

    try:
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        revenue_kws = filter_unique_keywords(data.get("revenue", []))[:1]
        info_kws = filter_unique_keywords(data.get("info", []))[:2]
        logger.info("오늘 카테고리: %s (요일=%d)", cat_name, today_weekday)
        logger.info("수익형 키워드: %s", revenue_kws)
        logger.info("정보형 키워드: %s", info_kws)

        # 부족분 폴백 보충
        if len(revenue_kws) < 1:
            revenue_kws += _fallback_keywords(1, kw_type="revenue")
        if len(info_kws) < 2:
            info_kws += _fallback_keywords(2 - len(info_kws), kw_type="info")

        return {"revenue": revenue_kws[:1], "info": info_kws[:2]}

    except Exception as e:
        logger.error("GPT 키워드 생성 실패: %s → 폴백 사용", e)
        return {
            "revenue": _fallback_keywords(1, kw_type="revenue"),
            "info": _fallback_keywords(2, kw_type="info"),
        }


def _fallback_keywords(count: int, kw_type: str = "revenue") -> list[str]:
    """GPT 실패 시 사용할 폴백 키워드 풀 (수익형/정보형 분리)."""
    REVENUE_POOL = [
        # 구매 의도 — 영양제/제품 추천·비교·후기
        "40대 여성 마그네슘 영양제 추천 비교", "직장인 피로회복 비타민 효과 후기",
        "50대 무릎 관절 영양제 3가지 비교", "갱년기 여성 칼슘 영양제 추천 순위",
        "혈압 낮추는 영양제 3개월 먹어본 후기", "당뇨 전단계 혈당 영양제 추천",
        "탈모 영양제 6개월 써본 솔직 후기", "수면 영양제 추천 효과 있는 것만",
        "장 건강 유산균 추천 비교 2가지", "눈 건강 루테인 영양제 추천 후기",
        "50대 남성 전립선 영양제 추천 비교", "임산부 엽산 철분 영양제 추천",
        "다이어트 보조제 효과 있는 것 추천", "피부 콜라겐 영양제 추천 순위",
        "오메가3 고함량 추천 직접 비교해봤더니", "비타민D 영양제 추천 용량 기준",
    ]
    INFO_POOL = [
        # 탐색 의도 — 원인·이유·방법
        "갱년기 여성 수면 장애 원인 3가지", "혈당 스파이크 식후 증상 놓치는 이유",
        "40대부터 근육 빠지는 이유와 예방법", "내장지방 쌓이는 진짜 원인",
        "만성 피로 원인 혈액검사로 알 수 있는 것", "공복혈당 높아지는 원인",
        "고혈압 약 장기 복용 부작용 알아야 할 것", "콜레스테롤 수치 기준 오해와 진실",
        "장누수 증후군 증상 놓치기 쉬운 신호들", "수면 부족이 혈당에 미치는 영향",
        "염증성 음식 vs 항염 음식 실제 차이", "단백질 부족 증상 나이별 다른 이유",
    ]

    pool = REVENUE_POOL if kw_type == "revenue" else INFO_POOL
    result = []
    for kw in pool:
        if not check_keyword_duplicate(kw):
            if not check_title_duplicate(kw, threshold=0.5):
                result.append(kw)
        if len(result) >= count:
            break

    return result[:count]


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

        MAX_CACHE_PRICE = 50_000  # 캐시 상품 가격 상한 (건강/영양제 기준)

        def _pick_from_cache(candidates: list) -> list:
            """캐시 상품 목록에서 가격 상한 + 세션 내 중복 제거 후 반환."""
            # 가격 오름차순 정렬 후 상한 필터
            affordable = sorted(
                [p for p in candidates if 0 < (p.get("productPrice") or p.get("product_price") or 0) <= MAX_CACHE_PRICE],
                key=lambda p: p.get("productPrice") or p.get("product_price") or 0,
            )
            # 가격 필터 통과 상품 없으면 전체에서 가장 저렴한 순으로 시도
            if not affordable:
                affordable = sorted(
                    [p for p in candidates if (p.get("productPrice") or p.get("product_price") or 0) > 0],
                    key=lambda p: p.get("productPrice") or p.get("product_price") or 0,
                )
            result = []
            for p_data in affordable:
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


def generate_content(keyword: str, products: list, post_type: str = "revenue") -> dict:
    """블로그 콘텐츠를 생성한다. post_type: 'revenue'(수익형) | 'info'(정보형)"""
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

    template = INFO_PROMPT if post_type == "info" else REVENUE_PROMPT
    prompt = template.format(keyword=keyword, products=product_names, internal_links=link_lines)

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


_AD_CONTEXT = {
    "problem": (
        "위와 같은 문제로 고민이라면, 실질적인 도움이 될 수 있는 제품을 확인해보세요.",
        "지금 많은 분들이 찾고 있는 제품이에요. 잠깐 살펴보시면 도움이 될 거예요. 👇",
    ),
    "solution": (
        "앞서 소개한 방법을 실천할 때 함께 활용하면 더 효과적인 제품을 소개해 드릴게요.",
        "직접 써보고 선별한 제품입니다. 가격 대비 만족도가 높아요. 👇",
    ),
    "conclusion": (
        "오늘 알아본 내용, 지금 바로 시작해보실 수 있어요.",
        "바로 아래에서 관련 제품을 확인하고 시작해보세요. 배송도 빠릅니다. 👇",
    ),
}


def build_ad_block(adsense_html: str, product, context_type: str = "problem") -> str:
    """클릭 유도 문맥 + 쿠팡 단일 상품 + 애드센스 광고를 조합한 블록."""
    lead, cta = _AD_CONTEXT.get(context_type, _AD_CONTEXT["problem"])
    product_html = ""
    if product:
        name = getattr(product, "product_name", "") or product.get("productName", "")
        price = getattr(product, "product_price", 0) or int(product.get("productPrice", 0))
        url = getattr(product, "product_url", "#") or product.get("productUrl", "#")
        img = getattr(product, "product_image", "") or product.get("productImage", "")
        is_rocket = getattr(product, "is_rocket", False)
        img_tag = f'<img src="{img}" alt="{name[:20]}" style="width:130px;height:130px;object-fit:contain;border-radius:6px;background:#fff;border:1px solid #eee;" loading="lazy" />' if img else ""
        rocket_badge = "🚀 로켓배송" if is_rocket else "일반배송"
        product_html = f"""<div style="margin:10px 0 15px;padding:18px;border:1px solid #e0e0e0;border-radius:8px;background:#fafafa;">
<a href="{url}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;color:#333;">
<div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
{img_tag}
<div style="flex:1;min-width:200px;">
<p style="font-size:17px;font-weight:bold;color:#2c3e50;margin:0 0 8px 0;">{name}</p>
<p style="font-size:20px;font-weight:bold;color:#e44d26;margin:0 0 6px 0;">{price:,}원</p>
<p style="font-size:13px;color:#888;margin:0 0 10px 0;">{rocket_badge}</p>
<span style="display:inline-block;padding:8px 24px;background:#e44d26;color:white;border-radius:4px;font-size:14px;font-weight:bold;">최저가 확인하기 →</span>
</div></div></a></div>"""

    return f"""<div style="background:#fff8f8;border-radius:10px;padding:20px;margin:25px 0;border:1px solid #FFE4E8;">
<p style="color:#555;font-size:14px;margin:0 0 6px 0;">{lead}</p>
<p style="color:#e44d26;font-size:13px;font-weight:bold;margin:0 0 12px 0;">{cta}</p>
{product_html}
{adsense_html}
<p style="color:#999;font-size:11px;margin:8px 0 0 0;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
</div>"""


def _pick_section_images(keyword: str, post_index: int, sections: list) -> dict[int, tuple[str, str]]:
    """섹션 인덱스 → (이미지URL, alt텍스트) 매핑 반환.

    규칙:
    - 최대 3개 (기본 2개: 헤더 + 핵심 설명 섹션)
    - 삽입 위치: 헤더(도입부), 핵심 설명(2번째 섹션), 경험/사례 섹션(5번째 섹션)
    - URL·파일명 중복 없음, alt 텍스트 모두 다르게
    - 글 흐름 우선 → 이미지 없어도 자연스러우면 생략
    """
    from src.content.image_search import get_images_for_keyword as _get_imgs

    # 이미지 3개 요청 → URL/파일명 중복 제거
    raw = _get_imgs(keyword, count=3, post_index=post_index)
    seen_urls: set[str] = set()
    seen_fnames: set[str] = set()
    unique: list[str] = []
    for url in raw:
        fname = url.split("/")[-1]
        if url not in seen_urls and fname not in seen_fnames:
            seen_urls.add(url)
            seen_fnames.add(fname)
            unique.append(url)
        if len(unique) >= 3:
            break

    # 섹션별 alt 텍스트 생성 (섹션 제목 기반, 모두 다르게)
    def _alt(section_heading: str, context: str) -> str:
        return f"{keyword} — {section_heading}"[:60]

    # 삽입 대상 섹션 결정: 핵심 설명(idx=2), 경험(idx=4 또는 5)
    # sections[0] = 도입부, sections[1..] = 본문
    body_sections = [s for s in sections[1:] if s.get("heading", "") != "마무리"]
    img_map: dict[int, tuple[str, str]] = {}  # 섹션 i → (url, alt)

    # 핵심 설명 섹션: 인덱스 2 (body_sections[1])
    key_sec_idx = 2
    # 경험/사례 섹션: "경험" "사례" "후기" "실제" 포함 or 인덱스 4~5
    exp_sec_idx = None
    for j, s in enumerate(body_sections, 1):
        hdg = s.get("heading", "")
        if any(kw in hdg for kw in ["경험", "사례", "후기", "실제", "써봤", "먹어봤", "직접"]):
            exp_sec_idx = j
            break
    if exp_sec_idx is None:
        exp_sec_idx = min(5, len(body_sections))  # fallback: 5번째

    # URL 배정 (최대 2개 섹션 이미지; 이미지 부족 시 생략)
    if len(unique) >= 2:
        img_map[key_sec_idx] = (unique[1], _alt(
            body_sections[key_sec_idx - 1]["heading"] if key_sec_idx - 1 < len(body_sections) else keyword,
            "핵심설명"
        ))
    if len(unique) >= 3 and exp_sec_idx and exp_sec_idx != key_sec_idx:
        img_map[exp_sec_idx] = (unique[2], _alt(
            body_sections[exp_sec_idx - 1]["heading"] if exp_sec_idx - 1 < len(body_sections) else keyword,
            "경험사례"
        ))

    return img_map, unique[0] if unique else None


def build_full_html(data: dict, products: list, post_index: int, keyword: str = "", post_type: str = "revenue") -> str:
    """전체 블로그 포스트 HTML을 조립한다."""
    sections = data.get("sections", [])

    # 이미지 선택: URL·파일명 중복 없음, alt 모두 다르게, 최대 3개
    if keyword:
        section_img_map, header_img = _pick_section_images(keyword, post_index, sections)
        if not header_img:
            header_img = HEADER_IMAGES[0]
    else:
        header_img = _pick_image(HEADER_IMAGES, post_index, keyword=keyword)
        section_img_map = {}
    sections = data.get("sections", [])
    tags = data.get("tags", [])
    summary_cards = data.get("summary_cards", [])
    faqs = data.get("faq", [])
    # 애드센스 광고 슬롯
    ad_top = build_adsense_ad(os.getenv("ADSENSE_SLOT_TOP", ""))
    ad_mid = build_adsense_ad(os.getenv("ADSENSE_SLOT_MID", ""), "infeed")
    ad_bottom = build_adsense_ad(os.getenv("ADSENSE_SLOT_BOTTOM", ""))

    # 정보형은 쿠팡 상품 사용 안 함
    is_revenue = (post_type == "revenue")
    # 저가 → 중가 → 고가 순으로 정렬
    if products and is_revenue:
        sorted_products = sorted(products[:3], key=lambda p: int(p.productPrice) if hasattr(p, "productPrice") else p.get("productPrice", 0) if isinstance(p, dict) else 0)
    else:
        sorted_products = []
    p_list = sorted_products
    p_problem  = p_list[0] if len(p_list) > 0 else None  # 문제 인식 직후 (저가)
    p_solution = p_list[1] if len(p_list) > 1 else None  # 해결 방법 직후 (중가)
    p_conclude = p_list[2] if len(p_list) > 2 else None  # 결론 직전 (고가)

    parts = []

    # 대표 이미지 (도입부 — alt는 제목 기반으로 구체적으로)
    header_alt = data.get("title", keyword) or keyword
    parts.append(f'<figure style="text-align: center; margin: 0 0 20px 0;"><img src="{header_img}" alt="{header_alt}" style="max-width:100%; height:auto; border-radius:8px;" width="486" /></figure>')

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

        # 섹션 content에서 GPT가 삽입한 이미지 전체 제거 (시스템이 _pick_section_images로 직접 삽입)
        content = section.get("content", "")
        content = re.sub(r'<figure[^>]*>[\s\S]*?</figure>', '', content)
        content = re.sub(r'<img\s[^>]*/?>',  '', content)

        # 지정된 섹션(핵심설명/경험)에만 시스템 이미지 삽입 — URL·alt 중복 없음
        img_html = ""
        if i in section_img_map:
            sec_img_url, sec_img_alt = section_img_map[i]
            img_html = f'<figure style="text-align: center; margin: 15px 0;"><img src="{sec_img_url}" alt="{sec_img_alt}" style="max-width:100%; height:auto; border-radius:8px;" width="486" /></figure>'
        parts.append(f"""<div id="sec{i}" style="background-color: #ffffff; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
<h2 style="color: #2c3e50; border-bottom: 2px solid #FFE4E8; padding-bottom: 10px;">{section["heading"]}</h2>
{img_html}
{content}
</div>""")

        # 광고: 문제 인식 직후(2번째 섹션), 해결 방법 직후(4번째 섹션)
        if i == 2:
            parts.append(build_ad_block(ad_top, p_problem, "problem"))
        elif i == 4:
            parts.append(build_ad_block(ad_mid, p_solution, "solution"))

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

    # 결론 직전 광고 (문맥 + 쿠팡 3번째 상품 + 애드센스)
    parts.append(build_ad_block(ad_bottom, p_conclude, "conclusion"))

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

    # 쿠팡 추천 상품은 각 광고 블록에 분산 삽입되었으므로 별도 섹션 불필요

    # 태그
    tag_str = ", ".join(tags)
    parts.append(f'<div style="margin-bottom: 30px;"><p>{tag_str}</p></div>')

    # 쿠팡 배너 (최하단)
    parts.append("""<div style="text-align: center; margin: 20px 0 30px 0;">
<a href="https://link.coupang.com/a/d4YwkD" target="_blank" referrerpolicy="unsafe-url"><img src="https://ads-partners.coupang.com/banners/882911?subId=&traceId=V0-301-879dd1202e5c73b2-I882911&w=728&h=90" alt="" style="max-width:100%; height:auto;" /></a>
</div>""")

    result = "\n\n".join(parts)

    # 후처리 1: GPT가 삽입한 모든 <img> 제거 (쿠팡 배너는 ads-partners.coupang.com 도메인으로 보존)
    result = re.sub(
        r'<figure[^>]*>[\s\S]*?</figure>',
        '',
        result
    )
    result = re.sub(
        r'<img\s[^>]*src="(?!https://ads-partners\.coupang\.com)[^"]*"[^>]*/?>',
        '',
        result
    )

    # 후처리 2: 쿠팡 광고 이미지 alt가 비어있으면 공백으로 유지 (의도적)
    # 후처리 3: GPT가 만든 CSS 버그 수정 (border: 1px solid: → border: 1px solid)
    result = re.sub(r'border:\s*(\w+\s+\w+)\s*:\s*(#[0-9a-fA-F]+)', r'border: \1 \2', result)

    # 후처리 4: GPT 앵커 제거 (시스템 #sec 유지)
    result = re.sub(r'<a[^>]*href="#(?!sec\d)[^"]*"[^>]*>(.*?)</a>', r'\1', result)

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
    output_base = Path(__file__).parent.parent / "output" / "posts"
    output_dir = output_base / today

    # 오늘 폴더 기존 파일 삭제 (재생성 시 중복 방지)
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        logger.info("기존 오늘 포스트 삭제: %s", output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 수익형 키워드 1개 + 정보형 키워드 2개 생성
    kw_map = get_trending_keywords()
    revenue_kws = kw_map.get("revenue", [])
    info_kws = kw_map.get("info", [])
    # 순서: 수익형 → 정보형 → 정보형
    keyword_plan = [
        (revenue_kws[0] if revenue_kws else "건강 영양제 추천", "revenue"),
        (info_kws[0] if len(info_kws) > 0 else "건강 정보", "info"),
        (info_kws[1] if len(info_kws) > 1 else info_kws[0] if info_kws else "건강 생활습관", "info"),
    ]
    logger.info("=== %s 일일 포스트 생성 시작 ===", today)
    logger.info("  수익형: %s", revenue_kws)
    logger.info("  정보형: %s", info_kws)

    results = []

    for i, (keyword, post_type) in enumerate(keyword_plan):
        logger.info("[%d/3] 키워드: '%s' (%s)", i + 1, keyword, post_type)

        # 1. 쿠팡 상품 검색 (수익형만)
        products = search_coupang_products(keyword) if post_type == "revenue" else []
        logger.info("  쿠팡: %d개 상품", len(products))

        # 2. 콘텐츠 생성
        logger.info("  콘텐츠 생성 중... [%s]", post_type)
        data = generate_content(keyword, products, post_type=post_type)
        logger.info("  제목: %s", data.get("title", ""))

        # 3. 전체 HTML 조립
        blog_html = build_full_html(data, products, i, keyword=keyword, post_type=post_type)

        # 4. 파일 저장 (발행 도구 UI 없이 순수 HTML)
        import re as _re
        safe_name = _re.sub(r'[\\/:*?"<>|]', '', keyword).replace(" ", "_")[:30]
        filename = f"post_{i + 1}_{safe_name}.html"
        filepath = output_dir / filename
        filepath.write_text(blog_html, encoding="utf-8")
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
        if i < len(keyword_plan) - 1:
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
