"""애드센스 광고 자동 삽입 모듈."""

from __future__ import annotations

import re

from src.core.config import AdsenseConfig
from src.core.logger import setup_logger

logger = setup_logger("adsense")

# 반응형 애드센스 광고 코드 템플릿
AD_TEMPLATE = """<div class="ads-wrap" style="margin: 25px 0; text-align: center; clear: both;">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-client="{pub_id}"
       data-ad-slot="{slot_id}"
       data-ad-format="auto"
       data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>"""

# 인피드 광고 템플릿 (본문 중간용)
INFEED_AD_TEMPLATE = """<div class="ads-wrap-infeed" style="margin: 20px 0; clear: both;">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-format="fluid"
       data-ad-layout-key="-fb+5w+4e-db+86"
       data-ad-client="{pub_id}"
       data-ad-slot="{slot_id}"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>"""


def generate_ad_code(
    config: AdsenseConfig, position_index: int = 0, ad_type: str = "responsive"
) -> str:
    """애드센스 광고 코드를 생성한다.

    Args:
        config: 애드센스 설정
        position_index: 광고 위치 인덱스 (0=상단, 1=중간, 2=하단)
        ad_type: 광고 유형 (responsive 또는 infeed)
    """
    slot_id = ""
    if config.ad_slots and position_index < len(config.ad_slots):
        slot_id = config.ad_slots[position_index]

    if not slot_id:
        slot_id = "auto"

    if not config.pub_id:
        logger.warning("ADSENSE_PUB_ID가 설정되지 않았습니다")
        return ""

    if ad_type == "infeed":
        return INFEED_AD_TEMPLATE.format(pub_id=config.pub_id, slot_id=slot_id)
    return AD_TEMPLATE.format(pub_id=config.pub_id, slot_id=slot_id)


def insert_ads_into_html(
    html: str,
    config: AdsenseConfig,
    positions: list[str] | None = None,
) -> str:
    """HTML 콘텐츠에 애드센스 광고를 삽입한다.

    positions: ["after_first_h2", "after_third_h2", "before_conclusion"]
    """
    if not config.pub_id:
        logger.warning("ADSENSE_PUB_ID 미설정 → 광고 삽입 건너뜀")
        return html

    if positions is None:
        positions = config.ad_positions

    h2_pattern = re.compile(r"(</h2>)", re.IGNORECASE)
    h2_positions = list(h2_pattern.finditer(html))

    inserted_count = 0
    offset = 0

    for position in positions:
        if position == "after_first_h2" and len(h2_positions) >= 1:
            ad_code = generate_ad_code(config, position_index=0)
            idx = h2_positions[0].end() + offset
            html = html[:idx] + "\n" + ad_code + "\n" + html[idx:]
            offset += len(ad_code) + 2
            inserted_count += 1

        elif position == "after_third_h2" and len(h2_positions) >= 3:
            ad_code = generate_ad_code(config, position_index=1, ad_type="infeed")
            idx = h2_positions[2].end() + offset
            html = html[:idx] + "\n" + ad_code + "\n" + html[idx:]
            offset += len(ad_code) + 2
            inserted_count += 1

        elif position == "before_conclusion":
            last_h2 = re.search(
                r"<h2[^>]*>[^<]*(?:결론|마무리|정리|마치며)", html, re.IGNORECASE
            )
            if last_h2:
                ad_code = generate_ad_code(config, position_index=2)
                idx = last_h2.start()
                html = html[:idx] + ad_code + "\n" + html[idx:]
                inserted_count += 1

    if inserted_count > 3:
        logger.warning("광고 수 3개 초과, 정책 위반 주의")

    logger.info("애드센스 광고 %d개 삽입 완료", inserted_count)
    return html
