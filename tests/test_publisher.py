"""티스토리 발행 모듈 테스트."""

from __future__ import annotations

import pytest

from src.adsense.ad_inserter import generate_ad_code, insert_ads_into_html
from src.core.config import AdsenseConfig
from src.tistory.publisher import PostData


class TestPostData:
    def test_create_post_data(self) -> None:
        post = PostData(
            title="테스트 포스트",
            content_html="<h2>테스트</h2><p>내용</p>",
            category="건강정보",
            tags=["테스트", "건강"],
            visibility="public",
        )
        assert post.title == "테스트 포스트"
        assert post.visibility == "public"
        assert len(post.tags) == 2

    def test_default_values(self) -> None:
        post = PostData(title="제목", content_html="<p>내용</p>")
        assert post.category == ""
        assert post.tags is None
        assert post.visibility == "public"


class TestAdInserter:
    @pytest.fixture
    def adsense_config(self) -> AdsenseConfig:
        return AdsenseConfig(
            pub_id="ca-pub-test123",
            gtag_id="G-TEST123",
            ad_positions=["after_first_h2", "after_third_h2", "before_conclusion"],
        )

    def test_generate_ad_code(self, adsense_config: AdsenseConfig) -> None:
        code = generate_ad_code(adsense_config)
        assert "adsbygoogle" in code
        assert "ca-pub-test123" in code

    def test_generate_infeed_ad(self, adsense_config: AdsenseConfig) -> None:
        code = generate_ad_code(adsense_config, ad_type="infeed")
        assert "fluid" in code
        assert "ca-pub-test123" in code

    def test_insert_ads_after_h2(self, adsense_config: AdsenseConfig) -> None:
        html = """
        <h2>첫 번째 섹션</h2>
        <p>내용1</p>
        <h2>두 번째 섹션</h2>
        <p>내용2</p>
        <h2>세 번째 섹션</h2>
        <p>내용3</p>
        <h2>결론</h2>
        <p>마무리</p>
        """
        result = insert_ads_into_html(html, adsense_config, ["after_first_h2", "after_third_h2"])
        assert result.count("ads-wrap") == 2

    def test_insert_no_ads_without_h2(self, adsense_config: AdsenseConfig) -> None:
        html = "<p>H2가 없는 간단한 콘텐츠</p>"
        result = insert_ads_into_html(html, adsense_config, ["after_first_h2"])
        assert "adsbygoogle" not in result

    def test_insert_before_conclusion(self, adsense_config: AdsenseConfig) -> None:
        html = """
        <h2>본문</h2>
        <p>내용</p>
        <h2>결론</h2>
        <p>마무리</p>
        """
        result = insert_ads_into_html(html, adsense_config, ["before_conclusion"])
        assert "adsbygoogle" in result
