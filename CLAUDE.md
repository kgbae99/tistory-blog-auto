# 티스토리 블로그 자동화 - 건강온도사(행복++)

## 프로젝트 개요
티스토리 블로그(kgbae2369.tistory.com) 수익화 자동화 시스템.
쿠팡 파트너스 + 구글 애드센스 기반 콘텐츠 자동 생성/발행 파이프라인.

## 핵심 규칙

### 언어 & 런타임
- Python 3.11+ 필수
- 비동기: asyncio + Playwright
- 타입 힌트 필수 (모든 함수 시그니처)

### 코딩 컨벤션
- 린터: ruff (line-length=100)
- 포매터: ruff format
- 테스트: pytest + pytest-asyncio
- 모듈 구조: src/ 하위 패키지별 분리

### 보안 규칙 (엄격 준수)
- API 키, 비밀번호는 반드시 .env 파일에만 저장
- .env는 절대 git에 커밋하지 않음
- 로그에 민감 정보 출력 금지
- Playwright 세션 데이터는 .gitignore에 포함

### 블로그 도메인 지식
- 주제: 건강/생활/뷰티/정부지원/복지 정보
- 대상 독자: 건강과 생활에 관심 있는 20~60대
- 톤: 친근하고 전문적인 (건강온도사 브랜딩)
- 포스트당 쿠팡 상품 3개, 애드센스 광고 3개 배치

## 파일 구조 참조 (필요시 읽기)
- `src/coupang/` — 쿠팡 파트너스 API 연동 (HMAC 인증)
- `src/tistory/` — Playwright 기반 티스토리 자동 발행
- `src/content/` — Claude API 콘텐츠 생성 엔진
- `src/adsense/` — 애드센스 광고 자동 삽입
- `src/scheduler/` — APScheduler 기반 발행 스케줄러
- `templates/` — Jinja2 HTML 블로그 포스트 템플릿
- `config/settings.yaml` — 전체 설정 파일

## 팀 에이전트
- `.claude/agents/content-strategist.md` — 콘텐츠 전략
- `.claude/agents/seo-optimizer.md` — SEO 최적화
- `.claude/agents/trend-researcher.md` — 트렌드 리서치
- `.claude/agents/coupang-specialist.md` — 쿠팡 파트너스
- `.claude/agents/quality-reviewer.md` — 품질 검토

## 스킬
- `.claude/skills/blog-post-writer/` — 블로그 글쓰기
- `.claude/skills/keyword-research/` — 키워드 리서치
- `.claude/skills/coupang-link/` — 쿠팡 링크 생성
- `.claude/skills/seo-audit/` — SEO 감사

## 커맨드
- `/publish` — 트렌드 기반 자동 포스트 생성 및 발행
- `/trend` — 현재 트렌드 키워드 분석
- `/revenue-report` — 수익 현황 리포트

## 개발 워크플로우
1. 기능 구현 → ruff 린트 → pytest 테스트
2. 콘텐츠 관련 변경 시 quality-reviewer 에이전트 실행
3. SEO 관련 변경 시 seo-optimizer 에이전트 실행
