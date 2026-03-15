"""HTML 템플릿 엔진 - Jinja2 기반 블로그 포스트 렌더링."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.core.logger import setup_logger

logger = setup_logger("template")

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"


def _create_env() -> Environment:
    """Jinja2 환경을 생성한다."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )


def render_blog_post(
    title: str,
    sections: list[dict[str, str]],
    product_widgets: list[str],
    ad_slots: list[str],
    disclaimer: str,
    meta_description: str = "",
    tags: list[str] | None = None,
    publish_date: str = "",
    faq_items: list[dict[str, str]] | None = None,
) -> str:
    """블로그 포스트 HTML을 렌더링한다."""
    env = _create_env()
    template = env.get_template("blog_post.html")
    return template.render(
        title=title,
        sections=sections,
        product_widgets=product_widgets,
        ad_slots=ad_slots,
        disclaimer=disclaimer,
        meta_description=meta_description,
        tags=tags or [],
        publish_date=publish_date,
        faq_items=faq_items or [],
    )


def render_product_review(
    title: str,
    intro: str,
    products: list[dict],
    conclusion: str,
    ad_slots: list[str],
    disclaimer: str,
) -> str:
    """상품 리뷰 포스트 HTML을 렌더링한다."""
    env = _create_env()
    template = env.get_template("product_review.html")
    return template.render(
        title=title,
        intro=intro,
        products=products,
        conclusion=conclusion,
        ad_slots=ad_slots,
        disclaimer=disclaimer,
    )
