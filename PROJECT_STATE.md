# PROJECT_STATE.md — 건강온도사(행복++) 블로그 자동화 현황

> 최종 업데이트: 2026-09-14

---

## 1. 블로그 현황

### 건강 블로그 — 건강온도사(행복++)
- URL: https://kgbae2369.tistory.com/
- 주제: 건강/생활/뷰티/정부지원/복지
- 카테고리(현재 실제 목록): 생활 건강, 생활습관·면역, 제철·계절 건강, 운동·통증, 영양·식이, 정부지원·복지, 증상·질환, 오늘의 건강뉴스
- 수익화: 구글 애드센스 승인완료 (gtag: G-SD7PEXH5NK), 쿠팡 파트너스 API 연동

### IT 블로그 — 테크온도(IT++)
- URL: https://uyoblog.tistory.com/
- 주제: IT 기기 리뷰/추천, 생산성 도구, AI 툴
- 카테고리: IT/가젯 등

---

## 2. 자동화 파이프라인 (전체 구조)

콘텐츠 **생성**은 GitHub Actions에서 완전 자동, 실제 **발행**은 로컬 PC에서 Playwright로 수동 실행한다. GitHub Actions는 티스토리에 로그인할 방법이 없어(공식 글쓰기 API가 2024년 초 종료됨) 발행 단계까지 자동화할 수 없다.

### 2-1. 생성 단계 (GitHub Actions, 완전 자동)

`.github/workflows/daily-posts.yml` — 매일 07:00 KST (UTC 22:00 전날) 실행:
- `scripts/generate_daily_posts.py` → 건강 포스트 2개
- `scripts/generate_health_news.py --count 7` → 건강뉴스 롤업 1개 (RSS 5개 매체 요약, 출처 표시)
- `scripts/generate_it_posts.py` → IT 포스트 2개
- `scripts/request_indexing.py --count 200` → GSC 색인 요청
- 결과를 `output/`, `data/`에 커밋/푸시

> 과거에 `daily-pipeline.yml`(step1~4, gpt-4o 기반)이라는 두 번째 생성 워크플로우가 동일 cron으로 같이 돌고 있었는데, 위 워크플로우가 매번 같은 출력 폴더를 `shutil.rmtree()`로 지우고 덮어써서 매일 결과물이 통째로 버려지고 있었다. 2026-09-14에 해당 워크플로우/스크립트(`step1_keywords.py`~`step4_rewrite.py`, `generate.bat`)와 축적된 중간산출물(`data/pipeline/`, ~1,272개 파일)을 전량 제거했다.

### 2-2. 발행 단계 (로컬 PC, Playwright, 수동 트리거)

1. `pull_posts.bat` (= `git pull`) — GH Actions가 생성한 오늘자 포스트를 로컬로 받기
2. `blog_manager.bat` 실행 → 메뉴 선택
   - `[4]` Upload - Health Blog / `[5]` Upload - IT Blog / `[6]` Upload - All Blogs
   - `[8]` Auth - Save login session (수동 세션 갱신)
3. 로그인 세션 만료 시 `scripts/save_auth_cookies.py`가 자동으로 브라우저를 띄우고 카카오 로그인을 요청 → 로그인 완료하면 자동으로 이어서 진행

핵심 스크립트:
- `scripts/multi_blog_reserve_upload.py` — Playwright로 실제 발행(카테고리 선택, 대표이미지, 예약/즉시발행). `BLOG_MAP`에 블로그별 폴더/카테고리/파일매칭 규칙이 있음. `posts`와 `health-news`는 같은 폴더(`output/posts`)를 쓰지만 `file_match` 규칙으로 서로의 파일을 건드리지 않게 분리되어 있음.
- `scripts/save_auth_cookies.py` — 로그인 세션(쿠키) 저장/갱신. 로그인 완료를 카카오 콜백 중간 페이지가 아니라 실제 타겟 블로그 관리 페이지 접속 결과로 확인함.
- 세션 파일: `config/auth_blog.json`(건강), `config/auth_blog_it.json`(IT) — `.gitignore` 처리됨, 절대 커밋되지 않음.

### Make + Buffer SNS 자동 홍보
- 플랫폼: Make (무료 플랜) + Buffer
- 연동: RSS 피드 → OpenAI 요약 → Buffer → 쓰레드 자동 게시
- 주기: 3시간마다 실행 (Make 시나리오)

### 텔레그램 알림 봇
- 봇명: @Kgblog_bot, chat_id: 8623125283
- 코드: `src/notify/telegram.py`

---

## 3. 파일 구조 (핵심)

```
blog/
├── .github/workflows/daily-posts.yml   # 생성 자동화 (유일한 생성 워크플로우)
├── blog_manager.bat                    # 로컬 발행 메뉴 (생성+업로드)
├── pull_posts.bat                      # git pull 래퍼 (오늘자 포스트 받기)
├── scripts/
│   ├── generate_daily_posts.py         # 건강 블로그 생성
│   ├── generate_health_news.py         # 건강뉴스 롤업 생성 (RSS 5개 매체)
│   ├── generate_it_posts.py            # IT 블로그 생성
│   ├── multi_blog_reserve_upload.py    # Playwright 발행 (핵심)
│   ├── save_auth_cookies.py            # 로그인 세션 저장/갱신
│   ├── refresh_gsc_token.py            # GSC/Indexing API 토큰 재발급
│   └── request_indexing.py             # GSC 색인 요청
├── src/
│   ├── core/, tistory/, coupang/, content/, adsense/, notify/, scheduler/
├── config/
│   ├── .env                            # API 키 (git 제외)
│   ├── auth_blog.json / auth_blog_it.json   # 로그인 세션 (git 제외)
│   ├── gsc_token.json / credentials.json    # GSC 인증 (git 제외)
│   └── settings.yaml
├── data/
│   ├── indexed_urls.json, published_titles.json, posts_db.json 등
└── output/
    ├── posts/YYYY-MM-DD/       # 건강 블로그 + 건강뉴스 HTML
    └── it-posts/YYYY-MM-DD/    # IT 블로그 HTML
```

---

## 4. Google Search Console (GSC)

- 사이트: https://kgbae2369.tistory.com/
- 색인 요청: `scripts/request_indexing.py` (일일 200건 한도, Google Indexing API)
- OAuth scope: `indexing` 쓰기 권한 포함됨 (`refresh_gsc_token.py` 참고)
- 토큰 만료 시 `python scripts/refresh_gsc_token.py`로 재발급 후 `GSC_TOKEN_JSON` 시크릿 갱신

---

## 5. 콘텐츠 규칙

### 포스트 제목 스타일 (클릭률 최적화)
- 규칙: 밋밋한 제목 금지, 연도(2025/2026) 사용 금지
- 형식: 궁금증 유발 / 반전 / 숫자 / "이것" / "이렇게" 활용
- 예시: "목주름, 이렇게 하면 정말 줄어들까?" / "의사가 절대 안 먹는다는 식품 5가지"

### 건강뉴스 롤업 출처 표시
- RSS 내부 식별자(yna_health 등)가 아니라 실제 언론사명으로 표시 (연합뉴스, 청년의사, 헬스코리아뉴스, 뉴시스, 코메디닷컴)

---

## 6. 환경 변수 (GitHub Secrets)

| 변수명 | 용도 |
|--------|------|
| OPENAI_API_KEY | 콘텐츠 생성 |
| GEMINI_API_KEY | 예비 AI API |
| COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY | 쿠팡 파트너스 API (HMAC) |
| TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID | 텔레그램 봇 알림 |
| GSC_TOKEN_JSON / GSC_CREDENTIALS_JSON | GSC OAuth |
| ADSENSE_PUB_ID / ADSENSE_SLOT_TOP/MID/BOTTOM | 애드센스 |

로컬 전용(git 제외, GitHub Secrets에는 없음): `config/auth_blog.json`, `config/auth_blog_it.json` — 발행은 로컬에서만 하므로 이 세션 파일들은 CI에 올릴 필요 없음.

---

## 7. 알려진 이슈 / TODO

- [ ] 애드센스 사이트 확장(uyoblog) 여부 재검토 — 별도 승인 필요 여부 확인
- [ ] `output/`, `data/`가 매일 누적되어 리포 용량이 계속 커짐 — 오래된 발행분 정리 정책 검토
- [ ] `multi_blog_reserve_upload.py`에 발행 이력 가드가 없어, 같은 날 업로드를 두 번 실행하면 중복 발행될 수 있음 (수동 주의 필요)

---

## 8. 참고 링크

- 건강 블로그: https://kgbae2369.tistory.com/
- IT 블로그: https://uyoblog.tistory.com/
- GitHub Actions: `.github/workflows/daily-posts.yml`
- 텔레그램 봇: @Kgblog_bot
- Make 시나리오: RSS → OpenAI → Buffer → Threads (3시간마다)
