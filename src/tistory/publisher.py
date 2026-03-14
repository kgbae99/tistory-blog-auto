"""티스토리 글 발행 자동화 (Playwright 기반)."""

from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import BrowserContext, Page

from src.core.config import TistoryConfig
from src.core.logger import setup_logger
from src.tistory.auth import ensure_logged_in, save_session

logger = setup_logger("tistory_publisher")


@dataclass
class PostData:
    """발행할 포스트 데이터."""

    title: str
    content_html: str
    category: str = ""
    tags: list[str] | None = None
    visibility: str = "public"  # public, protected, private


async def publish_post(context: BrowserContext, config: TistoryConfig,
                       post: PostData) -> str | None:
    """티스토리에 새 포스트를 발행한다. 발행된 URL을 반환한다."""
    page = await context.new_page()

    try:
        # 로그인 확인
        if not await ensure_logged_in(page, config):
            logger.error("로그인 실패로 발행 중단")
            return None

        # 글쓰기 페이지로 이동
        write_url = f"{config.blog_url}/manage/newpost"
        await page.goto(write_url)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # HTML 모드 전환
        await _switch_to_html_mode(page)

        # 제목 입력
        title_input = page.locator("#post-title-inp")
        await title_input.click()
        await title_input.fill(post.title)
        logger.info("제목 입력 완료: %s", post.title)

        # 본문 입력 (HTML 모드)
        await _insert_html_content(page, post.content_html)
        logger.info("본문 입력 완료 (%d자)", len(post.content_html))

        # 카테고리 설정
        if post.category:
            await _set_category(page, post.category)

        # 태그 설정
        if post.tags:
            await _set_tags(page, post.tags)

        # 발행
        published_url = await _click_publish(page, post.visibility)
        await save_session(context)

        logger.info("포스트 발행 완료: %s", published_url)
        return published_url

    except Exception as e:
        logger.error("포스트 발행 실패: %s", e)
        return None
    finally:
        await page.close()


async def _switch_to_html_mode(page: Page) -> None:
    """에디터를 HTML 모드로 전환한다."""
    html_btn = page.locator("button.btn_html, [data-mode='html']")
    if await html_btn.count() > 0:
        await html_btn.click()
        await page.wait_for_timeout(500)
        logger.info("HTML 모드 전환 완료")


async def _insert_html_content(page: Page, html: str) -> None:
    """HTML 콘텐츠를 에디터에 삽입한다."""
    # CodeMirror 에디터 또는 textarea에 입력
    editor = page.locator(".CodeMirror, textarea.html")
    if await editor.count() > 0:
        # CodeMirror인 경우
        await page.evaluate(
            """(html) => {
                const cm = document.querySelector('.CodeMirror');
                if (cm && cm.CodeMirror) {
                    cm.CodeMirror.setValue(html);
                } else {
                    const textarea = document.querySelector('textarea.html');
                    if (textarea) {
                        textarea.value = html;
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            }""",
            html,
        )
    else:
        # 기본 contenteditable 에디터
        content_frame = page.frame_locator("#content-editor-iframe")
        body = content_frame.locator("body")
        await body.evaluate("(el, html) => el.innerHTML = html", html)

    await page.wait_for_timeout(500)


async def _set_category(page: Page, category: str) -> None:
    """카테고리를 설정한다."""
    category_btn = page.locator("#category-btn, .btn_category")
    if await category_btn.count() > 0:
        await category_btn.click()
        await page.wait_for_timeout(300)

        category_option = page.locator(f"text={category}").first
        if await category_option.count() > 0:
            await category_option.click()
            logger.info("카테고리 설정: %s", category)
        else:
            logger.warning("카테고리 '%s'를 찾을 수 없음", category)


async def _set_tags(page: Page, tags: list[str]) -> None:
    """태그를 설정한다."""
    tag_input = page.locator("#tagText, input.tag-input")
    if await tag_input.count() > 0:
        for tag in tags:
            await tag_input.fill(tag)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)
        logger.info("태그 설정: %s", ", ".join(tags))


async def _click_publish(page: Page, visibility: str) -> str | None:
    """발행 버튼을 클릭하고 발행된 URL을 반환한다."""
    # 공개 설정
    if visibility == "public":
        public_radio = page.locator("input[value='20'], label:has-text('공개')")
        if await public_radio.count() > 0:
            await public_radio.click()

    # 발행 버튼 클릭
    publish_btn = page.locator(
        "button#publish-layer-btn, button:has-text('발행'), button:has-text('완료')"
    )
    if await publish_btn.count() > 0:
        await publish_btn.click()
        await page.wait_for_timeout(3000)
        await page.wait_for_load_state("networkidle")

    # 발행된 URL 추출
    current_url = page.url
    if "/manage/" not in current_url:
        return current_url

    # 최근 포스트 URL 확인
    return current_url
