"""
티스토리 로그인 후 쿠키 저장 스크립트
실행: python scripts/save_auth_cookies.py
       python scripts/save_auth_cookies.py --blog it  (IT 블로그용)
"""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError


def safe_goto(page, url: str, wait_until: str = "domcontentloaded"):
    """
    티스토리가 로그인 직후 같은 URL로 자체 리다이렉트를 걸 때
    우리 쪽 goto와 경합하며 발생하는 'interrupted by another navigation'
    예외를 무시하고, 실제로 도착했는지 로드 상태로 확인한다.
    """
    try:
        page.goto(url, wait_until=wait_until)
    except PlaywrightError as e:
        if "interrupted by another navigation" not in str(e):
            raise
        page.wait_for_load_state(wait_until)

BLOG_CONFIGS = {
    "health": {
        "url": "https://kgbae2369.tistory.com/manage",
        "auth": r"C:\Users\CleanAdmin\Desktop\claude\blog\config\auth_blog.json",
        "name": "건강 블로그 (kgbae2369)",
    },
    "it": {
        "url": "https://uyoblog.tistory.com/manage",
        "auth": r"C:\Users\CleanAdmin\Desktop\claude\blog\config\auth_blog_it.json",
        "name": "IT 블로그 (uyoblog)",
    },
}

def save_cookies(blog_key: str):
    cfg = BLOG_CONFIGS[blog_key]
    auth_path = Path(cfg["auth"])
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  {cfg['name']} 쿠키 갱신")
    print(f"{'='*50}")
    print("1. 브라우저가 열립니다.")
    print("2. 카카오 계정으로 로그인하세요.")
    print("3. 관리 화면이 뜨면 엔터를 누르세요.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.tistory.com/auth/login", wait_until="domcontentloaded")

        # 로그인 완료를 URL 변화로 감지 (tistory.com 메인/관리 화면)
        print("로그인 화면이 열렸습니다. 카카오 계정으로 로그인하세요...")
        try:
            # tistory.com 도메인으로 돌아올 때까지 최대 3분 대기
            # auth/kakao/redirect 는 세션이 아직 확정되지 않은 콜백 중간 페이지이므로 제외
            page.wait_for_url(
                lambda url: "tistory.com" in url
                and "accounts.kakao.com" not in url
                and "auth/login" not in url
                and "auth/kakao/redirect" not in url,
                timeout=180_000
            )
            print("로그인 감지됨!")
        except Exception:
            input("자동 감지 실패 — 로그인 완료 후 엔터: ")

        # 실제 업로드에 쓰는 블로그 관리 페이지로 이동해 세션이 그 블로그에도 적용됐는지 확인
        safe_goto(page, cfg["url"], wait_until="networkidle")
        page.wait_for_timeout(1500)

        if "auth/login" in page.url or "카카오계정으로 로그인" in page.content():
            print(f"\n!! {cfg['url']} 접속 시 아직 로그인 화면입니다. 세션이 이 블로그에 적용되지 않았어요.")
            input("브라우저에서 직접 로그인/확인 후 관리 화면이 보이면 엔터: ")
            safe_goto(page, cfg["url"], wait_until="networkidle")
            page.wait_for_timeout(1500)

        # 쿠키 저장
        context.storage_state(path=str(auth_path))
        print(f"\n쿠키 저장 완료: {auth_path}")

        browser.close()

    print("\n완료! 이제 multi_blog_reserve_upload.py 를 실행하세요.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blog", choices=["health", "it", "both"], default="health")
    args = parser.parse_args()

    if args.blog == "both":
        save_cookies("health")
        save_cookies("it")
    else:
        save_cookies(args.blog)

if __name__ == "__main__":
    main()
