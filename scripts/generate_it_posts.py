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

_CORE_GOALS_IT = """
## 핵심 지시 (정보글이 아니라 돈 되는 글을 만들어라)
너는 구글 SEO와 애드센스 수익 구조를 이해하는 IT 블로그 전문가다.
검색 유입 → 체류 → 클릭 → 수익까지 이어지는 글을 작성한다.

### 규칙 1: 키워드
- 반드시 롱테일 키워드 사용 (이유/방법/추천/후기/비교 포함)
- 검색 의도가 명확한 키워드만 사용
- 제목에 숫자+결과 또는 경험 1개 이상 포함

### 규칙 2: 글 구조
- 문제 → 공감 → 해결 → 직접 사용 경험 → 행동 순서 필수
- 첫 문단에 실패 경험 또는 불편 상황 포함 (독자 공감 유도)
- 실제 경험처럼 자연스럽게 작성
- 수치 포함 (사용 기간, 성능 변화, 가격 대비 만족도 등)

### 규칙 3: 수익 구조 (광고 위치)
- 광고는 3곳에 고정:
  1. 문제 인식 직후
  2. 해결 방법 직후
  3. 결론 직전
- 각 광고 바로 위에 "지금 이게 필요하다"는 감정 연결 문장 삽입

### 규칙 4: CTA
- 중간 CTA 1개 이상: "이 방법이 어렵다면 아래 방법이 더 현실적입니다" 포함
- 마지막 CTA 1개 필수: 다음 관련 IT 글로 연결

### 규칙 5: 제품 추천 순서
- 제품은 바로 추천하지 말고 문제→해결→경험→결과 이후에만 배치
- 제품 블록 바로 위 브릿지 문장 필수 (ex: "직접 써보니 이게 없었으면 불편했을 것 같았어요.")
- 선택 구조: 이런 사람 → A / 저런 사람 → B
- 가격 순서: 저가 → 중가 → 고가

### 규칙 6: 이미지
- 이미지 최대 3개
- 같은 이미지 반복 금지
- alt 텍스트 모두 다르게 작성

### 규칙 7: 금지
- 백과사전식 설명 금지
- 의미 없는 표 반복 금지
- 검색하면 바로 나오는 뻔한 팁 금지 ("절전 모드 켜세요" 수준)
- 박스(강조 div) 연속 2개 이상 금지 (사이에 텍스트 문단 1개 이상)
"""

IT_REVENUE_PROMPT = """당신은 "테크온도(IT++)" 티스토리 블로그의 IT 전문 리뷰어입니다.
""" + _CORE_GOALS_IT + """
## 글 유형: 수익형 (상품 추천 + CTA 중심)
- 목적: 독자의 IT 문제를 해결하면서 관련 상품 구매를 자연스럽게 유도
- 쿠팡 추천 상품을 해결책 맥락에서 자연스럽게 언급 (억지 끼워넣기 금지)
- 제품 배치 순서 (필수): 문제 제기 → 공감 → 해결책 설명 → 직접 사용 경험/수치 결과 → **이 시점에만** 제품 블록
- 제품 블록 바로 위 브릿지 문장 필수: "직접 써보니 이게 없었으면 불편했을 것 같았어요. 그래서 이걸 계속 쓰게 됐습니다." 형식
- 제품 가격 순서: 저가 → 중가 → 고가 (부담감 최소화)
- 제품 블록 앞에 선택 구조 카드: "이런 분 → A 제품 / 저런 분 → B 제품" 2열 카드
- 이미지: 최대 3개, alt 텍스트 모두 다르게 (중복 금지), "[키워드] [구체적 상황]" 형식
- 박스(강조 div) 연속 2개 이상 금지 — 박스 사이에 텍스트 문단 1개 이상 삽입
- 각 섹션 첫 100자는 순수 텍스트로 시작 (박스·리스트·표 금지)

## 글 스타일
- 제목: 반드시 롱테일 키워드 형식 (20~35자). 아래 규칙 필수:
  * [타겟/상황 + 숫자/결과 + 제품/주제 + 방법/이유/후기/추천/비교] 구조
  * "방법", "이유", "후기", "추천", "비교" 중 하나 반드시 포함
  * 숫자, 결과, 경험 중 최소 1개 반드시 포함
    - 숫자: 가격(3만원대), 기간(1개월), 수치(배터리 30시간), 개수(3개 비교)
    - 결과: 속도 2배, 끊김 해결, 배터리 늘어난
    - 경험: 직접 써봤더니, 한 달 써보고, 3개 비교해봤더니
  * ✅ 좋은 예: "3만원대 무선이어폰 한 달 써본 솔직 후기", "SSD 교체 후 부팅 속도 3배 빨라진 이유"
  * ✅ 좋은 예: "노트북 3개 직접 비교해봤더니 이게 달랐다", "재택근무 키보드 2개월 써보고 추천하는 이유"
  * ❌ 금지: 숫자/결과 없는 막연한 제목, "완벽 가이드", "총정리", "TOP5", 연도(2024~2026)
- 전체 흐름: 문제 제기 → 공감 → 해결책 → 사례/경험 → 행동 촉구 순서 필수
- H2 섹션 6~7개, H3 사용 안 함
- **전체 최소 3,000자 이상** (불필요한 반복 없이 실질적 내용으로만)
- 각 섹션 400~600자, 문단 4~6문장 (구체적 스펙, 가격, 비교 포함)
- ❌ 금지: 같은 내용 반복, "앞서 설명했듯이", "이상으로 알아봤습니다" 같은 빈 문장
- ❌ 금지: "배터리 오래 쓰려면 절전 모드 켜세요" 같이 검색하면 바로 나오는 뻔한 내용
- ✅ 필수: 차별화된 관점 1개 이상 포함
  * 반직관적 사실 / 간과된 디테일 / 실패 경험 / 수치 비교 / 대부분이 모르는 설정/팁
  * 예: "가격 비쌀수록 좋다" ❌ → "3만원대가 10만원대보다 나은 구체적인 경우" ✅
- ✅ 기준: 문장마다 새로운 정보(수치, 스펙, 비교, 경험) 포함
- 문체: ~합니다/~세요/~요 존댓말, 친근하고 실용적
- 표(table)는 글 전체 최대 1~2개 (꼭 필요한 스펙 비교에만, 매 섹션마다 넣지 말 것)
- 불릿/번호 리스트는 꼭 필요한 경우만 — 3개 이상 연속 리스트는 문단으로 풀어쓸 것
- ❌ 금지: 본문과 같은 내용을 "요약" 박스로 반복
- 마지막 섹션은 "마무리"
- 태그 6~7개

## 글쓰기 규칙
1. **도입부 첫 3줄 안에 문제 제기 필수**
   예: "노트북이 느려졌는데 새 제품을 사기엔 부담스럽다면, SSD 교체만으로 해결될 수 있습니다."
2. **섹션 흐름**: 1~2번째=문제 원인, 3~4번째=해결책, 5번째=직접 사용 경험(필수)
   - 반드시 "내가 해봤다" 서술 포함: 실패 → 개선 → 수치로 증명된 결과 흐름
   - 반드시 구체적 수치 포함: 사용 기간, 성능 변화(속도, 배터리, ms 등), 가격 대비 만족도
   - 예시: "처음 2주는 연결이 불안정했는데, 펌웨어 업데이트 후 끊김이 90% 줄었습니다."
   - 예시: "3개 제품을 한 달씩 써봤더니 A제품의 노이즈 캔슬링이 압도적으로 좋았어요."
   - ❌ 금지: "좋은 것 같아요", "추천해요" 같은 근거 없는 평가
   - ✅ 필수: 사용 기간 + 수치/비교 + 결론 3요소 모두 포함
3. **서식 절제 규칙**:
   - 표: 글 전체 최대 1~2개 (스펙 비교 등 꼭 필요한 곳에만)
   - 리스트: 연속 3개 이상은 문단으로 풀어쓸 것
   - 요약 반복 금지: 섹션 내용을 다시 나열하는 "정리" 박스 추가 금지
3. **CTA 필수 규칙**:
   - **중간 CTA (1개 이상)**: 해결책 섹션 끝에 삽입. "이 방법이 어렵다면 ~" 형태 + 관련 글 링크
   - **최종 CTA (필수)**: 마지막 섹션 끝에 삽입. 다음에 읽으면 좋은 관련 IT 글로 연결
   - CTA HTML 형식 (중간):
     ```html
     <div style="background:linear-gradient(135deg,#F0F7FF,#E3F2FD);border-radius:10px;padding:20px;margin:25px 0;border-left:4px solid #90CAF9;text-align:center;">
     <p style="font-size:15px;color:#555;margin:0 0 8px 0;">이 방법이 어렵다면?</p>
     <p style="font-size:17px;font-weight:bold;color:#1565C0;margin:0 0 15px 0;">[더 쉬운 대안 한 줄 설명]</p>
     <a href="[내부링크URL]" style="display:inline-block;padding:12px 30px;background:#1565C0;color:white;border-radius:6px;text-decoration:none;font-weight:bold;">바로 확인하기 →</a>
     </div>
     ```
   - CTA HTML 형식 (최종):
     ```html
     <div style="background:linear-gradient(135deg,#F0F7FF,#E3F2FD);border-radius:10px;padding:25px;margin:30px 0;text-align:center;border:2px solid #90CAF9;">
     <p style="font-size:18px;font-weight:bold;color:#1565C0;margin:0 0 10px 0;">📌 다음으로 읽으면 좋은 글</p>
     <a href="[내부링크URL]" style="display:block;padding:15px;background:#fff;border-radius:8px;text-decoration:none;color:#1565C0;font-weight:bold;border:1px solid #90CAF9;margin-top:12px;">👉 [관련 글 제목]</a>
     </div>
     ```
4. 각 H2 섹션에 블루톤 스타일 테이블 포함 (아래 HTML 형식)
5. 각 섹션 내용은 topic-content div로 감쌈
6. 절대로 목차(TOC)를 생성하지 마세요
7. 핵심 요약 카드 5개 (flexbox)
8. FAQ 3개
9. 제품 비교 시 장단점 명확히

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

## 내부 링크 (CTA에 반드시 활용)
- 중간 CTA 버튼 href: https://uyoblog.tistory.com (관련 글 없을 시 블로그 메인)
- 최종 CTA href: https://uyoblog.tistory.com
※ 중간 CTA("이 방법이 어렵다면" 버튼)와 최종 CTA("다음으로 읽으면 좋은 글")에 각각 사용하세요.

## 출력: 반드시 JSON만
{{"title":"제목(20~35자, 숫자+결과+방법/이유/후기/추천/비교)","meta_description":"155자이내 SEO 설명","sections":[{{"heading":"H2제목","content":"HTML본문(400자이상, 반복없이 실질적 내용)"}}],"summary_cards":["요약1","요약2","요약3","요약4","요약5"],"faq":[{{"q":"질문","a":"답변"}}],"tags":["태그1","태그2"]}}"""

IT_INFO_PROMPT = """당신은 "테크온도(IT++)" 티스토리 블로그의 IT 전문 작가입니다.
""" + _CORE_GOALS_IT + """
## 글 유형: 정보형 (순수 IT 정보 제공, 상품 추천 없음)
- 목적: 독자에게 깊이 있는 IT 정보를 제공하여 신뢰 구축 및 SEO 트래픽 확보
- ❌ 절대 금지: 상품 추천, 쿠팡 링크, "이 제품 사세요", "최저가 확인" 같은 상업적 표현
- 중간 CTA: "이 내용이 더 궁금하다면?" + 관련 IT 정보 글 링크
  <div style="background:linear-gradient(135deg,#F0F7FF,#E3F2FD);border-radius:10px;padding:20px;margin:25px 0;border-left:4px solid #90CAF9;text-align:center;"><p style="font-size:15px;color:#555;margin:0 0 8px 0;">이 내용이 더 궁금하다면?</p><a href="https://uyoblog.tistory.com" style="display:inline-block;padding:12px 30px;background:#1565C0;color:white;border-radius:6px;text-decoration:none;font-weight:bold;">관련 글 보러가기 →</a></div>
- 최종 CTA: "📌 함께 읽으면 좋은 글" + 관련 정보 글 카드
  <div style="background:linear-gradient(135deg,#F0F7FF,#E3F2FD);border-radius:10px;padding:25px;margin:30px 0;text-align:center;border:2px solid #90CAF9;"><p style="font-size:18px;font-weight:bold;color:#1565C0;margin:0 0 10px 0;">📌 함께 읽으면 좋은 글</p><a href="https://uyoblog.tistory.com" style="display:block;padding:15px;background:#fff;border-radius:8px;text-decoration:none;color:#1565C0;font-weight:bold;border:1px solid #90CAF9;margin-top:12px;">👉 [관련 글 제목]</a></div>

## 글 스타일
- 제목: 반드시 롱테일 키워드 형식 (20~35자), 숫자·결과·경험 중 1개 이상 포함
  * ✅ 예: "SSD vs HDD 실제 속도 차이 직접 비교해봤더니", "RAM 16GB와 32GB 차이 체감한 솔직 후기"
  * ❌ 금지: 연도, "완벽 가이드", "총정리", "TOP5"
- 전체 흐름: 문제 제기 → 원인 분석 → 해결책 → 직접 경험(필수) → 결론
- 도입부 첫 3줄 안에 문제 제기 필수
- 5번째 H2에 직접 사용 경험 필수: 실패 → 개선 → 수치 결과 (기간+수치+변화 3요소)
- H2 섹션 6~7개, H3 사용 안 함, 목차(TOC) 생성 금지
- 전체 최소 3,000자 이상, 각 섹션 400~600자
- 표: 글 전체 최대 1~2개, 리스트: 3개 이상 연속이면 문단으로 풀어쓸 것
- ❌ 금지: 반복 요약, 의미 없는 문장
- 태그 6~7개
- 각 섹션은 topic-content div로 감쌈:
  <div class="topic-content" style="background-color: #F5F9FF; padding: 20px; border-radius: 8px; border-left: 4px solid #90CAF9;"><p style="color: #333; line-height: 1.8;">내용</p></div>

## 이번 글 요청
- 키워드: "{keyword}"
- 카테고리: IT/가젯
- 연도 금지

## 출력: 반드시 JSON만
{{"title":"제목(20~35자, 숫자+결과+방법/이유/후기/비교)","meta_description":"155자이내 SEO 설명","sections":[{{"heading":"H2제목","content":"HTML본문(400자이상)"}}],"summary_cards":["요약1","요약2","요약3","요약4","요약5"],"faq":[{{"q":"질문","a":"답변"}}],"tags":["태그1","태그2"]}}"""

# 하위 호환 유지
BLOG_STYLE_PROMPT = IT_REVENUE_PROMPT

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


def get_it_keywords() -> dict[str, list[str]]:
    """수익형(구매 의도) 2개 + 정보형(탐색 의도) 1개 키워드를 반환한다.

    Returns:
        {"revenue": ["kw1", "kw2"], "info": ["kw3"]}
    """
    day = datetime.now().day

    # 구매 의도: 추천·비교·후기·써봤더니 포함
    REVENUE_POOLS = {
        "가젯/악세서리": [
            "3만원대 무선이어폰 한 달 써본 솔직 후기",
            "노이즈캔슬링 이어폰 2개 직접 비교해봤더니",
            "재택근무 기계식 키보드 추천 이유",
            "가성비 블루투스 스피커 추천 비교",
            "게이밍 마우스 3개 써보고 추천하는 이유",
            "보조배터리 고르는 법과 추천 모델",
            "스마트워치 2개 비교해봤더니 이게 달랐다",
            "웹캠 재택근무용 추천 직접 써본 후기",
            "무선충전 패드 추천 속도 비교",
            "게이밍 헤드셋 3만원대 vs 10만원대 비교",
        ],
        "노트북/PC": [
            "가성비 노트북 추천 직접 써본 후기",
            "SSD 교체 후 속도 3배 빨라진 이유와 추천",
            "사무용 노트북 3개 비교해봤더니 이게 최고",
            "RAM 16GB vs 32GB 실제 체감 차이 후기",
            "4K 모니터 추천 눈 피로 줄어든 이유",
            "외장SSD vs 외장HDD 실사용 비교",
            "미니PC 재택근무 3개월 써본 솔직 후기",
            "조립PC 견적 직접 맞춰봤더니 이게 나왔다",
            "맥북 vs 윈도우 노트북 6개월 써본 비교",
            "그래픽카드 업그레이드 전후 성능 비교 후기",
        ],
    }

    # 탐색 의도: 원인·이유·차이 포함
    INFO_POOLS = [
        "노트북 발열 심해지는 진짜 원인과 해결법",
        "배터리 빨리 닳는 이유 놓치기 쉬운 원인",
        "와이파이 느려지는 이유 설정으로 해결하는 법",
        "SSD vs HDD 실제 속도 차이 얼마나 날까",
        "RAM 부족 증상 PC가 보내는 신호들",
        "스마트폰 저장 공간 부족한 진짜 이유",
        "노트북 오래 쓰면 느려지는 이유와 원인",
        "블루투스 연결 끊기는 원인 해결하는 법",
        "CPU vs GPU 어느 게 성능에 더 중요한가",
        "모니터 해상도 차이 실제로 눈에 보이는 기준",
    ]

    cats = list(REVENUE_POOLS.keys())
    revenue_kws = []
    for i, cat in enumerate(cats[:2]):
        pool = REVENUE_POOLS[cat]
        revenue_kws.append(pool[(day + i * 5) % len(pool)])

    info_kw = INFO_POOLS[(day * 3) % len(INFO_POOLS)]

    return {"revenue": revenue_kws, "info": [info_kw]}


def generate_content(keyword: str, products: list, post_type: str = "revenue") -> dict | None:
    """OpenAI API로 IT 블로그 콘텐츠를 생성한다."""
    import openai

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    product_names = ", ".join(p.get("productName", "")[:30] for p in products[:3]) if products else "관련 상품 없음"

    template = IT_INFO_PROMPT if post_type == "info" else IT_REVENUE_PROMPT
    if post_type == "info":
        prompt = template.format(keyword=keyword)
    else:
        prompt = template.format(keyword=keyword, products=product_names)

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


def build_full_html(data: dict, keyword: str, products: list, post_date: str, post_index: int = 0, post_type: str = "revenue") -> str:
    """완성된 HTML 페이지를 조립한다."""
    title = data.get("title", keyword)
    meta_desc = data.get("meta_description", "")
    sections = data.get("sections", [])
    summary_cards = data.get("summary_cards", [])
    faq = data.get("faq", [])
    tags = data.get("tags", [])

    # 이미지 선택: URL·파일명 중복 없음, alt 모두 다르게, 최대 3개
    from src.content.image_search import get_images_for_keyword as _get_imgs
    _raw_imgs = _get_imgs(keyword, count=3, post_index=post_index)
    _seen_urls: set = set()
    _seen_fnames: set = set()
    _unique_imgs: list = []
    for _u in _raw_imgs:
        _fn = _u.split("/")[-1]
        if _u not in _seen_urls and _fn not in _seen_fnames:
            _seen_urls.add(_u)
            _seen_fnames.add(_fn)
            _unique_imgs.append(_u)
        if len(_unique_imgs) >= 3:
            break
    header_img = _unique_imgs[0] if _unique_imgs else _pick_image(keyword, 0)

    # 삽입 위치: 핵심설명(섹션 2) + 경험/사례 섹션 (최대 2개)
    _body_secs = [s for s in sections if s.get("heading", "") != "마무리"]
    _exp_idx = None
    for _j, _s in enumerate(_body_secs):
        if any(_kw in _s.get("heading", "") for _kw in ["경험", "사례", "후기", "실제", "써봤", "직접", "비교"]):
            _exp_idx = _j
            break
    if _exp_idx is None:
        _exp_idx = min(4, len(_body_secs) - 1)

    # 섹션인덱스 → (url, alt) 매핑 (alt는 섹션 제목 기반, 모두 다르게)
    _section_img_map: dict = {}
    if len(_unique_imgs) >= 2:
        _key_idx = min(1, len(_body_secs) - 1)
        _section_img_map[_key_idx] = (
            _unique_imgs[1],
            f"{keyword} 핵심 설명 — {_body_secs[_key_idx].get('heading', '')}"[:60]
        )
    if len(_unique_imgs) >= 3 and _exp_idx is not None and _exp_idx not in _section_img_map:
        _section_img_map[_exp_idx] = (
            _unique_imgs[2],
            f"{keyword} 직접 경험 — {_body_secs[_exp_idx].get('heading', '')}"[:60]
        )

    # 정보형은 쿠팡 상품 사용 안 함 / 저가→중가→고가 순 정렬
    if products and post_type == "revenue":
        p_list = sorted(products[:3], key=lambda p: p.get("productPrice", 0) if isinstance(p, dict) else 0)
    else:
        p_list = []

    def _single_product_html(p: dict, context_type: str = "problem") -> str:
        """클릭 유도 문맥 + 단일 쿠팡 상품 블록 (IT 블루톤)."""
        _ctx = {
            "problem": ("이런 불편함이 있으셨다면, 아래 제품이 실질적인 해결책이 될 수 있어요.", "지금 많은 분들이 찾고 있는 제품이에요. 👇"),
            "solution": ("앞서 소개한 방법과 함께 쓰면 더 효과적인 제품입니다.", "직접 써본 후 추천하는 제품이에요. 👇"),
            "conclusion": ("오늘 다룬 내용을 바로 실천해볼 수 있어요.", "지금 바로 확인해보세요. 빠른 배송으로 받아볼 수 있어요. 👇"),
        }
        lead, cta = _ctx.get(context_type, _ctx["problem"])
        name = p.get("productName", "")
        price = int(p.get("productPrice", 0))
        url = p.get("productUrl", "#")
        img = p.get("productImage", "")
        img_tag = f'<img src="{img}" alt="{name[:20]}" style="width:130px;height:130px;object-fit:contain;border-radius:6px;background:#fff;border:1px solid #eee;" loading="lazy" />' if img else ""
        return f"""<div style="background:#F0F7FF;border-radius:10px;padding:20px;margin:25px 0;border:1px solid #90CAF9;">
<p style="color:#555;font-size:14px;margin:0 0 6px 0;">{lead}</p>
<p style="color:#1565C0;font-size:13px;font-weight:bold;margin:0 0 12px 0;">{cta}</p>
<div style="padding:18px;border:1px solid #e0e0e0;border-radius:8px;background:#fafafa;">
<a href="{url}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;color:#333;">
<div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
{img_tag}
<div style="flex:1;min-width:200px;">
<p style="font-size:17px;font-weight:bold;color:#1565C0;margin:0 0 8px 0;">{name}</p>
<p style="font-size:20px;font-weight:bold;color:#e44d26;margin:0 0 10px 0;">{price:,}원</p>
<span style="display:inline-block;padding:8px 24px;background:#1565C0;color:white;border-radius:4px;font-size:14px;font-weight:bold;">최저가 확인하기 →</span>
</div></div></a></div>
<p style="color:#999;font-size:11px;margin:8px 0 0 0;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
</div>"""

    # 섹션 HTML - 지정된 섹션에만 이미지 삽입 (URL·alt 중복 없음)
    sections_html = ""
    for i, sec in enumerate(sections):
        heading = sec.get("heading", "")
        content = sec.get("content", "")
        if i in _section_img_map:
            _s_url, _s_alt = _section_img_map[i]
            img_html = f'<div style="text-align: center; margin: 15px 0;"><img src="{_s_url}" alt="{_s_alt}" style="max-width: 100%; height: auto; border-radius: 8px;" loading="lazy" /></div>'
        else:
            img_html = ""
        sections_html += f"""
<h2 style="font-size: 22px; color: #1565C0; border-bottom: 3px solid #42A5F5; padding-bottom: 10px; margin: 40px 0 20px;">{heading}</h2>
{img_html}
{content}
"""
        # 광고: 문제 인식 직후(2번째 섹션), 해결 방법 직후(4번째 섹션)
        if i == 1 and len(p_list) > 0:
            sections_html += _single_product_html(p_list[0], "problem")
        elif i == 3 and len(p_list) > 1:
            sections_html += _single_product_html(p_list[1], "solution")

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

    # 결론 직전 광고 (3번째 쿠팡 상품)
    conclude_ad_html = _single_product_html(p_list[2], "conclusion") if len(p_list) > 2 else ""

    # 쿠팡 상품은 섹션별 분산 삽입되었으므로 별도 하단 블록 불필요
    coupang_html = ""

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

    import re as _re
    # 후처리 1: GPT가 섹션 내 삽입한 외부 <img> 제거 (GitHub 호스팅 외 경로)
    sections_html = _re.sub(
        r'<img\s[^>]*src="(?!https://raw\.githubusercontent\.com/kgbae99/tistory-blog-auto)[^"]*"[^>]*/?>',
        '',
        sections_html
    )
    # 후처리 2: CSS 버그 수정 (border: 1px solid: → border: 1px solid)
    sections_html = _re.sub(r'border:\s*(\w+\s+\w+)\s*:\s*(#[0-9a-fA-F]+)', r'border: \1 \2', sections_html)

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
{conclude_ad_html}
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

    kw_map = get_it_keywords()
    revenue_kws = kw_map.get("revenue", [])
    info_kws = kw_map.get("info", [])
    keyword_plan = [
        (revenue_kws[0] if len(revenue_kws) > 0 else "무선이어폰 추천", "revenue"),
        (info_kws[0]    if len(info_kws) > 0    else "노트북 발열 원인", "info"),
        (revenue_kws[1] if len(revenue_kws) > 1 else revenue_kws[0] if revenue_kws else "노트북 추천", "revenue"),
    ]
    logger.info("=== IT 포스트 생성 시작 ===")
    logger.info("  수익형: %s", revenue_kws)
    logger.info("  정보형: %s", info_kws)

    results = []
    for i, (keyword, post_type) in enumerate(keyword_plan, 1):
        logger.info("[%d/3] 키워드: %s (%s)", i, keyword, post_type)

        # 중복 체크
        if check_title_duplicate(keyword):
            logger.warning("중복 키워드 스킵: %s", keyword)
            continue

        # 쿠팡 상품 (수익형만)
        products = search_coupang_products(keyword) if post_type == "revenue" else []
        logger.info("쿠팡 상품: %d개", len(products))

        # 콘텐츠 생성
        data = generate_content(keyword, products, post_type=post_type)
        if not data:
            logger.error("콘텐츠 생성 실패: %s", keyword)
            continue

        title = data.get("title", keyword)

        # HTML 생성
        html = build_full_html(data, keyword, products, today, post_index=i, post_type=post_type)
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
