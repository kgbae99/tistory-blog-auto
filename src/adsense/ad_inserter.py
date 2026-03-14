"""애드센스 광고 자동 삽입 모듈."""

from __future__ import annotations

import re

from src.core.config import AdsenseConfig
from src.core.logger import setup_logger

logger = setup_logger("adsense")

# 반응형 애드센스 광고 코드 템플릿
AD_TEMPLATE = """<div class="ads-wrap" style="margin: 20px 0; text-align: center;">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-client="{pub_id}"
       data-ad-slot="auto"
       data-ad-format="auto"
       data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>"""

# 인피드 광고 템플릿
INFEED_AD_TEMPLATE = """<div class="ads-wrap-infeed" style="margin: 15px 0;">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-format="fluid"
       data-ad-layout-key="auto"
       data-ad-client="{pub_id}"
       data-ad-slot="auto"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>"""


def generate_ad_code(config: AdsenseConfig, ad_type: str = "responsive") -> str:
    """애드센스 광고 코드를 생성한다."""
    if ad_type == "infeed":
        return INFEED_AD_TEMPLATE.format(pub_id=config.pub_id)
    return AD_TEMPLATE.format(pub_id=config.pub_id)


def insert_ads_into_html(
    html: str,
    config: AdsenseConfig,
    positions: list[str] | None = None,
) -> str:
    """HTML 콘텐츠에 애드센스 광고를 삽입한다.

    positions: ["after_first_h2", "after_third_h2", "before_conclusion"]
    """
    if positions is None:
        positions = config.ad_positions

    ad_code = generate_ad_code(config)

    # H2 태그 위치 찾기
    h2_pattern = re.compile(r"(</h2>)", re.IGNORECASE)
    h2_positions = list(h2_pattern.finditer(html))

    inserted_count = 0
    offset = 0

    for position in positions:
        if position == "after_first_h2" and len(h2_positions) >= 1:
            idx = h2_positions[0].end() + offset
            html = html[:idx] + "\n" + ad_code + "\n" + html[idx:]
            offset += len(ad_code) + 2
            inserted_count += 1

        elif position == "after_third_h2" and len(h2_positions) >= 3:
            idx = h2_positions[2].end() + offset
            html = html[:idx] + "\n" + ad_code + "\n" + html[idx:]
            offset += len(ad_code) + 2
            inserted_count += 1

        elif position == "before_conclusion":
            # 마지막 H2 앞에 삽입
            last_h2 = re.search(r"<h2[^>]*>[^<]*(?:결론|마무리|정리|마치며)", html, re.IGNORECASE)
            if last_h2:
                idx = last_h2.start()
                html = html[:idx] + ad_code + "\n" + html[idx:]
                inserted_count += 1

    # 최대 광고 수 제한 (애드센스 정책)
    if inserted_count > 3:
        logger.warning("광고 수 3개 초과, 정책 위반 주의")

    logger.info("애드센스 광고 %d개 삽입 완료", inserted_count)
    return html
