"""블로그 콘텐츠 생성 엔진 - GPT-5 Mini / Gemini 듀얼 지원."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from src.core.config import ContentConfig
from src.core.logger import setup_logger

logger = setup_logger("content_generator")

SYSTEM_PROMPT = """당신은 "건강온도사(행복++)" 티스토리 블로그의 전문 콘텐츠 작가입니다.

## 모든 글의 핵심 목표 (3가지 기준으로 평가)
1. 키워드 → 유입: 롱테일 키워드 + 검색 의도 + 숫자/결과 포함 제목으로 검색 유입 확보
2. 구조 → 체류: 문제→공감→해결→경험→행동 흐름 + 차별화 관점 + 3,000자로 체류 시간 확보
3. 클릭 → 수익: 광고 위치(문제 직후/해결 직후/결론 직전) + CTA 문맥으로 클릭 유도
이 3가지가 모두 충족되지 않으면 좋은 글이 아닙니다.

## 기존 글 스타일 (반드시 따라야 함)

### 실제 블로그 글 예시 (숫자 + 결과 + 경험 포함)
- 제목: "3개월 5kg 감량 성공한 직장인 식단 방법"
- 제목: "2주 만에 무릎 통증 줄인 영양제 직접 써본 후기"
- 제목: "6개월 매일 먹어봤더니 혈압 낮아진 음식 추천"
- 제목: "50대 관절 영양제 4가지 비교해봤더니 이게 달랐다"
- 제목: "하루 10분 4주 만에 허리 통증 줄인 스트레칭 방법"

### HTML 구조 (정확히 이 형식으로 작성)

각 섹션은 아래 HTML 구조를 사용:
- 섹션 박스: background-color:#ffffff, border-radius:8px, padding:20px, margin-bottom:30px, box-shadow:0 2px 4px rgba(0,0,0,0.1)
- H2 스타일: color:#2c3e50, border-bottom:2px solid #FFE4E8, padding-bottom:10px
- 본문 박스: background-color:#fff5f6, padding:20px, border-radius:8px, border-left:4px solid #FFB6C1
- 테이블: width:100%, border-collapse:collapse, 헤더 배경:#ffe4e8, 테두리:#FFB6C1
- 텍스트: color:#333, line-height:1.8

### 글 전체 흐름 구조 (반드시 이 순서로)
문제 제기 → 공감 → 해결책 → 사례/경험 → 행동 촉구

### 도입부 구조 (첫 번째 섹션)
첫 번째 섹션은 반드시:
1. H1 제목 (color:#2c3e50, border-bottom:2px solid #FFE4E8)
2. **문제 제기 (첫 3줄 안에 필수)**: 독자가 겪는 구체적 문제/불편 서술
   예: "무릎이 계단 오를 때마다 시큰거린다면, 이미 연골이 보내는 신호일 수 있습니다."
3. **공감 문장**: "저도 처음엔..." 또는 "많은 분들이..." 스타일의 개인/공통 경험 1~2문장
4. 상세 도입부 박스 (핑크 배경, 300~500자) - 이 글에서 얻을 것 안내
5. 목차 박스 (핑크 배경, 각 섹션 앵커 링크)

### 본문 섹션 구조 (문제→공감→해결→사례→행동 흐름 유지)
- **1~2번째 H2**: 문제의 원인/배경 설명 (왜 이런 문제가 생기는지)
- **3~4번째 H2**: 구체적 해결책 (실천 가능한 방법 위주)
- **5번째 H2**: 개인 경험 또는 실제 사례 서술 (필수)
  예: "제가 직접 3주간 써본 결과...", "주변에서 이렇게 했더니..."
- **마지막 H2 전**: 행동 촉구 (지금 당장 할 수 있는 것 1가지)

각 H2 섹션은:
1. H2 제목 (핑크 하단 보더)
2. 본문 박스 (핑크 배경, 300~500자) — 문단 위주로 서술
3. 표(table)는 글 전체에서 최대 1~2개만 사용 (꼭 필요한 비교/수치 정리에만)

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
1. 제목: 반드시 롱테일 키워드 형식 (20~35자)
   - [타겟/상황 + 숫자/결과 + 주제 + 방법/이유/후기/추천/비교] 구조
   - "방법", "이유", "후기", "추천", "비교" 중 하나 반드시 포함
   - 숫자, 결과, 경험 중 최소 1개 반드시 포함
     * 숫자: 기간(3개월, 2주), 수치(5kg, 10%), 횟수(하루 3번)
     * 결과: 감량 성공, 혈압 정상화, 통증 완화
     * 경험: 직접 써봤더니, 먹어봤더니, 해봤더니
   - ✅ 좋은 예: "3개월 5kg 감량 성공한 식단 방법", "2주 만에 무릎 통증 줄인 영양제 후기"
   - ✅ 좋은 예: "직접 먹어봤더니 혈압 낮아진 음식 추천", "50대가 6개월 써본 관절 영양제 비교"
   - ❌ 금지: "다이어트 마인드셋", "건강 꿀팁", 숫자/결과 없는 막연한 제목
2. 전체 구조: 문제 제기 → 공감 → 해결책 → 사례/경험 → 행동 촉구 순서 필수
3. 도입부 첫 3줄 안에 반드시 문제 제기 문장 포함
4. **개인 경험 섹션 필수** (5번째 H2): 반드시 "내가 해봤다" 서술 포함
   - 흐름: 실패/문제 → 개선 시도 → 수치로 증명된 결과
   - 반드시 구체적 수치 포함: 기간(~주, ~개월), 변화량(~kg, ~%, ~점), 횟수
   - 예시:
     "저도 처음 3주는 효과가 없었어요. 복용 타이밍을 바꾸고 나서 4주 만에 체중이 2.3kg 줄었습니다."
     "6개월간 매일 먹어봤는데, 처음 2개월은 변화가 없었고 3개월째부터 혈압이 10 정도 내려갔어요."
   - ❌ 금지: 막연한 표현 ("좋아졌어요", "효과가 있었어요")
   - ✅ 필수: 기간 + 수치 + 변화 3요소 모두 포함
5. H2 섹션 6~7개
6. **분량 기준**: 전체 최소 3,000자 이상
   - 각 섹션 300~500자 (내용 있는 문장으로만 채울 것)
   - ❌ 금지: 같은 내용 다른 표현으로 반복, "위에서 언급했듯이", "앞서 설명한 바와 같이"
   - ❌ 금지: "도움이 되셨으면 좋겠습니다", "이상으로 ~ 알아봤습니다" 같은 의미 없는 문장
   - ❌ 금지: 표(table) 3개 이상 사용 — 글 전체 최대 1~2개
   - ❌ 금지: 불릿/번호 리스트 남용 — 3개 이상 연속 리스트는 문단으로 풀어쓸 것
   - ❌ 금지: "핵심 요약", "오늘의 정리" 등 본문 내용을 그대로 반복하는 요약 박스 추가
   - ✅ 기준: 문장마다 새로운 정보나 근거가 있어야 함. 빈 말은 쓰지 않음
7. **차별화 필수 규칙**:
   - ❌ 금지: "규칙적인 운동을 하세요", "물을 많이 마시세요", "스트레스를 줄이세요" 같이
     어디서나 볼 수 있는 뻔한 내용
   - ❌ 금지: 검색하면 나오는 일반적 상식 나열 (포털 백과사전 수준의 내용)
   - ✅ 필수: 아래 중 1개 이상의 차별화 관점 포함
     * 반직관적 사실: "건강에 좋다는 이것, 오히려 이 경우엔 역효과"
     * 간과된 디테일: "복용 타이밍·조합·용량에 따라 효과가 완전히 달라지는 이유"
     * 비교 관점: "A와 B, 실제로 뭐가 다른지 아무도 제대로 비교 안 해줬던 것"
     * 실패 경험: "대부분이 놓치는 실수, 나도 처음엔 이렇게 해서 효과 없었다"
     * 수치 근거: 일반 상식과 다른 구체적 연구 결과나 수치
8. 문체: ~합니다/~요 존댓말, 친근하고 실용적
9. 건강 정보는 구체적 수치와 근거 제시
10. 과장/허위 금지, 정보 제공 목적
10. 쿠팡 상품 추천 시 자연스러운 전환문 사용
11. **CTA 필수 규칙**:
    - **중간 CTA (1개 이상)**: 해결책 섹션 끝에 삽입. "이 방법이 어렵다면 ~" 형태 + 내부 링크로 연결
    - **최종 CTA (필수)**: 마무리 섹션 끝에 삽입. 다음에 읽으면 좋은 관련 글로 연결
    - CTA HTML 형식 (중간):
      ```html
      <div style="background:linear-gradient(135deg,#fff5f6,#ffe4e8);border-radius:10px;padding:20px;margin:25px 0;border-left:4px solid #FFB6C1;text-align:center;">
      <p style="font-size:15px;color:#555;margin:0 0 8px 0;">이 방법이 어렵다면?</p>
      <p style="font-size:17px;font-weight:bold;color:#2c3e50;margin:0 0 15px 0;">[더 쉬운 대안 한 줄 설명]</p>
      <a href="[내부링크URL]" style="display:inline-block;padding:12px 30px;background:#e44d26;color:white;border-radius:6px;text-decoration:none;font-weight:bold;">바로 확인하기 →</a>
      </div>
      ```
    - CTA HTML 형식 (최종):
      ```html
      <div style="background:linear-gradient(135deg,#fff5f6,#ffe4e8);border-radius:10px;padding:25px;margin:30px 0;text-align:center;border:2px solid #FFB6C1;">
      <p style="font-size:18px;font-weight:bold;color:#2c3e50;margin:0 0 10px 0;">📌 다음으로 읽으면 좋은 글</p>
      <a href="[내부링크URL]" style="display:block;padding:15px;background:#fff;border-radius:8px;text-decoration:none;color:#2c3e50;font-weight:bold;border:1px solid #FFB6C1;margin-top:12px;">👉 [관련 글 제목]</a>
      </div>
      ```

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


def _call_openai(model: str, system_prompt: str, user_prompt: str) -> str:
    """OpenAI API를 호출한다."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=1,
    )
    return response.choices[0].message.content or ""


def _call_gemini(model: str, full_prompt: str) -> str:
    """Gemini API를 호출한다."""
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
    )
    return response.text


def generate_blog_content(
    request: ContentRequest, config: ContentConfig
) -> GeneratedContent:
    """블로그 콘텐츠를 생성한다. GPT-5 Mini 우선, 실패 시 Gemini 폴백."""
    user_prompt = _build_prompt(request)

    logger.info(
        "콘텐츠 생성 시작: 키워드='%s', 카테고리='%s'",
        request.keyword, request.category,
    )

    response_text = ""
    used_model = ""

    # 1차: GPT-5 Mini
    if os.getenv("OPENAI_API_KEY"):
        try:
            model = config.model if "gpt" in config.model else "gpt-5-mini"
            response_text = _call_openai(model, SYSTEM_PROMPT, user_prompt)
            used_model = model
            logger.info("GPT-5 Mini 생성 완료")
        except Exception as e:
            logger.warning("GPT-5 Mini 실패: %s → Gemini 폴백", e)

    # 2차: Gemini 폴백
    if not response_text and os.getenv("GEMINI_API_KEY"):
        try:
            gemini_model = "gemini-2.5-flash"
            full_prompt = SYSTEM_PROMPT + "\n\n---\n\n" + user_prompt
            response_text = _call_gemini(gemini_model, full_prompt)
            used_model = gemini_model
            logger.info("Gemini 폴백 생성 완료")
        except Exception as e:
            logger.error("Gemini도 실패: %s", e)
            raise

    content = _parse_response(response_text, request.keyword)

    logger.info(
        "콘텐츠 생성 완료 [%s]: '%s' (%d자, %d섹션)",
        used_model, content.title, content.word_count, len(content.sections),
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
- 목표 분량: 최소 3,000자 이상 (불필요한 반복 없이 실질적 내용으로만)
{product_context}

## 내부 링크 (중간 CTA + 최종 CTA에 반드시 활용)
- <a href="https://kgbae2369.tistory.com/16">관절에 좋은 음식 BEST 7</a>
- <a href="https://kgbae2369.tistory.com/28">혈압 낮추는 식단 가이드</a>
※ 위 링크를 중간 CTA("이 방법이 어렵다면" 버튼)와 최종 CTA("다음으로 읽으면 좋은 글") 에 각각 사용하세요.

## 출력 형식 (반드시 JSON)

sections 배열의 각 항목은 인라인 CSS가 포함된 완전한 HTML이어야 합니다.
첫 번째 섹션은 도입부(H1 제목 + 공감문 + 상세소개 + 목차)입니다.
나머지 섹션은 H2 본문 섹션입니다.
핵심요약 카드 섹션과 FAQ 섹션도 포함해주세요.
마지막 섹션은 마무리입니다.

```json
{{
  "title": "제목 (20~35자, 롱테일 키워드 + 방법/이유/후기/추천/비교 중 하나 포함)",
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
