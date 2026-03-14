"""콘텐츠 생성 엔진 테스트."""

from __future__ import annotations

import json

import pytest

from src.content.generator import (
    ContentRequest,
    GeneratedContent,
    _build_prompt,
    _parse_response,
)
from src.content.seo_optimizer import SEOScore, analyze_seo, optimize_content
from src.content.trend_analyzer import (
    generate_weekly_topics,
    get_seasonal_keywords,
    get_upcoming_keywords,
)


@pytest.fixture
def sample_content() -> GeneratedContent:
    return GeneratedContent(
        title="비타민D 효능 5가지, 전문가가 추천하는 복용법",
        meta_description="비타민D의 놀라운 효능 5가지와 올바른 복용법을 건강온도사가 알려드립니다.",
        sections=[
            {"heading": "비타민D란 무엇인가요?", "content": "비타민D는 " + "중요한 영양소입니다. " * 30},
            {"heading": "비타민D 효능 첫 번째: 뼈 건강", "content": "비타민D는 칼슘 흡수를 돕습니다. " * 25},
            {"heading": "비타민D 효능 두 번째: 면역력", "content": "면역 체계를 강화합니다. " * 25},
            {"heading": "비타민D 효능 세 번째: 기분 개선", "content": "세로토닌 생성에 관여합니다. " * 25},
            {"heading": "비타민D 효능 네 번째: 근력 유지", "content": "근육 기능을 지원합니다. " * 25},
            {"heading": "올바른 비타민D 복용법", "content": "하루 권장량은 " + "1000~2000IU입니다. " * 20},
        ],
        tags=["비타민D", "비타민D 효능", "건강", "영양제", "면역력"],
        focus_keyword="비타민D 효능",
        word_count=2000,
    )


class TestContentRequest:
    def test_build_prompt(self) -> None:
        request = ContentRequest(
            keyword="비타민D 효능",
            category="건강정보",
            secondary_keywords=["비타민D 복용법", "비타민D 추천"],
            product_names=["종근당 비타민D 3000IU"],
        )
        prompt = _build_prompt(request)
        assert "비타민D 효능" in prompt
        assert "건강정보" in prompt
        assert "종근당 비타민D 3000IU" in prompt
        assert "JSON" in prompt

    def test_build_prompt_minimal(self) -> None:
        request = ContentRequest(keyword="건강 팁")
        prompt = _build_prompt(request)
        assert "건강 팁" in prompt


class TestParseResponse:
    def test_parse_valid_json(self) -> None:
        response = json.dumps({
            "title": "테스트 제목",
            "meta_description": "테스트 설명",
            "sections": [{"heading": "섹션1", "content": "내용입니다"}],
            "tags": ["태그1"],
            "focus_keyword": "테스트",
        })
        content = _parse_response(f"```json\n{response}\n```", "테스트")
        assert content.title == "테스트 제목"
        assert len(content.sections) == 1

    def test_parse_invalid_json(self) -> None:
        content = _parse_response("이것은 JSON이 아닙니다", "테스트")
        assert "테스트" in content.title
        assert len(content.sections) > 0


class TestSEOOptimizer:
    def test_analyze_seo_good_content(self, sample_content: GeneratedContent) -> None:
        score = analyze_seo(sample_content)
        assert isinstance(score, SEOScore)
        assert 0 <= score.total <= 100
        assert score.title_score >= 0
        assert score.meta_score >= 0

    def test_analyze_seo_bad_content(self) -> None:
        bad_content = GeneratedContent(
            title="짧음",
            meta_description="",
            sections=[],
            tags=[],
            focus_keyword="키워드",
            word_count=100,
        )
        score = analyze_seo(bad_content)
        assert score.total < 50
        assert len(score.issues) > 0

    def test_optimize_meta_length(self, sample_content: GeneratedContent) -> None:
        sample_content.meta_description = "x" * 200
        optimized = optimize_content(sample_content)
        assert len(optimized.meta_description) <= 155

    def test_optimize_adds_keyword_to_tags(self) -> None:
        content = GeneratedContent(
            title="제목",
            meta_description="설명",
            sections=[],
            tags=["태그1"],
            focus_keyword="키워드",
            word_count=500,
        )
        optimized = optimize_content(content)
        assert "키워드" in optimized.tags


class TestTrendAnalyzer:
    def test_get_seasonal_keywords(self) -> None:
        keywords = get_seasonal_keywords(3)  # 3월
        assert "건강" in keywords
        assert "뷰티" in keywords
        assert "생활" in keywords
        assert len(keywords["건강"]) > 0

    def test_get_upcoming_keywords(self) -> None:
        keywords = get_upcoming_keywords(12)  # 12월 → 1월
        assert "건강" in keywords

    def test_generate_weekly_topics(self) -> None:
        topics = generate_weekly_topics(3)
        assert len(topics) == 7
        assert all("day" in t for t in topics)
        assert all("keyword" in t for t in topics)
