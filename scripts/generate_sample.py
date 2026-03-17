"""기존 블로그 스타일에 맞춘 샘플 포스트 생성."""

import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT = """당신은 "건강온도사(행복++)" 티스토리 블로그의 전문 콘텐츠 작가입니다.

## 기존 글 스타일 (반드시 이 스타일을 따르세요)

### 예시1 제목: "뼈가 약해졌다면 지금 꼭 챙기세요"
H2 섹션들: 칼슘이 풍부한 식품 / 비타민 D의 역할 / 규칙적인 운동 / 식단에서 피해야 할 음식 / 스트레스 관리 / 뼈 건강을 위한 보충제
- 각 섹션 150~250자, 친근한 존댓말
- 마지막에 면책문 + 쿠팡 고지문

### 예시2 제목: "간을 망치는 음식, 혹시 매일 드시나요?"
H2 섹션들: 간 건강의 중요성 / 가공식품과 간 건강 / 알코올의 위험성 / 설탕과 간의 관계 / 트랜스지방과 간 건강 / 결론
- 관련 포스트 내부링크 2개를 본문 중간에 자연스럽게 삽입

### 예시3 제목: "1일 1식단, 이걸로 건강 지켜냅니다"
H2 섹션들: 효능과 필요성 / 식사 구성 / 주의사항 / 성공 사례 / 실천 팁 / 꾸준함이 주는 혜택 / 마무리

## 글쓰기 규칙 (절대 규칙)
1. 제목: 짧고 강렬한 호기심 유발형 (15~25자)
2. H2 섹션 6~7개, H3는 절대 사용하지 않음
3. 각 섹션 150~300자, 짧은 문단 (2~3문장씩)
4. 문체: ~합니다/~세요/~요 존댓말, 친근하고 실용적
5. 불릿 포인트를 각 섹션에 적극 활용
6. 내부링크 2개를 본문 중간 섹션에 자연스럽게 삽입:
   - <a href="https://kgbae2369.tistory.com/16">관절에 좋은 음식 BEST 7</a>
   - <a href="https://kgbae2369.tistory.com/28">혈압 낮추는 식단 가이드</a>
7. 마지막 섹션 heading은 "마무리"로 작성
8. 쿠팡 추천 상품을 본문에서 자연스럽게 1~2회 언급 (노골적 광고 금지)
9. 태그 6~7개

## 이번 글 요청
- 키워드: "춘곤증 극복 방법"
- 카테고리: 건강 & 웰빙
- 쿠팡 추천 상품 (자연스럽게 언급): 비타민B 영양제, 홍삼 스틱

## 출력 형식
반드시 아래 JSON만 출력하세요. 다른 텍스트 없이 JSON만:

{"title":"제목","sections":[{"heading":"H2제목","content":"본문HTML"}],"disclaimer":"면책문+쿠팡고지HTML","tags":["태그"],"meta_description":"155자이내"}

content에는 <p>, <ul><li>, <strong>, <a> 태그를 사용하세요.
disclaimer에는 면책문과 쿠팡 파트너스 고지문을 포함하세요:
- ※ 본 글은 건강 정보를 요약한 것이며, 질병 치료 목적이 아닙니다.
- 📌 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."""


def main():
    print("Gemini 콘텐츠 생성 중...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROMPT,
    )

    text = response.text
    if "```json" in text:
        json_str = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        json_str = text.split("```")[1].split("```")[0]
    else:
        json_str = text

    data = json.loads(json_str.strip())

    print("=" * 60)
    print(f"  제목: {data['title']}")
    print(f"  메타: {data['meta_description']}")
    print(f"  섹션: {len(data['sections'])}개")
    print(f"  태그: {data['tags']}")
    print("=" * 60)

    for s in data["sections"]:
        print(f"\n<h2>{s['heading']}</h2>")
        preview = s["content"][:400]
        print(preview)
        if len(s["content"]) > 400:
            print("...")

    if "disclaimer" in data:
        print(f"\n---\n{data['disclaimer']}")

    # HTML 파일 저장
    html_parts = []
    for s in data["sections"]:
        html_parts.append(f"<h2>{s['heading']}</h2>")
        html_parts.append(s["content"])

    html_body = "\n".join(html_parts)
    if "disclaimer" in data:
        html_body += "\n" + data["disclaimer"]

    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    html_path = output_dir / "preview_춘곤증_스타일맞춤.html"
    html_path.write_text(
        f"<article>\n{html_body}\n</article>", encoding="utf-8"
    )

    json_path = output_dir / "preview_춘곤증_스타일맞춤.json"
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    total_chars = sum(len(s["content"]) for s in data["sections"])
    print(f"\n저장 완료:")
    print(f"  HTML: {html_path}")
    print(f"  JSON: {json_path}")
    print(f"  총 글자수: {total_chars}자")


if __name__ == "__main__":
    main()
