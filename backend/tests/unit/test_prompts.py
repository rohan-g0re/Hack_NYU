"""
Unit tests for prompt templates.

WHAT: Test prompt rendering and content validation
WHY: Ensure prompts contain required constraints and style cues
HOW: Assert presence of keywords and structure
"""

import pytest
from app.agents.prompts import render_buyer_prompt, render_seller_prompt
from app.models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem


@pytest.fixture
def sample_buyer_constraints():
    """Sample buyer constraints."""
    return BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )


@pytest.fixture
def sample_seller():
    """Sample seller configuration."""
    return Seller(
        seller_id="seller1",
        name="Alice",
        profile=SellerProfile(
            priority="customer_retention",
            speaking_style="very_sweet"
        ),
        inventory=[
            InventoryItem(
                item_id="item1",
                item_name="Widget",
                cost_price=8.0,
                selling_price=18.0,
                least_price=12.0,
                quantity_available=10
            )
        ]
    )


def test_render_buyer_prompt_structure(sample_buyer_constraints):
    """Test buyer prompt has correct structure."""
    sellers = []
    messages = render_buyer_prompt(
        buyer_name="Bob",
        constraints=sample_buyer_constraints,
        conversation_history=[],
        available_sellers=sellers
    )
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_render_buyer_prompt_constraints(sample_buyer_constraints):
    """Test buyer prompt includes constraints."""
    sellers = []
    messages = render_buyer_prompt(
        buyer_name="Bob",
        constraints=sample_buyer_constraints,
        conversation_history=[],
        available_sellers=sellers
    )
    
    system_prompt = messages[0]["content"]
    
    # Check for constraint keywords
    assert "Widget" in system_prompt
    assert "5" in system_prompt  # quantity
    assert "$10.00" in system_prompt or "10.0" in system_prompt
    assert "$20.00" in system_prompt or "20.0" in system_prompt


def test_render_buyer_prompt_mention_convention(sample_buyer_constraints):
    """Test buyer prompt mentions @SellerName convention."""
    sellers = [
        Seller(
            seller_id="s1",
            name="Alice",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[]
        )
    ]
    
    messages = render_buyer_prompt(
        buyer_name="Bob",
        constraints=sample_buyer_constraints,
        conversation_history=[],
        available_sellers=sellers
    )
    
    system_prompt = messages[0]["content"]
    
    # Check for mention convention
    assert "@" in system_prompt or "@Alice" in system_prompt
    assert "mention" in system_prompt.lower()


def test_render_seller_prompt_structure(sample_seller, sample_buyer_constraints):
    """Test seller prompt has correct structure."""
    messages = render_seller_prompt(
        seller=sample_seller,
        constraints=sample_buyer_constraints,
        conversation_history=[],
        buyer_name="Bob"
    )
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_render_seller_prompt_inventory_bounds(sample_seller, sample_buyer_constraints):
    """Test seller prompt includes inventory pricing bounds."""
    messages = render_seller_prompt(
        seller=sample_seller,
        constraints=sample_buyer_constraints,
        conversation_history=[],
        buyer_name="Bob"
    )
    
    system_prompt = messages[0]["content"]
    
    # Check for pricing constraints
    assert "12.00" in system_prompt or "12.0" in system_prompt  # least_price
    assert "18.00" in system_prompt or "18.0" in system_prompt  # selling_price
    assert "cannot go below" in system_prompt.lower() or "minimum" in system_prompt.lower()


def test_render_seller_prompt_style(sample_seller, sample_buyer_constraints):
    """Test seller prompt reflects speaking style."""
    messages = render_seller_prompt(
        seller=sample_seller,
        constraints=sample_buyer_constraints,
        conversation_history=[],
        buyer_name="Bob"
    )
    
    system_prompt = messages[0]["content"]
    
    # Check for style instruction
    assert "sweet" in system_prompt.lower() or "friendly" in system_prompt.lower()


def test_render_seller_prompt_priority(sample_seller, sample_buyer_constraints):
    """Test seller prompt reflects priority."""
    messages = render_seller_prompt(
        seller=sample_seller,
        constraints=sample_buyer_constraints,
        conversation_history=[],
        buyer_name="Bob"
    )
    
    system_prompt = messages[0]["content"]
    
    # Check for priority instruction
    assert "customer" in system_prompt.lower() or "retention" in system_prompt.lower()


def test_render_seller_prompt_offer_format(sample_seller, sample_buyer_constraints):
    """Test seller prompt includes JSON offer format hint."""
    messages = render_seller_prompt(
        seller=sample_seller,
        constraints=sample_buyer_constraints,
        conversation_history=[],
        buyer_name="Bob"
    )
    
    system_prompt = messages[0]["content"]
    
    # Check for JSON offer format
    assert "json" in system_prompt.lower() or "offer" in system_prompt.lower()

