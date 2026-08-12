"""
Tests for SEO Analysis Module
"""
import pytest
from app.seo_analysis import analyze_seo_html, ISSUE_CONFIG, ISSUE_IMPACT


class TestSeoAnalysis:
    """Tests for the centralized SEO analysis logic"""
    
    def test_perfect_page_score_100(self):
        """A page with all SEO elements should score 100"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Best Product - Shop Now | Brand Name</title>
            <meta name="description" content="Buy the best product online. Free shipping, great prices, and excellent customer service. Shop now and save!">
            <link rel="canonical" href="https://example.com/product">
            <meta property="og:title" content="Best Product">
            <meta property="og:description" content="Buy now">
            <meta property="og:image" content="https://example.com/image.jpg">
            <script type="application/ld+json">{"@type": "Product"}</script>
        </head>
        <body>
            <h1>Best Product</h1>
            <h2>Product Features</h2>
            <img src="image.jpg" alt="Product image">
            <a href="/related">Related</a>
            <a href="/category">Category</a>
            <a href="/home">Home</a>
        </body>
        </html>
        """
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["score"] == 100
        assert len(result["issues"]) == 0
        assert result["title"] == "Best Product - Shop Now | Brand Name"
        assert result["h1"] == "Best Product"
        assert result["has_canonical"] is True
        assert result["has_schema"] is True
        assert result["has_og_tags"] is True
    
    def test_missing_title_penalty(self):
        """Missing title should apply penalty"""
        html = "<html><head></head><body><h1>Hello</h1></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("missing_title") is True
        expected_penalty = ISSUE_CONFIG["missing_title"]["penalty"]
        assert result["score"] <= 100 - expected_penalty
    
    def test_title_length_issue(self):
        """Title too short flags title_too_short (alto); too long flags title_too_long (medio)"""
        # Too short
        html = "<html><head><title>Hi</title></head><body></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        assert result["issues"].get("title_too_short") is True
        assert ISSUE_IMPACT.get("title_too_short") == "alto"

        # Too long
        long_title = "A" * 100
        html = f"<html><head><title>{long_title}</title></head><body></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        assert result["issues"].get("title_too_long") is True
        assert ISSUE_IMPACT.get("title_too_long") == "medio"
    
    def test_missing_meta_description(self):
        """Missing meta description should be flagged"""
        html = "<html><head><title>Test Title Here OK</title></head><body></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("missing_meta_description") is True
        assert result["meta_description"] is None
    
    def test_missing_h1(self):
        """Missing H1 should be flagged"""
        html = "<html><head><title>Test Title Here OK</title></head><body><p>No heading</p></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("missing_h1") is True
        assert result["h1"] is None
    
    def test_multiple_h1(self):
        """Multiple H1 tags should be flagged"""
        html = """
        <html><head><title>Test Title Here OK</title></head>
        <body><h1>First</h1><h1>Second</h1></body>
        </html>
        """
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("multiple_h1") is True
    
    def test_missing_canonical(self):
        """Missing canonical link should be flagged"""
        html = "<html><head><title>Test Title Here OK</title></head><body></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("missing_canonical") is True
        assert result["has_canonical"] is False
    
    def test_noindex_detected(self):
        """Noindex meta tag should be flagged"""
        html = """
        <html><head>
            <title>Test Title Here OK</title>
            <meta name="robots" content="noindex, nofollow">
        </head><body></body></html>
        """
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("noindex_detected") is True
    
    def test_missing_img_alt(self):
        """Images without alt text should be flagged"""
        html = """
        <html><head><title>Test Title Here OK</title></head>
        <body><img src="test.jpg"><img src="test2.jpg"></body>
        </html>
        """
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("missing_img_alt") is True
        assert result["images_without_alt"] == 2
    
    def test_few_internal_links(self):
        """Pages with few internal links should be flagged"""
        html = """
        <html><head><title>Test Title Here OK</title></head>
        <body>
            <a href="https://external.com">External</a>
        </body>
        </html>
        """
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("few_internal_links") is True
    
    def test_missing_og_tags(self):
        """Missing Open Graph tags should be flagged"""
        html = "<html><head><title>Test Title Here OK</title></head><body></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("missing_og_tags") is True
        assert result["has_og_tags"] is False
    
    def test_missing_schema(self):
        """Missing Schema.org JSON-LD should be flagged"""
        html = "<html><head><title>Test Title Here OK</title></head><body></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["issues"].get("missing_schema") is True
        assert result["has_schema"] is False
    
    def test_score_never_below_zero(self):
        """Score should never go below 0 even with many issues"""
        html = "<html><head></head><body></body></html>"
        result = analyze_seo_html(html, "https://example.com")
        
        assert result["score"] >= 0


class TestIssueConfig:
    """Tests for ISSUE_CONFIG consistency"""
    
    def test_all_issues_have_penalty(self):
        """All issues should have a penalty defined"""
        for issue_code, config in ISSUE_CONFIG.items():
            assert "penalty" in config, f"Missing penalty for {issue_code}"
            assert isinstance(config["penalty"], int), f"Penalty should be int for {issue_code}"
            assert config["penalty"] > 0, f"Penalty should be positive for {issue_code}"
    
    def test_all_issues_have_message(self):
        """All issues should have a message defined"""
        for issue_code, config in ISSUE_CONFIG.items():
            assert "message" in config, f"Missing message for {issue_code}"
            assert len(config["message"]) > 0, f"Message should not be empty for {issue_code}"
    
    def test_total_penalty_reasonable(self):
        """Total of all penalties should not exceed 100 by too much"""
        total = sum(config["penalty"] for config in ISSUE_CONFIG.values())
        # Allow some buffer since not all issues can occur simultaneously
        assert total < 200, f"Total penalties ({total}) seem too high"
