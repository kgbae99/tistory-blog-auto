# 30일 블로그 수익화 플랜

## 하루 루틴 (자동화 완료)

```
07:00 KST — GitHub Actions 자동 실행
  STEP 1: 키워드 20개 생성 (GPT-4o, ~30초)
  STEP 2: 상위 3개 필터링 (즉시)
  STEP 3: 초안 3개 생성 (GPT-4.1-mini, ~3분)
  STEP 4: 수익형 리라이팅 + HTML 조립 (GPT-4o, ~3분/건)
  COLOR:  GSC 색인 요청 (일 200건 한도)
  DONE:   output/posts/YYYY-MM-DD/ 에 HTML 3개 저장 + git push
```

총 소요: 약 15분 / 하루 / API 비용 ~$0.30~0.50

---

## 30일 누적 목표

| 구간 | 건강 블로그 | IT 블로그 | 누적 합계 |
|------|------------|----------|----------|
| 1~10일 | +30개 | +30개 | 60개 |
| 11~20일 | +30개 | +30개 | 120개 |
| 21~30일 | +30개 | +30개 | 180개 |

> 현재 건강 블로그 공개 336개 기준 → 30일 후 366개 목표

---

## 포스트 유형 비율 (자동 적용)

| 유형 | 비율 | 목적 |
|------|------|------|
| 수익형 (revenue) | 60% | 쿠팡 상품 + 광고 클릭 직결 |
| 정보형 (info) | 40% | 검색 유입 + 체류시간 확보 |

하루 3개 기준 → 수익형 2개 + 정보형 1개

---

## 내부 링크 자동화

- step3 실행 시 `src/content/internal_links.py`가 자동으로 연결
- 기준: 키워드 유사도 + 카테고리 매칭 → 상위 2개 자동 삽입
- 크롤링 DB: `data/blog_posts_index.json` (94개 → 매일 갱신)

---

## 수익 시뮬레이션 (30일 후)

| 항목 | 예상치 |
|------|--------|
| 일일 유입 (검색) | +50~100 PV/일 (30일 후) |
| 애드센스 RPM | 500~1,500원/1000PV |
| 쿠팡 전환율 | 0.5~2% |
| 월 예상 수익 | 3~10만원 (6개월 후 30~100만원 목표) |

---

## 품질 관리 기준

- step4 품질 점수 **5/5** 필수 (자동 체크)
- 제목: 연도 금지 / 클릭 유도형 필수
- 광고: 문제 인식 직후 / 해결 직후 / 결론 직전 고정
- 선택 구조: 상품 앞에 "이런 분 → A / 저런 분 → B" 삽입

---

## 실행 명령 (수동 실행 시)

```bash
# 건강 블로그 3개
python scripts/step1_keywords.py --blog health --count 20
python scripts/step2_filter.py   --blog health --top 3
python scripts/step3_generate.py --blog health
python scripts/step4_rewrite.py  --blog health

# IT 블로그 3개
python scripts/step1_keywords.py --blog it --count 20
python scripts/step2_filter.py   --blog it --top 3
python scripts/step3_generate.py --blog it
python scripts/step4_rewrite.py  --blog it
```
