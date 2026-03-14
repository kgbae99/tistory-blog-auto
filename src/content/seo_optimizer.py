"""SEO 최적화 모듈."""

from __future__ import annotations

from dataclasses import dataclass

from src.content.generator import GeneratedContent
from src.core.logger import setup_logger

logger = setup_logger("seo_optimizer")


@dataclass
class SEOScore:
    """SEO 점수 결과."""

    total: int
    title_score: int
    meta_score: int
    heading_score: int
    content_score: int
    keyword_score: int
    issues: list[str]
    suggestions: list[str]


def analyze_seo(content: GeneratedContent) -> SEOScore:
    """콘텐츠의 SEO 상태를 분석하고 점수를 매긴다."""
    issues = []
    suggestions = []
    title_score = _check_title(content, issues, suggestions)
    meta_score = _check_meta(content, issues, suggestions)
    heading_score = _check_headings(content, issues, suggestions)
    content_score = _check_content(content, issues, suggestions)
    keyword_score = _check_keyword_density(content, issues, suggestions)

    total = title_score + meta_score + heading_score + content_score + keyword_score

    logger.info("SEO 분석 완료: %d/100점, %d개 이슈", total, len(issues))
    return SEOScore(
        total=total,
        title_score=title_score,
        meta_score=meta_score,
        heading_score=heading_score,
        content_score=content_score,
        keyword_score=keyword_score,
        issues=issues,
        suggestions=suggestions,
    )


def _check_title(content: GeneratedContent, issues: list, suggestions: list) -> int:
    """제목 SEO 점수 (최대 20점)."""
    score = 0
    title = content.title
    keyword = content.focus_keyword

    if keyword.lower() in title.lower():
        score += 8
    else:
        issues.append("제목에 포커스 키워드가 포함되지 않음")

    title_len = len(title)
    if 30 <= title_len <= 60:
        score += 7
    elif 20 <= title_len <= 70:
        score += 4
        suggestions.append(f"제목 길이 조정 권장 (현재 {title_len}자, 권장 30~60자)")
    else:
        issues.append(f"제목 길이 부적절 ({title_len}자)")

    if any(c.isdigit() for c in title) or any(w in title for w in ["방법", "추천", "TOP", "비교"]):
        score += 5
    else:
        suggestions.append("제목에 숫자나 액션 키워드 추가 고려")

    return score


def _check_meta(content: GeneratedContent, issues: list, suggestions: list) -> int:
    """메타 설명 점수 (최대 20점)."""
    score = 0
    meta = content.meta_description

    if not meta:
        issues.append("메타 설명이 없음")
        return 0

    if len(meta) <= 155:
        score += 8
    else:
        issues.append(f"메타 설명이 너무 김 ({len(meta)}자, 최대 155자)")

    if content.focus_keyword.lower() in meta.lower():
        score += 7
    else:
        suggestions.append("메타 설명에 포커스 키워드 포함 권장")

    if len(meta) >= 80:
        score += 5
    else:
        suggestions.append("메타 설명을 80자 이상으로 확장 권장")

    return score


def _check_headings(content: GeneratedContent, issues: list, suggestions: list) -> int:
    """헤딩 구조 점수 (최대 20점)."""
    score = 0
    sections = content.sections
    num_sections = len(sections)

    if 5 <= num_sections <= 10:
        score += 10
    elif 3 <= num_sections <= 12:
        score += 6
        suggestions.append(f"H2 섹션 수 조정 권장 (현재 {num_sections}개, 권장 5~10개)")
    else:
        issues.append(f"섹션 수 부적절 ({num_sections}개)")

    keyword_in_heading = any(
        content.focus_keyword.lower() in s.get("heading", "").lower() for s in sections
    )
    if keyword_in_heading:
        score += 10
    else:
        issues.append("H2 헤딩에 포커스 키워드가 포함되지 않음")

    return score


def _check_content(content: GeneratedContent, issues: list, suggestions: list) -> int:
    """콘텐츠 품질 점수 (최대 20점)."""
    score = 0
    word_count = content.word_count

    if word_count >= 1500:
        score += 10
    elif word_count >= 1000:
        score += 6
        suggestions.append(f"본문 길이 확장 권장 (현재 {word_count}자, 권장 1,500자 이상)")
    else:
        issues.append(f"본문이 너무 짧음 ({word_count}자)")

    # 각 섹션의 평균 길이 체크
    if content.sections:
        avg_len = word_count / len(content.sections)
        if avg_len >= 200:
            score += 10
        elif avg_len >= 100:
            score += 5
            suggestions.append("각 섹션의 내용을 더 충실하게 작성 권장")
    return score


def _check_keyword_density(content: GeneratedContent, issues: list, suggestions: list) -> int:
    """키워드 밀도 점수 (최대 20점)."""
    score = 0
    keyword = content.focus_keyword.lower()
    all_text = " ".join(s.get("content", "") + " " + s.get("heading", "") for s in content.sections)
    all_text_lower = all_text.lower()

    keyword_count = all_text_lower.count(keyword)
    text_length = len(all_text)

    if text_length > 0 and keyword:
        density = (keyword_count * len(keyword)) / text_length * 100
        if 1.0 <= density <= 3.0:
            score += 20
        elif 0.5 <= density <= 4.0:
            score += 12
            suggestions.append(f"키워드 밀도 조정 권장 (현재 {density:.1f}%, 권장 1~3%)")
        else:
            issues.append(f"키워드 밀도 부적절 ({density:.1f}%)")
            score += 4
    else:
        issues.append("키워드 밀도 측정 불가")

    return score


def optimize_content(content: GeneratedContent) -> GeneratedContent:
    """SEO 분석 결과에 따라 콘텐츠를 자동 최적화한다."""
    # 메타 설명 길이 조정
    if len(content.meta_description) > 155:
        content.meta_description = content.meta_description[:152] + "..."

    # 태그에 포커스 키워드 포함 확인
    if content.focus_keyword not in content.tags:
        content.tags.insert(0, content.focus_keyword)

    logger.info("콘텐츠 SEO 자동 최적화 완료")
    return content
