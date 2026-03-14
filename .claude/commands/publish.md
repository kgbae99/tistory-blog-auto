---
name: publish
description: 트렌드 기반 블로그 포스트 자동 생성 및 티스토리 발행. 키워드 리서치 → 콘텐츠 생성 → 쿠팡 상품 삽입 → SEO 최적화 → 품질 검토 → 발행까지 전체 파이프라인 실행.
user_invocable: true
---

# /publish — 자동 포스트 생성 및 발행

## 실행 흐름

### 1단계: 트렌드 키워드 선정
trend-researcher 에이전트를 활용하여:
- 현재 트렌드 키워드 분석
- 건강/생활/뷰티 분야 필터링
- 쿠팡 상품 매칭 가능한 키워드 우선

### 2단계: 콘텐츠 생성
content-strategist 에이전트 + blog-post-writer 스킬 활용:
- 선정된 키워드로 포스트 구조 기획
- Claude API로 본문 생성 (src/content/generator.py)
- 1,500~3,000자 목표

### 3단계: 쿠팡 상품 삽입
coupang-specialist 에이전트 활용:
- 키워드로 쿠팡 상품 검색 (src/coupang/product_search.py)
- 상위 3개 상품 선택 및 수익 링크 생성
- HTML 위젯 삽입

### 4단계: SEO 최적화
seo-optimizer 에이전트 + seo-audit 스킬 활용:
- 제목/메타 설명 최적화
- 헤딩 구조 점검
- 구조화 데이터 추가

### 5단계: 애드센스 광고 배치
- 설정(settings.yaml)에 따라 광고 코드 삽입
- src/adsense/ad_inserter.py 실행

### 6단계: 품질 검토
quality-reviewer 에이전트 활용:
- 70점 이상이면 발행 진행
- 미달 시 개선 후 재검토

### 7단계: 티스토리 발행
- src/tistory/publisher.py로 Playwright 발행
- 카테고리/태그 자동 설정
- 발행 완료 후 URL 반환

## 사용법
```
/publish                    # 자동 키워드 선정 후 발행
/publish "비타민D 효능"      # 특정 키워드로 발행
/publish --dry-run          # 발행 없이 미리보기만
```
