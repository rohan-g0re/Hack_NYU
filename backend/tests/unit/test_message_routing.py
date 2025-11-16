"""
Tests for message routing utilities.

WHAT: Test mention parsing and seller targeting
WHY: Ensure correct routing of buyer messages to sellers
HOW: Test various mention patterns and edge cases
"""

import pytest
from app.services.message_router import normalize_handle, parse_mentions, select_targets
from app.models.negotiation import SellerProfile


@pytest.mark.phase2
@pytest.mark.unit
class TestHandleNormalization:
    """Test handle normalization."""
    
    def test_lowercase_conversion(self):
        """Test that handles are lowercased."""
        assert normalize_handle("SellerOne") == "sellerone"
        assert normalize_handle("SELLER_TWO") == "seller_two"
    
    def test_space_removal(self):
        """Test that spaces are removed."""
        assert normalize_handle("Seller One") == "sellerone"
        assert normalize_handle("Big Seller Corp") == "bigsellercorp"
    
    def test_punctuation_removal(self):
        """Test that punctuation is removed except underscores."""
        assert normalize_handle("Seller-One") == "sellerone"
        assert normalize_handle("Seller.Two") == "sellertwo"
        assert normalize_handle("Seller_Three") == "seller_three"
    
    def test_multiple_underscores_collapsed(self):
        """Test that multiple underscores are collapsed."""
        assert normalize_handle("seller___one") == "seller_one"
        assert normalize_handle("a__b__c") == "a_b_c"
    
    def test_edge_cases(self):
        """Test edge cases."""
        assert normalize_handle("") == ""
        assert normalize_handle("___") == ""
        assert normalize_handle("123") == "123"


@pytest.mark.phase2
@pytest.mark.unit
class TestMentionParsing:
    """Test mention parsing from text."""
    
    def test_single_mention(self):
        """Test parsing single @mention."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="SellerOne")
        ]
        
        text = "Hi @SellerOne, can you help?"
        mentions = parse_mentions(text, sellers)
        
        assert mentions == ["s1"]
    
    def test_multiple_mentions(self):
        """Test parsing multiple @mentions."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="SellerOne"),
            SellerProfile(seller_id="s2", display_name="SellerTwo"),
            SellerProfile(seller_id="s3", display_name="SellerThree")
        ]
        
        text = "@SellerOne and @SellerThree please respond"
        mentions = parse_mentions(text, sellers)
        
        assert mentions == ["s1", "s3"]
    
    def test_case_insensitive_matching(self):
        """Test case-insensitive mention matching."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="SellerOne")
        ]
        
        text = "@sellerone @SELLERONE @SellerOne"
        mentions = parse_mentions(text, sellers)
        
        # Should deduplicate
        assert mentions == ["s1"]
    
    def test_spacing_variations(self):
        """Test handling of spacing variations in names."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="Big Seller Corp")
        ]
        
        text = "@BigSellerCorp can you help?"
        mentions = parse_mentions(text, sellers)
        
        assert mentions == ["s1"]
    
    def test_underscore_variations(self):
        """Test handling of underscores - both with and without match."""
        # Test that @Seller_One matches display_name="Seller_One"
        sellers = [
            SellerProfile(seller_id="s1", display_name="Seller_One")
        ]
        
        text = "@Seller_One please respond"
        mentions = parse_mentions(text, sellers)
        assert mentions == ["s1"]
        
        # Test that @SellerOne also matches display_name="Seller_One" after normalization
        text2 = "@SellerOne please respond"
        mentions2 = parse_mentions(text2, sellers)
        # This won't match because "sellerone" != "seller_one", which is expected behavior
        assert mentions2 == []
    
    def test_unknown_mentions_ignored(self):
        """Test that unknown mentions are ignored."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="SellerOne")
        ]
        
        text = "@SellerOne @UnknownSeller @AnotherUnknown"
        mentions = parse_mentions(text, sellers)
        
        assert mentions == ["s1"]
    
    def test_no_mentions(self):
        """Test text with no mentions."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="SellerOne")
        ]
        
        text = "Hello everyone, please send your best offers"
        mentions = parse_mentions(text, sellers)
        
        assert mentions == []
    
    def test_duplicate_mentions_deduplicated(self):
        """Test that duplicate mentions are deduplicated."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="SellerOne")
        ]
        
        text = "@SellerOne @SellerOne @SellerOne"
        mentions = parse_mentions(text, sellers)
        
        assert mentions == ["s1"]
    
    def test_mention_order_preserved(self):
        """Test that mention order is preserved."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="SellerOne"),
            SellerProfile(seller_id="s2", display_name="SellerTwo"),
            SellerProfile(seller_id="s3", display_name="SellerThree")
        ]
        
        text = "@SellerThree @SellerOne @SellerTwo"
        mentions = parse_mentions(text, sellers)
        
        assert mentions == ["s3", "s1", "s2"]
    
    def test_empty_text(self):
        """Test empty text."""
        sellers = [
            SellerProfile(seller_id="s1", display_name="SellerOne")
        ]
        
        mentions = parse_mentions("", sellers)
        assert mentions == []
    
    def test_empty_sellers_list(self):
        """Test with no sellers."""
        mentions = parse_mentions("@Someone help", [])
        assert mentions == []
    
    def test_mention_by_seller_id(self):
        """Test mentioning by seller_id works too."""
        sellers = [
            SellerProfile(seller_id="aggressive_seller", display_name="Aggressive Inc")
        ]
        
        text = "@aggressive_seller please respond"
        mentions = parse_mentions(text, sellers)
        
        assert mentions == ["aggressive_seller"]


@pytest.mark.phase2
@pytest.mark.unit
class TestTargetSelection:
    """Test seller target selection logic."""
    
    def test_mentioned_sellers_only(self):
        """Test routing to mentioned sellers only."""
        mentioned = ["s1", "s3"]
        active = ["s1", "s2", "s3", "s4"]
        
        targets = select_targets(mentioned, active, fallback_to_all=False)
        
        assert targets == ["s1", "s3"]
    
    def test_filters_inactive_sellers(self):
        """Test that inactive sellers are filtered out."""
        mentioned = ["s1", "s3", "s5"]
        active = ["s1", "s2", "s3"]  # s5 not active
        
        targets = select_targets(mentioned, active, fallback_to_all=False)
        
        assert targets == ["s1", "s3"]
    
    def test_fallback_to_all_when_no_mentions(self):
        """Test fallback to all active sellers when no mentions."""
        mentioned = []
        active = ["s1", "s2", "s3"]
        
        targets = select_targets(mentioned, active, fallback_to_all=True)
        
        assert targets == ["s1", "s2", "s3"]
    
    def test_no_fallback_returns_empty(self):
        """Test no fallback returns empty list."""
        mentioned = []
        active = ["s1", "s2", "s3"]
        
        targets = select_targets(mentioned, active, fallback_to_all=False)
        
        assert targets == []
    
    def test_all_mentioned_inactive(self):
        """Test when all mentioned sellers are inactive."""
        mentioned = ["s5", "s6"]
        active = ["s1", "s2", "s3"]
        
        # With fallback
        targets = select_targets(mentioned, active, fallback_to_all=True)
        assert targets == ["s1", "s2", "s3"]
        
        # Without fallback
        targets = select_targets(mentioned, active, fallback_to_all=False)
        assert targets == []

