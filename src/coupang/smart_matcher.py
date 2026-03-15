"""쿠팡 스마트 상품 매칭 - 키워드별 고수익 카테고리 자동 선정."""

from __future__ import annotations

from src.core.logger import setup_logger

logger = setup_logger("smart_matcher")

# 키워드 → 고수익 쿠팡 검색어 매핑
# 수수료율이 높고 전환율이 좋은 상품 중심
KEYWORD_PRODUCT_MAP: dict[str, list[str]] = {
    # 건강/영양
    "알레르기": ["알레르기 비염약", "공기청정기 필터", "KF94 마스크"],
    "꽃가루": ["비강세척기", "공기청정기", "알레르기 비염 스프레이"],
    "춘곤증": ["비타민B 영양제", "홍삼 스틱", "에너지 보충제"],
    "미세먼지": ["공기청정기", "KF94 마스크", "미세먼지 측정기"],
    "다이어트": ["다이어트 보조제", "체중계", "단백질 쉐이크"],
    "식단": ["도시락통", "식단 관리 앱 쿠폰", "현미"],
    "비타민": ["종합비타민", "비타민D", "비타민C"],
    "면역력": ["유산균", "프로폴리스", "홍삼"],
    "수면": ["수면 안대", "멜라토닌", "메모리폼 베개"],
    "혈압": ["혈압계", "오메가3", "코엔자임Q10"],
    "당뇨": ["혈당측정기", "당뇨식", "여주차"],
    "관절": ["글루코사민", "관절보호대", "MSM"],
    "간": ["밀크시슬", "간건강 영양제", "헛개수"],
    "눈": ["루테인", "눈 마사지기", "블루라이트 차단 안경"],
    "피로": ["비타민B 컴플렉스", "마카", "아르기닌"],
    "해독": ["클렌즈주스", "유산균", "해독차"],
    "장건강": ["프로바이오틱스", "유산균", "식이섬유"],
    "뼈": ["칼슘 마그네슘", "비타민D", "뼈건강 영양제"],
    # 뷰티/스킨케어
    "피부": ["세럼", "수분크림", "선크림"],
    "스킨케어": ["토너", "에센스", "클렌징폼"],
    "자외선": ["선크림 SPF50", "UV 차단 모자", "선스틱"],
    "보습": ["수분크림", "히알루론산 세럼", "바디로션"],
    "모공": ["모공 세럼", "클레이 마스크", "토너패드"],
    "여드름": ["여드름 패치", "살리실산 클렌저", "시카크림"],
    # 생활
    "공기": ["공기청정기", "가습기", "에어컨 필터"],
    "운동": ["요가매트", "덤벨", "운동화"],
    "스트레스": ["아로마 디퓨저", "마사지건", "명상 쿠션"],
    "봄나물": ["봄나물 세트", "유기농 채소", "샐러드 키트"],
    # 정부지원/복지
    "정부지원": ["가계부", "재테크 도서", "통장 관리"],
}

# 고수익 카테고리 (쿠팡 수수료 3% 기준, 가격대가 높은 상품)
HIGH_VALUE_PRODUCTS = [
    "공기청정기", "혈압계", "혈당측정기", "안마의자", "마사지건",
    "종합비타민 대용량", "홍삼 선물세트", "눈 마사지기",
    "체중계", "체성분분석기",
]


def get_search_queries(keyword: str, count: int = 3) -> list[str]:
    """키워드에 맞는 쿠팡 검색어를 반환한다.

    Args:
        keyword: 포커스 키워드
        count: 반환할 검색어 수

    Returns:
        쿠팡 검색어 리스트
    """
    keyword_lower = keyword.lower()
    queries: list[str] = []

    # 직접 매칭
    for key, products in KEYWORD_PRODUCT_MAP.items():
        if key in keyword_lower:
            queries.extend(products)

    # 중복 제거
    seen: set[str] = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    if not unique:
        # 매칭 안 되면 키워드 자체로 검색
        unique = [keyword, f"{keyword} 추천", f"{keyword} 영양제"]

    result = unique[:count]
    logger.info("스마트 매칭: '%s' → %s", keyword, result)
    return result


def prioritize_high_value(products: list, count: int = 3) -> list:
    """고수익 상품을 우선 선택한다."""
    high = []
    normal = []

    for p in products:
        name = p.product_name if hasattr(p, "product_name") else str(p)
        is_high = any(hv in name for hv in HIGH_VALUE_PRODUCTS)
        if is_high:
            high.append(p)
        else:
            normal.append(p)

    # 고수익 상품 우선, 나머지로 채움
    result = high[:count]
    remaining = count - len(result)
    if remaining > 0:
        result.extend(normal[:remaining])

    return result[:count]
