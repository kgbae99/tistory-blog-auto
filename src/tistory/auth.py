"""티스토리 카카오 계정 로그인 (Playwright 기반)."""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.core.config import TistoryConfig
from src.core.logger import setup_logger

logger = setup_logger("tistory_auth")

SESSION_DIR = Path(__file__).parent.parent.parent / ".playwright-session"


async def create_browser_context(headless: bool = True) -> tuple[Browser, BrowserContext]:
    """Playwright 브라우저 컨텍스트를 생성한다. 세션 유지를 위해 storage state 사용."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless)

    storage_path = SESSION_DIR / "state.json"
    if storage_path.exists():
        context = await browser.new_context(storage_state=str(storage_path))
        logger.info("기존 세션 상태 로드 완료")
    else:
        context = await browser.new_context()
        logger.info("새 브라우저 컨텍스트 생성")

    return browser, context


async def save_session(context: BrowserContext) -> None:
    """세션 상태를 파일로 저장한다."""
    SESSION_DIR.mkdir(exist_ok=True)
    storage_path = SESSION_DIR / "state.json"
    await context.storage_state(path=str(storage_path))
    logger.info("세션 상태 저장 완료")


async def login_kakao(page: Page, config: TistoryConfig) -> bool:
    """카카오 계정으로 티스토리에 로그인한다."""
    try:
        await page.goto("https://www.tistory.com/auth/login")
        await page.wait_for_load_state("networkidle")

        # 카카오 로그인 버튼 클릭
        kakao_btn = page.locator("a.btn_login.link_kakao_id")
        if await kakao_btn.count() > 0:
            await kakao_btn.click()
            await page.wait_for_load_state("networkidle")

        # 카카오 로그인 폼
        email_input = page.locator("input#loginId, input[name='loginId']")
        if await email_input.count() > 0:
            await email_input.fill(config.kakao_email)
            await page.locator("input#password, input[name='password']").fill(
                config.kakao_password
            )
            await page.locator("button[type='submit'], button.btn_g.btn_confirm").click()
            await page.wait_for_load_state("networkidle")

        # 로그인 성공 확인
        await page.wait_for_url("**/tistory.com/**", timeout=15000)
        logger.info("카카오 로그인 성공")
        return True

    except Exception as e:
        logger.error("카카오 로그인 실패: %s", e)
        return False


async def ensure_logged_in(page: Page, config: TistoryConfig) -> bool:
    """로그인 상태를 확인하고, 필요시 로그인을 수행한다."""
    await page.goto(f"{config.blog_url}/manage")
    await page.wait_for_load_state("networkidle")

    current_url = page.url
    if "/auth/login" in current_url or "accounts.kakao.com" in current_url:
        logger.info("로그인 필요, 카카오 로그인 시도")
        return await login_kakao(page, config)

    logger.info("이미 로그인된 상태")
    return True
