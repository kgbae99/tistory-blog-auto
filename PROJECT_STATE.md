# PROJECT_STATE.md — 건강온도사(행복++) 블로그 자동화 현황

> 최종 업데이트: 2026-03-21

---

## 1. 블로그 현황

### 건강 블로그 — 건강온도사(행복++)
- URL: https://kgbae2369.tistory.com/
- 주제: 건강/생활/뷰티/정부지원/복지
- 전체 글: ~508개 (공개 336개, 비공개 ~172개)
- 수익화: 구글 애드센스 승인완료 (gtag: G-SD7PEXH5NK), 쿠팡 파트너스 API 연동

### IT 블로그 — 테크온도(IT++)
- URL: https://uyoblog.tistory.com/
- 주제: IT 기기 리뷰/추천, 생산성 도구, AI 툴
- 브랜드: 테크온도(IT++) / 파비콘 적용 완료
- 카테고리: IT기기, 소프트웨어, AI도구, 생산성 등 구성
- 애드센스: 동일 pub-id 사용 가능 (별도 승인 불필요), 글 30개 달성 후 사이트 추가 신청 예정

---

## 2. 수익화 현황

### 구글 애드센스
- 상태: 승인완료, PIN 우편 발송중 (2026-03-17 발송, 2~3주 소요)
- PIN 미입력 시 수익 지급 보류 (광고 표시는 정상)
- 3/15 수익 스파이크 확인 (이유 불명, 이후 정상 추적 중)
- 광고 배치: 포스트 상단/중간/하단 3개 슬롯

### 쿠팡 파트너스
- API 키 발급 완료 (HMAC-SHA256 인증)
- 포스트당 관련 상품 3개 자동 삽입
- 폴백 캐시: `data/coupang_cache.json` (API 실패 시 사용)

---

## 3. 자동화 파이프라인

### GitHub Actions 워크플로우 (`.github/workflows/daily-posts.yml`)
- 실행 시각: 매일 07:00 KST (UTC 22:00 전날)
- 건강 블로그: `scripts/generate_daily_posts.py` → 3개/일
- IT 블로그: `scripts/generate_it_posts.py` → 3개/일
- 색인 요청: `scripts/request_indexing.py --count 200` (일일 200건 한도)
- 결과 커밋: `output/`, `data/` 자동 push

### 포스트 생성 흐름
```
트렌드 키워드 분석 → OpenAI GPT-4.1-mini 콘텐츠 생성
  → 쿠팡 파트너스 상품 3개 삽입
  → 애드센스 광고 3개 삽입
  → SEO 최적화 (JSON-LD, OG 태그, 메타 설명)
  → HTML 파일 저장 (output/posts/YYYY-MM-DD/)
  → 텔레그램 알림 발송
  → Git 커밋/푸시
```

### Make + Buffer SNS 자동 홍보
- 플랫폼: Make (무료 플랜) + Buffer
- 연동: RSS 피드 → OpenAI 요약 → Buffer → 쓰레드 자동 게시
- 주기: 3시간마다 실행 (Make 시나리오)
- 상태: 쓰레드 게시 성공 확인 (인스타그램 모듈 제거, 쓰레드만 유지)

### 텔레그램 알림 봇
- 봇명: @Kgblog_bot
- chat_id: 8623125283
- 알림 항목: 포스트 생성 완료, 색인 요청 결과, 일일 요약
- 코드: `src/notify/telegram.py`

---

## 4. 파일 구조 (핵심)

```
blog/
├── .github/workflows/daily-posts.yml  # GitHub Actions 자동화
├── scripts/
│   ├── generate_daily_posts.py        # 건강 블로그 생성 메인
│   ├── generate_it_posts.py           # IT 블로그 생성 메인
│   ├── request_indexing.py            # GSC 색인 요청
│   └── crawl_blog_posts.py            # 블로그 포스트 크롤링
├── src/
│   ├── core/                          # config, logger
│   ├── tistory/                       # Playwright 발행 자동화
│   ├── coupang/                       # HMAC API 클라이언트
│   ├── content/                       # 콘텐츠 생성 엔진
│   ├── adsense/                       # 광고 삽입
│   ├── notify/telegram.py             # 텔레그램 알림
│   └── scheduler/                     # APScheduler
├── templates/                         # Jinja2 HTML 템플릿
├── config/
│   ├── .env                           # API 키 (git 제외)
│   ├── gsc_token.json                 # GSC OAuth 토큰
│   └── settings.yaml                  # 전체 설정
├── data/
│   ├── indexed_urls.json              # 색인 요청 완료 URL (~200개)
│   ├── published_titles.json          # 중복 방지용 발행 제목 목록
│   ├── coupang_cache.json             # 쿠팡 API 폴백 캐시
│   ├── used_images.json               # 사용된 이미지 추적
│   └── blog_posts_index.json          # 전체 포스트 인덱스
└── output/
    ├── posts/YYYY-MM-DD/              # 건강 블로그 포스트 HTML
    └── it-posts/YYYY-MM-DD/           # IT 블로그 포스트 HTML
```

---

## 5. Google Search Console (GSC)

- 사이트: https://kgbae2369.tistory.com/
- 사이트맵: /sitemap.xml → 507개 URL 제출 완료 (2026-03-19)
- 색인 현황: 약 200개 색인 완료, 315개 대기
- 일일 색인 요청 한도: 200건 (Google Indexing API)
- 현재 scope: readonly (쓰기 권한 추가 예정)
- 색인 데이터: `data/indexed_urls.json`

---

## 6. 블로그 품질 관리

### 비공개 처리 기준
- 노출 1~4회, 클릭 0회인 저품질 글 99개 비공개
- 대표이미지 없는 글 비공개 처리 (수동 확인 중)
- 댓글 달린 글은 비공개 제외 → 하루 15개씩 공개 전환 예정

### 현재 비공개 현황
- 전체: ~508개
- 공개: 336개
- 비공개: ~172개

### 포스트 제목 스타일 (클릭률 최적화)
- 규칙: 밋밋한 제목 금지, 연도(2025/2026) 사용 금지
- 형식: 궁금증 유발 / 반전 / 숫자 / "이것" / "이렇게" 활용
- 예시: "목주름, 이렇게 하면 정말 줄어들까?" / "의사가 절대 안 먹는다는 식품 5가지"

---

## 7. 알려진 이슈 및 TODO

### 즉시 수정 필요
- [ ] `generate_it_posts.py`: `NameError: filepath` 변수 미정의 → 수정 필요
- [ ] IT 블로그 포스트 태그 자동 생성 개선 (빈 배열 방지)

### 단기 TODO (이번 주)
- [ ] 색인 요청 남은 ~315개 완료 (일일 200건, 2~3일 소요)
- [ ] 댓글 달린 글 하루 15개씩 공개 전환 (티스토리 제한)
- [ ] GSC OAuth scope 쓰기 권한 추가

### 중기 TODO (이번 달)
- [ ] 애드센스 PIN 우편 수령 후 입력 (3/17 발송, ~4월 초 예상)
- [ ] uyoblog 글 30개 달성 후 애드센스 사이트 추가 신청
- [ ] 대표이미지 없는 나머지 글 비공개 처리 완료

---

## 8. 환경 변수 (GitHub Secrets)

| 변수명 | 용도 |
|--------|------|
| OPENAI_API_KEY | 콘텐츠 생성 (GPT-4.1-mini) |
| GEMINI_API_KEY | 예비 AI API |
| COUPANG_ACCESS_KEY | 쿠팡 파트너스 API |
| COUPANG_SECRET_KEY | 쿠팡 HMAC 인증 |
| TELEGRAM_BOT_TOKEN | 텔레그램 봇 알림 |
| TELEGRAM_CHAT_ID | 텔레그램 채팅 ID (8623125283) |
| GSC_TOKEN_JSON | GSC OAuth 토큰 |
| GSC_CREDENTIALS_JSON | GSC 인증 정보 |
| ADSENSE_PUB_ID | 애드센스 발행자 ID |
| ADSENSE_SLOT_TOP/MID/BOTTOM | 광고 슬롯 ID |

---

## 9. 참고 링크

- 건강 블로그: https://kgbae2369.tistory.com/
- IT 블로그: https://uyoblog.tistory.com/
- GitHub Actions: `.github/workflows/daily-posts.yml`
- 텔레그램 봇: @Kgblog_bot
- Make 시나리오: RSS → OpenAI → Buffer → Threads (3시간마다)
