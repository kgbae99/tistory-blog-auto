"""Google Gemini API 기반 블로그 콘텐츠 생성 엔진."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from google import genai

from src.core.config import ContentConfig
from src.core.logger import setup_logger

logger = setup_logger("content_generator")

SYSTEM_PROMPT = """당신은 "건강온도사(행복++)" 티스토리 블로그의 전문 콘텐츠 작가입니다.

## 기존 글 스타일 (반드시 따라야 함)

### 실제 블로그 글 예시
- 제목: "아침 공복에 좋은 음식, 따로 있습니다"
- 제목: "뼈가 약해졌다면 지금 꼭 챙기세요"
- 제목: "간을 망치는 음식, 혹시 매일 드시나요?"
- 제목: "1일 1식단, 이걸로 건강 지켜냅니다"

### HTML 구조 (정확히 이 형식으로 작성)

각 섹션은 아래 HTML 구조를 사용:
- 섹션 박스: background-color:#ffffff, border-radius:8px, padding:20px, margin-bottom:30px, box-shadow:0 2px 4px rgba(0,0,0,0.1)
- H2 스타일: color:#2c3e50, border-bottom:2px solid #FFE4E8, padding-bottom:10px
- 본문 박스: background-color:#fff5f6, padding:20px, border-radius:8px, border-left:4px solid #FFB6C1
- 테이블: width:100%, border-collapse:collapse, 헤더 배경:#ffe4e8, 테두리:#FFB6C1
- 텍스트: color:#333, line-height:1.8

### 도입부 구조
첫 번째 섹션은 반드시:
1. H1 제목 (color:#2c3e50, border-bottom:2px solid #FFE4E8)
2. 독자 공감 짧은 문장 (1~2문장, "혹시 이런 적 있으시죠?" 스타일)
3. 상세 도입부 박스 (핑크 배경, 200~300자)
4. 목차 박스 (핑크 배경, 각 섹션 앵커 링크)

### 본문 섹션 구조
각 H2 섹션은:
1. H2 제목 (핑크 하단 보더)
2. 표(table) 또는 리스트로 핵심 정보 요약
3. 본문 박스 (핑크 배경, 150~300자)

### 핵심 요약 카드
- 5개 카드를 flexbox로 배치
- 각 카드: 다른 파스텔 색상 (ffebee, fce4ec, f3e5f5, e1f5fe, e8f5e9)
- H3 제목 + 한 줄 설명

### FAQ 섹션
- 3개 질문/답변 카드
- 각 카드: 핑크 그라데이션 배경 (FAE3E3, FDE2E2, FCE5E5)

### 마무리 섹션
- 핵심 요약 + 행동 촉구
- 태그 목록 (6~7개)

## 글쓰기 규칙
1. 제목: 짧고 강렬한 호기심 유발형 (15~30자)
2. H2 섹션 6~7개
3. 각 섹션 150~300자, 짧은 문단
4. 문체: ~합니다/~요 존댓말, 친근하고 실용적
5. 건강 정보는 구체적 수치와 근거 제시
6. 과장/허위 금지, 정보 제공 목적
7. 쿠팡 상품 추천 시 자연스러운 전환문 사용

## 수익화 통합
- 쿠팡 상품 추천 시 자연스러운 전환문 사용 ("이런 분들에게 도움이 될 수 있어요")
- 과도한 상업적 표현 지양"""


@dataclass
class GeneratedContent:
    """생성된 콘텐츠 데이터."""

    title: str
    meta_description: str
    sections: list[dict[str, str]]
    tags: list[str]
    focus_keyword: str
    word_count: int


@dataclass
class ContentRequest:
    """콘텐츠 생성 요청."""

    keyword: str
    category: str = "건강정보"
    secondary_keywords: list[str] = field(default_factory=list)
    product_names: list[str] = field(default_factory=list)


def generate_blog_content(
    request: ContentRequest, config: ContentConfig
) -> GeneratedContent:
    """Google Gemini API를 사용하여 블로그 콘텐츠를 생성한다."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    user_prompt = _build_prompt(request)
    full_prompt = SYSTEM_PROMPT + "\n\n---\n\n" + user_prompt

    logger.info(
        "콘텐츠 생성 시작: 키워드='%s', 카테고리='%s'",
        request.keyword, request.category,
    )

    response = client.models.generate_content(
        model=config.model,
        contents=full_prompt,
    )

    response_text = response.text
    content = _parse_response(response_text, request.keyword)

    logger.info(
        "콘텐츠 생성 완료: '%s' (%d자, %d섹션)",
        content.title, content.word_count, len(content.sections),
    )
    return content


def _build_prompt(request: ContentRequest) -> str:
    """Gemini에게 보낼 프롬프트를 생성한다."""
    product_context = ""
    if request.product_names:
        products_list = "\n".join(
            f"- {name}" for name in request.product_names
        )
        product_context = f"""

## 쿠팡 추천 상품 (자연스럽게 언급)
{products_list}
이 상품들을 본문에서 자연스럽게 추천해주세요."""

    secondary = ""
    if request.secondary_keywords:
        secondary = (
            f"\n보조 키워드: {', '.join(request.secondary_keywords)}"
        )

    return f"""다음 주제로 블로그 포스트를 작성해주세요.

## 요청
- 포커스 키워드: {request.keyword}{secondary}
- 카테고리: {request.category}
- 목표 분량: 1,500~3,000자
{product_context}

## 내부 링크 (본문 중간에 자연스럽게 2개 삽입)
- <a href="https://kgbae2369.tistory.com/16">관절에 좋은 음식 BEST 7</a>
- <a href="https://kgbae2369.tistory.com/28">혈압 낮추는 식단 가이드</a>

## 출력 형식 (반드시 JSON)

sections 배열의 각 항목은 인라인 CSS가 포함된 완전한 HTML이어야 합니다.
첫 번째 섹션은 도입부(H1 제목 + 공감문 + 상세소개 + 목차)입니다.
나머지 섹션은 H2 본문 섹션입니다.
핵심요약 카드 섹션과 FAQ 섹션도 포함해주세요.
마지막 섹션은 마무리입니다.

```json
{{
  "title": "제목 (15~30자, 호기심 유발형)",
  "meta_description": "메타 설명 (155자 이내, CTA 포함)",
  "sections": [
    {{"heading": "도입부", "content": "<div id='section1' class='content-section' style='...'>H1 제목 + 공감문 + 소개 + 목차 HTML</div>"}},
    {{"heading": "섹션제목1", "content": "<div id='sec1' class='topic-section' style='...'>H2 + 테이블 + 본문박스 HTML</div>"}},
    {{"heading": "섹션제목2", "content": "..."}},
    {{"heading": "핵심 요약", "content": "<div style='...'>5개 카드 flexbox HTML</div>"}},
    {{"heading": "자주 묻는 질문", "content": "<div style='...'>FAQ 3개 카드 HTML</div>"}},
    {{"heading": "마무리", "content": "<div style='...'>결론 + 태그 HTML</div>"}}
  ],
  "tags": ["태그1", "태그2", ...6~7개],
  "focus_keyword": "{request.keyword}"
}}
```

JSON 코드블록만 출력하세요. 다른 텍스트는 포함하지 마세요."""


def _parse_response(response: str, keyword: str) -> GeneratedContent:
    """AI 응답을 파싱하여 GeneratedContent를 생성한다."""
    json_str = response
    if "```json" in response:
        json_str = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        json_str = response.split("```")[1].split("```")[0]

    try:
        data = json.loads(json_str.strip())
    except json.JSONDecodeError:
        logger.warning("JSON 파싱 실패, 기본 구조로 대체")
        data = {
            "title": f"{keyword} - 건강온도사가 알려드리는 꿀팁",
            "meta_description": (
                f"{keyword}에 대해 건강온도사가 쉽고 정확하게 알려드립니다."
            ),
            "sections": [{"heading": keyword, "content": response}],
            "tags": [keyword],
            "focus_keyword": keyword,
        }

    total_text = " ".join(
        s.get("content", "") for s in data.get("sections", [])
    )
    word_count = len(total_text)

    return GeneratedContent(
        title=data.get("title", ""),
        meta_description=data.get("meta_description", ""),
        sections=data.get("sections", []),
        tags=data.get("tags", []),
        focus_keyword=data.get("focus_keyword", keyword),
        word_count=word_count,
    )
