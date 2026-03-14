"""Google Gemini API 기반 블로그 콘텐츠 생성 엔진."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from google import genai

from src.core.config import ContentConfig
from src.core.logger import setup_logger

logger = setup_logger("content_generator")

SYSTEM_PROMPT = """당신은 "건강온도사(행복++)" 블로그의 전문 콘텐츠 작가입니다.

## 작성 규칙
- 대상 독자: 건강과 생활에 관심 있는 20~60대 한국인
- 톤: 친근하고 전문적인 (존댓말 사용)
- 브랜딩: "건강온도사"로서 신뢰감 있는 정보 전달
- 건강 정보는 근거 기반으로 작성, 과장/허위 금지
- 의학적 조언 대신 정보 제공 목적임을 명시

## 콘텐츠 구조
1. 도입부: 독자 공감 + 글의 가치 소개 (200~300자)
2. 본문: H2 5~8개, 각 H2 아래 H3 1~2개로 세분화, 각 섹션 300~500자
3. 결론: 핵심 요약 + 행동 촉구 + "함께 읽으면 좋은 글" 추천 (200~300자)

## SEO 규칙
- 포커스 키워드를 제목 앞부분, 도입부 첫 문단, H2 1개 이상에 포함
- 메타 설명 155자 이내, CTA 포함
- 키워드 밀도 1~2% 유지
- 제목은 40~60자, 숫자/리스트형 선호 ("~하는 5가지 방법")
- 각 H2 섹션에 불릿 포인트 또는 번호 리스트 최소 1개 포함
- 건강 정보는 구체적 수치와 근거 제시 (예: "1일 권장량 1000IU")

## 수익화 통합
- 쿠팡 상품 추천 시 자연스러운 전환문 사용 ("이런 분들에게 도움이 될 수 있어요")
- 과도한 상업적 표현 지양, 정보 제공 중심"""


@dataclass
class GeneratedContent:
    """생성된 콘텐츠 데이터."""

    title: str
    meta_description: str
    sections: list[dict[str, str]]  # [{"heading": "H2 제목", "content": "본문"}]
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
이 상품들을 본문에서 자연스럽게 추천해주세요. (2번째, 4번째 섹션 뒤에 배치 예정)"""

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

## 출력 형식 (반드시 JSON으로)
```json
{{
  "title": "포스트 제목 (40~60자, 키워드 포함)",
  "meta_description": "메타 설명 (155자 이내)",
  "sections": [
    {{"heading": "H2 섹션 제목", "content": "섹션 본문 (HTML 태그 사용 가능)"}},
    ...
  ],
  "tags": ["태그1", "태그2", ...],
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
