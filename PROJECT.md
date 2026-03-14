# 티스토리 블로그 자동화 - 건강온도사(행복++)

## 개요
티스토리 블로그 수익화 자동화 시스템. 쿠팡 파트너스 + 구글 애드센스 기반.

## 빠른 시작

### 1. 설치
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 환경 설정
```bash
cp config/.env.example config/.env
# .env 파일에 API 키 입력
```

### 3. 실행
```bash
# 자동 발행 (미리보기)
python scripts/daily_publish.py --dry-run

# 특정 키워드로 발행
python scripts/daily_publish.py --keyword "비타민D 효능"

# 스케줄러 시작 (매일 자동 발행)
python -m src.scheduler.cron_manager
```

### 4. 테스트
```bash
pytest tests/ -v
```

## Claude Code 커맨드
- `/publish` — 트렌드 기반 자동 포스트 생성 및 발행
- `/trend` — 현재 트렌드 키워드 분석
- `/revenue-report` — 수익 현황 리포트

## 구조
- `src/coupang/` — 쿠팡 파트너스 API (HMAC 인증)
- `src/tistory/` — Playwright 기반 티스토리 자동 발행
- `src/content/` — Claude API 콘텐츠 생성 엔진
- `src/adsense/` — 애드센스 광고 자동 삽입
- `src/scheduler/` — APScheduler 기반 발행 스케줄러
- `templates/` — Jinja2 블로그 포스트 템플릿
- `.claude/agents/` — 5개 전문 팀 에이전트
- `.claude/skills/` — 4개 재사용 가능한 스킬
- `.claude/commands/` — 3개 슬래시 커맨드
