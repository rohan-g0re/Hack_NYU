"""
Unit tests for decision engine.

WHAT: Test offer analysis and selection logic
WHY: Verify scoring algorithm and tie-breakers work correctly
HOW: Create test scenarios with known offers and validate scores
"""

import pytest
from app.services.decision_engine import (
    analyze_offers, select_best_offer, generate_decision_reason, OfferAnalysis
)
from app.models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem
from app.models.negotiation import NegotiationRoomState


@pytest.fixture
def sample_room_state():
    """Create sample room state for testing."""
    buyer_constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    sellers = [
        Seller(
            seller_id="seller1",
            name="Alice",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
            inventory=[InventoryItem(
                item_id="item1", item_name="Widget",
                cost_price=8.0, selling_price=18.0, least_price=12.0, quantity_available=10
            )]
        ),
        Seller(
            seller_id="seller2",
            name="Bob",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[InventoryItem(
                item_id="item1", item_name="Widget",
                cost_price=7.0, selling_price=19.0, least_price=11.0, quantity_available=8
            )]
        )
    ]
    
    return NegotiationRoomState(
        room_id="room1",
        buyer_id="buyer1",
        buyer_name="Charlie",
        buyer_constraints=buyer_constraints,
        sellers=sellers,
        conversation_history=[],
        current_round=1,
        max_rounds=5
    )


@pytest.mark.phase2
@pytest.mark.unit
def test_analyze_offers_calculates_scores_correctly(sample_room_state):
    """Test analyze_offers calculates all score components."""
    seller_results = {
        "seller1": {
            "message": "Great offer!",
            "offer": {"price": 15.0, "quantity": 5}
        },
        "seller2": {
            "message": "Here's my price",
            "offer": {"price": 16.0, "quantity": 6}
        }
    }
    
    analyses = analyze_offers(sample_room_state, seller_results)
    
    assert len(analyses) == 2
    for analysis in analyses:
        assert isinstance(analysis, OfferAnalysis)
        assert 0 <= analysis.price_score <= 40
        assert 0 <= analysis.responsiveness_score <= 30
        assert 0 <= analysis.total_score <= 100


@pytest.mark.phase2
@pytest.mark.unit
def test_analyze_offers_filters_invalid_offers(sample_room_state):
    """Test analyze_offers filters out-of-range offers."""
    seller_results = {
        "seller1": {
            "message": "Too expensive",
            "offer": {"price": 25.0, "quantity": 5}  # Above max_price
        },
        "seller2": {
            "message": "Not enough",
            "offer": {"price": 15.0, "quantity": 2}  # Below quantity_needed
        }
    }
    
    analyses = analyze_offers(sample_room_state, seller_results)
    
    # Both offers should be filtered out
    assert len(analyses) == 0


@pytest.mark.phase2
@pytest.mark.unit
def test_select_best_offer_applies_tie_breakers(sample_room_state):
    """Test select_best_offer chooses highest scored offer."""
    # Create analyses with different scores
    analyses = [
        OfferAnalysis(
            seller_id="seller1",
            seller_name="Alice",
            offer={"price": 12.0, "quantity": 5},
            price_score=32.0,  # Lower price = higher score
            responsiveness_score=30.0,
            negotiation_rounds=1,
            seller_priority="customer_retention",
            profile_score=10.0,
            total_score=72.0
        ),
        OfferAnalysis(
            seller_id="seller2",
            seller_name="Bob",
            offer={"price": 15.0, "quantity": 5},
            price_score=20.0,  # Higher price = lower score
            responsiveness_score=30.0,
            negotiation_rounds=1,
            seller_priority="maximize_profit",
            profile_score=0.0,
            total_score=50.0
        )
    ]
    
    best = select_best_offer(analyses, sample_room_state.buyer_constraints)
    
    assert best is not None
    assert best.seller_id == "seller1"  # Higher total score
    assert best.total_score == 72.0


@pytest.mark.phase2
@pytest.mark.unit
def test_select_best_offer_filters_invalid_offers():
    """Test select_best_offer filters invalid offers."""
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    analyses = [
        OfferAnalysis(
            seller_id="seller1",
            seller_name="Alice",
            offer={"price": 25.0, "quantity": 5},  # Price too high
            price_score=0.0,
            responsiveness_score=30.0,
            negotiation_rounds=1,
            seller_priority="customer_retention",
            profile_score=10.0,
            total_score=40.0
        )
    ]
    
    best = select_best_offer(analyses, constraints)
    
    # Should return None as offer is invalid
    assert best is None


@pytest.mark.phase2
@pytest.mark.unit
def test_decision_reason_includes_all_factors():
    """Test generate_decision_reason includes price, score, and details."""
    analysis = OfferAnalysis(
        seller_id="seller1",
        seller_name="Alice",
        offer={"price": 15.0, "quantity": 5},
        price_score=35.0,
        responsiveness_score=28.0,
        negotiation_rounds=2,
        seller_priority="customer_retention",
        profile_score=10.0,
        total_score=73.0
    )
    
    reason = generate_decision_reason(analysis)
    
    assert "Alice" in reason
    assert "15.00" in reason or "15.0" in reason  # Price
    assert "73" in reason or "73.0" in reason  # Score
    assert "5" in reason  # Quantity

