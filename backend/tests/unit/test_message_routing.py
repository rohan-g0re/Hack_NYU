"""
Unit tests for message routing and mention parsing.

WHAT: Test mention extraction and name normalization
WHY: Ensure correct routing of messages to sellers
HOW: Test regex parsing and edge cases
"""

import pytest
from app.services.message_router import parse_mentions
from app.models.agent import Seller, SellerProfile, InventoryItem


@pytest.fixture
def sample_sellers():
    """Sample sellers for testing."""
    return [
        Seller(
            seller_id="seller1",
            name="Alice",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[]
        ),
        Seller(
            seller_id="seller2",
            name="Bob",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
            inventory=[]
        ),
        Seller(
            seller_id="seller3",
            name="Charlie",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[]
        )
    ]


def test_parse_mentions_single(sample_sellers):
    """Test parsing single mention."""
    text = "Hello @Alice, can you help me?"
    mentions = parse_mentions(text, sample_sellers)
    
    assert len(mentions) == 1
    assert "seller1" in mentions


def test_parse_mentions_multiple(sample_sellers):
    """Test parsing multiple mentions."""
    text = "Hi @Alice and @Bob, I need your help."
    mentions = parse_mentions(text, sample_sellers)
    
    assert len(mentions) == 2
    assert "seller1" in mentions
    assert "seller2" in mentions


def test_parse_mentions_case_insensitive(sample_sellers):
    """Test case-insensitive matching."""
    text = "Hello @alice and @BOB"
    mentions = parse_mentions(text, sample_sellers)
    
    assert len(mentions) == 2
    assert "seller1" in mentions
    assert "seller2" in mentions


def test_parse_mentions_no_mentions(sample_sellers):
    """Test text with no mentions."""
    text = "Hello everyone, can anyone help?"
    mentions = parse_mentions(text, sample_sellers)
    
    assert len(mentions) == 0


def test_parse_mentions_invalid_mention(sample_sellers):
    """Test invalid mention (not a seller)."""
    text = "Hello @UnknownSeller"
    mentions = parse_mentions(text, sample_sellers)
    
    assert len(mentions) == 0


def test_parse_mentions_empty_text(sample_sellers):
    """Test empty text."""
    mentions = parse_mentions("", sample_sellers)
    assert len(mentions) == 0


def test_parse_mentions_empty_sellers():
    """Test with no sellers."""
    mentions = parse_mentions("Hello @Alice", [])
    assert len(mentions) == 0


def test_parse_mentions_duplicate_mentions(sample_sellers):
    """Test duplicate mentions return unique IDs."""
    text = "Hi @Alice, @Alice, @Bob"
    mentions = parse_mentions(text, sample_sellers)
    
    assert len(mentions) == 2  # Should be unique
    assert "seller1" in mentions
    assert "seller2" in mentions


def test_parse_mentions_with_underscores():
    """Test mentions with underscores."""
    sellers = [
        Seller(
            seller_id="seller1",
            name="Alice_Smith",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[]
        )
    ]
    
    text = "Hello @Alice_Smith"
    mentions = parse_mentions(text, sellers)
    
    assert len(mentions) == 1
    assert "seller1" in mentions

