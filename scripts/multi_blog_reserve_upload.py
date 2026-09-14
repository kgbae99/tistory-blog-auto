from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from datetime import datetime, timedelta
import random
import time
import re
import subprocess

# =========================
# 기본 설정
# =========================

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

BLOG_MAP = {
    "posts": {
        "base_dir": r"C:\Users\CleanAdmin\Desktop\claude\blog\output\posts",
        "auth": r"C:\Users\CleanAdmin\Desktop\claude\blog\config\auth_blog.json",
        "url": "https://kgbae2369.tistory.com/manage/newpost/",
        "category": "생활 건강",
        # health-news 파일(YYYYMMDD_health_news.html)은 이 키가 다루지 않음
        "file_match": lambda name: not name.lower().endswith("_health_news.html"),
    },
    "health-news": {
        "base_dir": r"C:\Users\CleanAdmin\Desktop\claude\blog\output\posts",
        "auth": r"C:\Users\CleanAdmin\Desktop\claude\blog\config\auth_blog.json",
        "url": "https://kgbae2369.tistory.com/manage/newpost/",
        "category": "오늘의 건강뉴스",
        "file_match": lambda name: name.lower().endswith("_health_news.html"),
    },
    "it-posts": {
        "base_dir": r"C:\Users\CleanAdmin\Desktop\claude\blog\output\it-posts",
        "auth": r"C:\Users\CleanAdmin\Desktop\claude\blog\config\auth_blog_it.json",
        "url": "https://uyoblog.tistory.com/manage/newpost/",
        "category": "IT/가젯"
    }
}

RESERVE_TIMES = ["08:00", "12:30", "18:00"]  # 기본값 (내일 예약 시 사용)

def get_today_reserve_times(count: int) -> list[str]:
    """
    오늘 현재 시각 기준으로 최소 30분 이후 시간대에서
    count개의 랜덤 예약 시간을 생성합니다.
    시간대 풀: 9~22시 중 30분 단위, 현재+30분 이후만 사용
    """
    now = datetime.now()
    min_time = now + timedelta(minutes=30)

    # 30분 단위 후보 슬롯 생성 (9:00 ~ 22:00)
    slots = []
    for hour in range(9, 23):
        for minute in [0, 30]:
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate > min_time:
                slots.append(candidate)

    if not slots:
        # 오늘 남은 슬롯 없으면 내일 오전으로
        tomorrow = now + timedelta(days=1)
        slots = [tomorrow.replace(hour=h, minute=m, second=0, microsecond=0)
                 for h in range(9, 23) for m in [0, 30]]

    # 랜덤 선택 후 시간순 정렬
    chosen = sorted(random.sample(slots, min(count, len(slots))))
    return [t.strftime("%H:%M") for t in chosen]

IFRAME_SELECTOR = (
    'iframe[title="서식 있는 텍스트 편집기 입니다. ALT-F9를 누르면 메뉴, '
    'ALT-F10를 누르면 툴바, ALT-0을 누르면 도움말을 볼 수 있습니다."]'
)

STOPWORDS = {
    # 파일명 잔재
    "post", "html",
    # 불용 동사/형용사
    "알게", "써보고", "느낀", "되는", "하고", "라는", "한다", "된다",
    "했다", "보고", "라면", "하여", "하면", "하지", "얻는", "이런",
    "다르다", "알아야", "통해", "위해", "대해", "관한",
    # 단순 조사/접속사
    "그리고", "하지만", "또한", "따라서", "즉", "및",
    # 너무 일반적인 명사
    "제품", "기능", "사용", "결과", "내용", "경우", "방식", "이유",
    "문제", "특징", "장점", "단점", "가격", "정도", "수준", "진짜",
    "실제", "완전", "종류", "항목", "기준", "여부", "목록", "변화",
    "가지", "이점", "구성", "상관", "관계", "차이", "점이",
}

# 블로그별 고정 태그
BLOG_FIXED_TAGS = {
    "posts":    ["건강", "웰빙", "건강정보", "생활건강"],
    "it-posts": ["IT", "가젯", "테크", "IT리뷰"],
}

# 한국어 조사 제거 패턴
_JOSA_PATTERN = re.compile(
    r"(과|와|의|을|를|이|가|은|는|도|로|으로|에|서|에서|부터|까지|만|보다|처럼|같이|라고|이라고|란|이란|와의|과의)$"
)

def _strip_josa(word: str) -> str:
    stripped = _JOSA_PATTERN.sub("", word)
    return stripped if len(stripped) >= 2 else word

def make_tags(title: str, file_path: Path, max_tags: int = 8, blog_key: str = "") -> list[str]:
    """
    태그 생성 전략:
    1. 블로그별 고정 태그 (건강/IT 등)
    2. 제목에서 2글자 이상 명사 추출 (조사 제거, 불용어 필터)
    3. 중복/부분문자열 제거
    """
    tags = []
    seen = set()

    # 1. 고정 태그 먼저
    for t in BLOG_FIXED_TAGS.get(blog_key, []):
        if t not in seen:
            seen.add(t)
            tags.append(t)

    # 2. 제목에서 명사 추출
    words = re.findall(r"[가-힣]{2,}|[A-Za-z][A-Za-z0-9]+", title)
    for word in words:
        word = _strip_josa(word.strip())
        if len(word) < 2:
            continue
        if word.lower() in STOPWORDS:
            continue
        # 부분 문자열 중복 제거
        if any(word in t or t in word for t in seen):
            continue
        seen.add(word)
        tags.append(word)
        if len(tags) >= max_tags:
            break

    return tags

def human_delay(a=1.0, b=2.2):
    time.sleep(random.uniform(a, b))

def get_today_folder(base_path: Path) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    return base_path / today

def get_tomorrow_date_str() -> str:
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

def read_html_file(path: Path) -> str:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"파일 내용이 비어 있습니다: {path}")
    return content

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def title_from_filename(file_path: Path) -> str:
    name = file_path.stem
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\bpost\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\b\d+\b", "", name)
    name = clean_text(name)
    return name if name else "제목 없음"

def extract_title_from_html(html: str, file_path: Path) -> str:
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if h1:
        text = clean_text(h1.get_text(" ", strip=True))
        if text:
            return text

    title_tag = soup.find("title")
    if title_tag:
        text = clean_text(title_tag.get_text(" ", strip=True))
        if "::" in text:
            text = text.split("::")[0].strip()
        if text:
            return text

    for tag in soup.find_all(["h2", "h3", "p"]):
        text = clean_text(tag.get_text(" ", strip=True))
        if len(text) >= 8:
            return text[:80]

    return title_from_filename(file_path)



def close_popups(page):
    for text in ["닫기", "취소", "나중에"]:
        try:
            btn = page.get_by_text(text)
            if btn.first.is_visible(timeout=1000):
                btn.first.click()
                human_delay(0.3, 0.8)
        except Exception:
            pass

def check_and_wait_login(page, post_url: str):
    """로그인 페이지로 리다이렉트됐는지 확인하고, 됐으면 로그인 대기 후 원래 URL로 복귀"""
    current = page.url
    if "accounts.kakao.com" in current or "tistory.com/auth" in current or "login" in current.lower():
        print("\n" + "="*50)
        print("!! 로그인 세션 만료 감지!")
        print("브라우저에서 로그인 후 관리 화면이 뜨면 엔터를 누르세요.")
        print("="*50)
        input(">>> 로그인 완료 후 엔터: ")
        safe_goto(page, post_url)
        human_delay(2.0, 3.0)
        close_popups(page)

# =========================
# 카테고리
# =========================


def _category_candidates(category_name: str) -> list[str]:
    base = (category_name or "").strip()
    variants = [base]
    # 티스토리가 "1. 카테고리명" 형태로 표시하는 경우 대비 — 번호 포함 버전 추가
    for n in range(1, 15):
        variants.append(f"{n}. {base}")
    if "IT" in base:
        variants.extend(["IT/가젯", "IT, 가젯", "IT 가젯", "가젯", "IT"])
    if "&" in base:
        variants.append(base.replace("&", "＆"))
        variants.append(base.replace("&", " and "))
    unique = []
    for item in variants:
        if item and item not in unique:
            unique.append(item)
    return unique

def select_category(page, category_name: str):
    print(f"카테고리 선택 시도: {category_name}")

    page.wait_for_load_state("networkidle")
    human_delay(1.5, 2.0)

    combo = page.get_by_role("combobox", name="카테고리 선택").first
    combo.wait_for(timeout=15000)
    combo.click()
    human_delay(0.8, 1.2)

    for candidate in _category_candidates(category_name):
        try:
            option = page.get_by_role("option", name=candidate).first
            option.wait_for(timeout=3000)
            option.click(force=True)
            print(f"카테고리 선택 완료 (role=option): {candidate}")
            human_delay(0.8, 1.2)
            return
        except Exception:
            pass

        try:
            option = page.locator("ul li, div[role='option']").filter(has_text=candidate).first
            option.wait_for(timeout=3000)
            option.scroll_into_view_if_needed()
            option.click(force=True)
            print(f"카테고리 선택 완료 (has_text): {candidate}")
            human_delay(0.8, 1.2)
            return
        except Exception:
            pass

    print(f"카테고리 선택 실패: {category_name}")

def fill_title(page, title: str):
    title_box = page.get_by_role("textbox", name="제목을 입력하세요")
    title_box.click()
    human_delay(0.3, 0.8)
    title_box.fill(title)

def insert_html_body(page, html_content: str):
    editor = page.frame_locator(IFRAME_SELECTOR).locator('[contenteditable="true"]')
    editor.click()
    human_delay(0.3, 0.8)

    editor.evaluate(
        """(el, html) => {
            el.focus();
            const sel = el.ownerDocument.getSelection();
            const range = el.ownerDocument.createRange();
            range.selectNodeContents(el);
            sel.removeAllRanges();
            sel.addRange(range);
            el.ownerDocument.execCommand('delete', false, null);
            el.ownerDocument.execCommand('insertHTML', false, html);
        }""",
        html_content
    )

def fill_tags(page, tags: list[str]):
    if not tags:
        return

    candidates = [
        page.get_by_placeholder("태그"),
        page.locator('input[placeholder*="태그"]').first,
        page.locator('input[name*="tag"]').first,
    ]

    tag_input = None
    for c in candidates:
        try:
            if c.is_visible(timeout=1000):
                tag_input = c
                break
        except Exception:
            pass

    if tag_input is None:
        print("태그 입력창을 찾지 못했습니다.")
        return

    tag_input.click()
    human_delay(0.3, 0.8)

    for tag in tags:
        tag_input.fill(tag)
        page.keyboard.press("Enter")
        human_delay(0.2, 0.5)

# ─── 버그 수정 1+3: 중복 호출 제거 + 대표이미지 체크 안정화 ───
def upload_and_set_representative_image(page, html_content: str) -> bool:
    """
    1. HTML 첫 번째 이미지를 클립보드로 에디터 상단에 붙여넣기
       (티스토리가 카카오CDN으로 업로드 → 대표이미지 버튼 활성화됨)
    2. 업로드된 이미지 클릭 → .mce-represent-image-btn 클릭
    """
    import requests
    import tempfile
    import os

    soup = BeautifulSoup(html_content, "html.parser")
    img_tag = soup.find("img")
    if not img_tag:
        print("이미지 없음 — 대표이미지 건너뜀")
        return False

    img_url = img_tag.get("src", "")
    if not img_url:
        print("이미지 src 없음")
        return False

    tmp_path = None
    try:
        # [케이스 1] data:image/... base64 → 임시파일로 디코딩
        if img_url.startswith("data:"):
            import base64, re as _re
            m = _re.match(r"data:image/(\w+);base64,(.+)", img_url)
            if not m:
                print("base64 이미지 파싱 실패")
                return False
            ext = m.group(1).lower()
            if ext == "jpeg": ext = "jpg"
            img_bytes = base64.b64decode(m.group(2))
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(img_bytes)
                tmp_path = f.name
            print(f"base64 이미지 임시파일 생성: {tmp_path}")

        # [케이스 2] 로컬 파일 경로 (C:\... 또는 /...)
        elif os.path.exists(img_url):
            tmp_path = img_url
            print(f"로컬 이미지 사용: {tmp_path}")

        # [케이스 3] HTTP URL → 다운로드
        else:
            print(f"대표이미지 다운로드 중: {img_url[:60]}...")
            resp = requests.get(img_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            ext = img_url.split("?")[0].split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png", "webp", "gif"]: ext = "jpg"
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
                f.write(resp.content)
                tmp_path = f.name

        # 클립보드에 이미지 복사
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile('{tmp_path}')
[System.Windows.Forms.Clipboard]::SetImage($img)
$img.Dispose()
"""
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=10)
        human_delay(0.5, 1.0)

        # 에디터 커서 맨 앞으로 이동 후 붙여넣기
        editor = page.frame_locator(IFRAME_SELECTOR).locator('[contenteditable="true"]')
        editor.click()
        human_delay(0.3, 0.5)
        page.keyboard.press("Control+Home")
        human_delay(0.2, 0.3)
        page.keyboard.press("Control+V")
        print("클립보드 이미지 붙여넣기 완료")

        # 티스토리가 카카오CDN으로 업로드할 때까지 대기
        # — kakaocdn.net URL을 가진 img가 생길 때까지 폴링
        print("카카오CDN 업로드 대기 중...")
        iframe = page.frame_locator(IFRAME_SELECTOR)
        for i in range(30):
            time.sleep(1.0)
            kakao_count = iframe.locator("img[src*='kakaocdn']").count()
            print(f"  [{i+1}] kakaocdn img count: {kakao_count}")
            if kakao_count > 0:
                print("카카오CDN 업로드 완료 — 대표이미지 버튼 클릭 시도")
                break
        else:
            print("카카오CDN 업로드 타임아웃 — 그냥 진행")

        human_delay(1.0, 1.5)

        # 첫 번째 이미지 클릭 → 대표이미지 버튼 클릭
        first_img = iframe.locator("img").first
        first_img.scroll_into_view_if_needed()
        first_img.click()
        human_delay(1.0, 1.5)

        # 툴바가 이미지 위에 뜨는데 화면 상단에 잘릴 수 있으므로 아래로 스크롤
        page.frame_locator(IFRAME_SELECTOR).locator("body").evaluate(
            "() => window.scrollBy(0, 150)"
        )
        human_delay(0.5, 0.8)

        # 폴링으로 버튼 대기 후 JS로 직접 클릭 (force=True도 안 되는 경우 대비)
        for i in range(16):
            time.sleep(0.5)
            count = page.locator(".mce-represent-image-btn").count()
            print(f"  [{i+1}] 대표이미지 버튼 count: {count}")
            if count > 0:
                # JS로 직접 클릭 (visibility 무관)
                page.evaluate("""
                    () => {
                        const btn = document.querySelector('.mce-represent-image-btn');
                        if (btn) btn.click();
                    }
                """)
                human_delay(0.5, 1.0)
                print("대표이미지 체크 완료")
                break
        else:
            print("대표이미지 버튼 미노출 — 건너뜀")

        if tmp_path and tmp_path != img_url and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return True

    except Exception as e:
        print(f"대표이미지 업로드 실패: {e}")
        return False

def click_complete(page):
    page.get_by_role("button", name="완료").click()
    human_delay(1.0, 1.8)

def open_reserve_panel(page):
    reserve_btn = page.get_by_text("예약", exact=True).first
    reserve_btn.click()
    human_delay(1.0, 1.5)

def set_reserve_datetime(page, reserve_date: str, reserve_time: str):
    human_delay(0.8, 1.2)
    hour, minute = reserve_time.split(":")

    date_btn = page.locator("button.btn_reserve").first
    date_btn.click()
    human_delay(0.8, 1.2)

    day_int = int(reserve_date.split("-")[2])
    day_locator = page.locator("button.btn_day, td.day, a.day").filter(has_text=str(day_int)).first
    try:
        day_locator.wait_for(timeout=3000)
        day_locator.click()
        human_delay(0.5, 0.8)
        print(f"날짜 선택 완료: {reserve_date}")
    except Exception:
        page.evaluate(f"""
            const btns = document.querySelectorAll('button, td, a');
            for (const btn of btns) {{
                if (btn.textContent.trim() === '{day_int}') {{
                    btn.click();
                    break;
                }}
            }}
        """)
        human_delay(0.5, 0.8)
        print(f"날짜 선택 완료 (JS): {reserve_date}")

    hour_input = page.locator("input[name='dateHour']")
    hour_input.click(click_count=3)
    hour_input.press("Control+A")
    hour_input.press("Backspace")
    hour_input.fill(hour)
    page.keyboard.press("Tab")
    human_delay(0.2, 0.3)

    minute_input = page.locator("input[name='dateMinute']")
    minute_input.click(click_count=3)
    minute_input.press("Control+A")
    minute_input.press("Backspace")
    minute_input.fill(minute)
    page.keyboard.press("Tab")
    human_delay(0.2, 0.3)

    print(f"예약 설정 완료: {reserve_date} {reserve_time}")

def click_publish(page):
    page.get_by_role("button", name="공개 발행").click()
    human_delay(1.0, 2.0)

# =========================
# 글 1개 처리
# =========================

def process_one_file(page, file_path: Path, reserve_date: str, reserve_time: str, post_url: str, category_name: str, blog_key: str = "", instant: bool = False):
    html_content = read_html_file(file_path)
    post_title = extract_title_from_html(html_content, file_path)
    tags = make_tags(post_title, file_path, blog_key=blog_key)

    print(f"\n처리 파일: {file_path.name}")
    print(f"제목: {post_title}")
    print(f"카테고리: {category_name}")
    print(f"태그: {tags}")
    if instant:
        print("발행 모드: 즉시 공개 발행")
    else:
        print(f"예약: {reserve_date} {reserve_time}")

    page.goto(post_url, wait_until="domcontentloaded")
    human_delay()
    close_popups(page)
    check_and_wait_login(page, post_url)

    select_category(page, category_name)
    fill_title(page, post_title)

    # ─── 순서: 대표이미지 먼저(빈 에디터일 때) → 본문 뒤에 추가 ───
    # 빈 에디터 상태에서 붙여넣으면 이미지가 반드시 맨 위에 위치함
    print("대표이미지 설정 시작...")
    ok = upload_and_set_representative_image(page, html_content)
    if not ok:
        print("대표이미지 설정 실패 — 계속 진행")
    human_delay(1.0, 1.5)

    # ─── 본문 삽입: 첫 번째 이미지 제거 후 커서 끝에서 추가 ───
    soup_tmp = BeautifulSoup(html_content, "html.parser")
    first_img = soup_tmp.find("img")
    if first_img:
        parent = first_img.parent
        if parent and parent.name in ("div", "p", "figure") and len(parent.find_all("img")) == 1 and not parent.get_text(strip=True):
            parent.decompose()
        else:
            first_img.decompose()

    body = soup_tmp.find("body")
    body_html = "".join(str(c) for c in body.children) if body else str(soup_tmp)

    # 에디터 커서를 맨 끝으로 이동 후 본문 삽입
    editor = page.frame_locator(IFRAME_SELECTOR).locator('[contenteditable="true"]')
    editor.click()
    human_delay(0.3, 0.5)
    editor.press("Control+End")
    human_delay(0.2, 0.3)
    insert_html_body(page, body_html)
    human_delay()

    fill_tags(page, tags)
    human_delay()

    # 본문 이미지 개수 확인 (디버그용)
    try:
        img_count = page.frame_locator(IFRAME_SELECTOR).locator("img").count()
        print(f"본문 이미지 개수: {img_count}")
    except Exception as e:
        print(f"본문 이미지 개수 확인 실패: {e}")

    click_complete(page)
    human_delay(1.0, 1.5)

    if instant:
        # 즉시 공개 발행 (예약 패널 사용 안 함)
        print("[7] Instant → 즉시 공개 발행")
        click_publish(page)
        print("즉시 발행 클릭 완료")
        print("캡챠가 뜨면: 입력 → 답변 제출 → 공개 발행 클릭")
        input("저장 완료 후 엔터를 누르세요...")
    else:
        # 예약 발행
        open_reserve_panel(page)
        set_reserve_datetime(page, reserve_date, reserve_time)
        click_publish(page)
        print("공개 발행 클릭 완료")
        print("캡챠가 뜨면: 입력 → 답변 제출 → 공개 발행 클릭")
        input("저장 완료 후 엔터를 누르세요...")

    try:
        page.goto("about:blank", wait_until="domcontentloaded")
        human_delay(1.0, 1.5)
    except Exception:
        pass

# =========================
# 블로그별 실행
# =========================

def pick_date_folder(base_path: Path) -> Path:
    """날짜 폴더 목록을 보여주고 선택하게 함 (즉시 발행용)"""
    # YYYY-MM-DD 형식 폴더만 수집, 최신순 정렬
    date_dirs = sorted(
        [d for d in base_path.iterdir() if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", d.name)],
        reverse=True
    )
    if not date_dirs:
        return get_today_folder(base_path)

    print("\n발행할 날짜 폴더를 선택하세요:")
    for i, d in enumerate(date_dirs[:10]):  # 최대 10개
        # 폴더 안 html 개수 표시
        html_count = len([f for f in d.iterdir() if f.is_file() and f.name.lower().endswith(".html")])
        marker = " << 오늘" if d.name == datetime.now().strftime("%Y-%m-%d") else ""
        print(f"  [{i+1}] {d.name}  ({html_count}개){marker}")

    try:
        sel = int(input(f"선택 (1~{min(10, len(date_dirs))}): ").strip()) - 1
        if 0 <= sel < len(date_dirs[:10]):
            return date_dirs[sel]
    except ValueError:
        pass

    print("잘못된 입력 - 오늘 폴더 사용")
    return get_today_folder(base_path)


def process_blog(folder_name: str, config: dict, instant: bool = False):
    base_path = Path(config["base_dir"])
    auth_path = Path(config["auth"])
    post_url = config["url"]
    category_name = config["category"]

    target_dir = pick_date_folder(base_path) if instant else get_today_folder(base_path)

    print(f"\n===== {folder_name} 시작 =====")
    print(f"확인 폴더: {target_dir}")

    if not target_dir.exists():
        print("폴더 없음")
        return

    if not auth_path.exists():
        print("auth 없음")
        return

    file_match = config.get("file_match", lambda name: True)
    files = []
    for f in target_dir.iterdir():
        if f.is_file() and f.name.strip().lower().endswith(".html") and file_match(f.name):
            files.append(f)

    files = sorted(files)
    print("발견 html:", [f.name for f in files])

    if not files:
        print("처리할 파일 없음")
        return

    # ── 파일마다 수동으로 날짜/시간 입력 ──
    print("\n" + "="*50)
    print("각 파일의 예약 발행 시간을 직접 입력하세요.")
    print("형식: HH:MM (오늘 날짜 자동)  또는  YYYY-MM-DD HH:MM")
    print("건너뛰려면 엔터 (해당 파일 업로드 안 함)")
    print("="*50)

    today_str = datetime.now().strftime("%Y-%m-%d")
    schedule = []

    for f in files:
        while True:
            raw = input(f"\n  [{f.name}]\n  예약 시간 입력 (엔터=즉시발행, n=건너뜀, HH:MM=예약): ").strip()
            if raw.lower() == "n":
                print("  -> 건너뜀")
                break
            if not raw:
                print("  -> 즉시 발행")
                schedule.append((f, None, None))
                break
            if re.match(r"^\d{1,2}:\d{2}$", raw):
                r_date = today_str
                r_time = raw.zfill(5)
            elif re.match(r"^\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}$", raw):
                parts = raw.split(" ")
                r_date = parts[0]
                r_time = parts[1].zfill(5)
            else:
                print("  형식 오류. 예) 14:30  /  2026-04-12 14:30")
                continue
            print(f"  -> {r_date} {r_time} 예약")
            schedule.append((f, r_date, r_time))
            break

    if not schedule:
        print("\n업로드할 파일이 없습니다.")
        return

    print("\n" + "="*50)
    print("최종 업로드 스케줄:")
    for f, d, t in schedule:
        mode = "즉시 발행" if d is None else f"{d} {t}"
        print(f"  {f.name}  ->  {mode}")
    print("="*50)
    confirm = input("진행할까요? (Y/n): ").strip().lower()
    if confirm == "n":
        print("취소됨.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=80)
        context = browser.new_context(storage_state=str(auth_path))
        page = context.new_page()

        for file_path, reserve_date, reserve_time in schedule:
            mode = "즉시 발행" if reserve_date is None else f"{reserve_date} {reserve_time}"
            print(f"\n업로드 시작: {file_path.name} -> {mode}")
            process_one_file(
                page=page,
                file_path=file_path,
                reserve_date=reserve_date or "",
                reserve_time=reserve_time or "",
                post_url=post_url,
                category_name=category_name,
                blog_key=folder_name,
                instant=(reserve_date is None)
            )

        browser.close()

# =========================
# 전체 실행 (argparse)
# =========================

def run():
    import argparse
    parser = argparse.ArgumentParser(description="Tistory 블로그 업로드")
    parser.add_argument(
        "--blog",
        choices=["posts", "health-news", "it-posts", "all"],
        default=None,
        help="업로드할 블로그 (posts / it-posts / all)"
    )
    parser.add_argument(
        "--instant",
        metavar="BLOG",
        choices=["posts", "health-news", "it-posts"],
        default=None,
        help="즉시 공개 발행 (posts / it-posts)"
    )
    args = parser.parse_args()

    # 즉시 발행 모드
    if args.instant:
        blog_key = args.instant
        config = BLOG_MAP[blog_key]
        print(f"\n[즉시 발행] {blog_key}")
        process_blog(blog_key, config, instant=True)
        return

    # 예약 업로드 모드
    if args.blog:
        if args.blog == "all":
            selected = ["posts", "it-posts"]
        else:
            selected = [args.blog]
    else:
        # 인수 없이 직접 실행 시 대화형 선택
        print("\n업로드할 블로그를 선택하세요:")
        print("  1. posts (생활 건강)")
        print("  2. health-news (오늘의 건강뉴스)")
        print("  3. it-posts (IT/가젯)")
        print("  4. 전체 (posts + it-posts)")
        choice = input("\n선택 (1/2/3/4): ").strip()
        if choice == "1":
            selected = ["posts"]
        elif choice == "2":
            selected = ["health-news"]
        elif choice == "3":
            selected = ["it-posts"]
        elif choice == "4":
            selected = ["posts", "it-posts"]
        else:
            print("잘못된 입력. 전체 실행합니다.")
            selected = ["posts", "it-posts"]

    print(f"선택된 블로그: {selected}\n")
    for folder_name in selected:
        config = BLOG_MAP[folder_name]
        process_blog(folder_name, config, instant=False)

if __name__ == "__main__":
    run()
