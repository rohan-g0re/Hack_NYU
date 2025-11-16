"""
Decision engine tests for Phase 3.

WHAT: Test buyer decision validation and tie-breaking logic
WHY: Ensure chosen deals are valid and best offers are selected correctly
HOW: Test various offer scenarios with different price/quantity combinations
"""

import pytest
from app.services.decision_engine import validate_decision, select_best_offer, compute_total_cost
from app.models.agent import BuyerConstraints


@pytest.fixture
def sample_constraints():
    """Create sample buyer constraints."""
    return BuyerConstraints(
        item_id="laptop",
        item_name="Gaming Laptop",
        quantity_needed=2,
        min_price_per_unit=800.0,
        max_price_per_unit=1200.0
    )


class TestValidateDecision:
    """Test decision validation logic."""
    
    def test_validate_valid_offer(self, sample_constraints):
        """Test validation of a valid offer within constraints."""
        offer = {"price": 1000.0, "quantity": 2}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is True
        assert error is None
    
    def test_validate_offer_below_min_price(self, sample_constraints):
        """Test rejection of offer below minimum price."""
        offer = {"price": 700.0, "quantity": 2}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is False
        assert "below minimum" in error.lower()
        assert "800.00" in error
    
    def test_validate_offer_above_max_price(self, sample_constraints):
        """Test rejection of offer above maximum price."""
        offer = {"price": 1300.0, "quantity": 2}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is False
        assert "above maximum" in error.lower()
        assert "1200.00" in error
    
    def test_validate_offer_exceeds_quantity(self, sample_constraints):
        """Test rejection of offer with quantity exceeding needed."""
        offer = {"price": 1000.0, "quantity": 5}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is False
        assert "exceeds needed" in error.lower()
        assert "5" in error
        assert "2" in error
    
    def test_validate_offer_zero_quantity(self, sample_constraints):
        """Test rejection of offer with zero quantity."""
        offer = {"price": 1000.0, "quantity": 0}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is False
        assert "at least 1" in error.lower()
    
    def test_validate_offer_missing_price(self, sample_constraints):
        """Test rejection of offer missing price."""
        offer = {"quantity": 2}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is False
        assert "missing price" in error.lower()
    
    def test_validate_offer_missing_quantity(self, sample_constraints):
        """Test rejection of offer missing quantity."""
        offer = {"price": 1000.0}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is False
        assert "missing" in error.lower()
    
    def test_validate_no_offer(self, sample_constraints):
        """Test rejection when no offer is provided."""
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=None,
            buyer_constraints=sample_constraints,
            all_offers=[]
        )
        assert is_valid is False
        assert "no offer" in error.lower()
    
    def test_validate_exact_min_price(self, sample_constraints):
        """Test acceptance of offer at exact minimum price."""
        offer = {"price": 800.0, "quantity": 2}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is True
        assert error is None
    
    def test_validate_exact_max_price(self, sample_constraints):
        """Test acceptance of offer at exact maximum price."""
        offer = {"price": 1200.0, "quantity": 2}
        is_valid, error = validate_decision(
            selected_seller_id="seller1",
            final_offer=offer,
            buyer_constraints=sample_constraints,
            all_offers=[offer]
        )
        assert is_valid is True
        assert error is None


class TestSelectBestOffer:
    """Test tie-breaking and best offer selection."""
    
    def test_select_best_offer_single_valid(self, sample_constraints):
        """Test selection when only one valid offer exists."""
        offers = [
            {"seller_id": "seller1", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 3}
        ]
        best = select_best_offer(offers, sample_constraints)
        assert best is not None
        assert best["seller_id"] == "seller1"
        assert best["price"] == 1000.0
    
    def test_select_best_offer_lowest_price(self, sample_constraints):
        """Test selection of lowest price offer."""
        offers = [
            {"seller_id": "seller1", "price": 1100.0, "quantity": 2, "round_number": 1, "message_count": 3},
            {"seller_id": "seller2", "price": 900.0, "quantity": 2, "round_number": 1, "message_count": 2},
            {"seller_id": "seller3", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 4}
        ]
        best = select_best_offer(offers, sample_constraints, tie_breaker="price")
        assert best is not None
        assert best["seller_id"] == "seller2"
        assert best["price"] == 900.0
    
    def test_select_best_offer_filters_invalid(self, sample_constraints):
        """Test that invalid offers are filtered out."""
        offers = [
            {"seller_id": "seller1", "price": 700.0, "quantity": 2, "round_number": 1, "message_count": 3},  # Below min
            {"seller_id": "seller2", "price": 1300.0, "quantity": 2, "round_number": 1, "message_count": 2},  # Above max
            {"seller_id": "seller3", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 4}  # Valid
        ]
        best = select_best_offer(offers, sample_constraints)
        assert best is not None
        assert best["seller_id"] == "seller3"
    
    def test_select_best_offer_no_valid_offers(self, sample_constraints):
        """Test that None is returned when no valid offers exist."""
        offers = [
            {"seller_id": "seller1", "price": 700.0, "quantity": 2, "round_number": 1, "message_count": 3},
            {"seller_id": "seller2", "price": 1300.0, "quantity": 2, "round_number": 1, "message_count": 2}
        ]
        best = select_best_offer(offers, sample_constraints)
        assert best is None
    
    def test_select_best_offer_empty_list(self, sample_constraints):
        """Test that None is returned for empty offer list."""
        best = select_best_offer([], sample_constraints)
        assert best is None
    
    def test_select_best_offer_tie_breaker_responsiveness(self, sample_constraints):
        """Test selection by responsiveness (most messages)."""
        offers = [
            {"seller_id": "seller1", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 2},
            {"seller_id": "seller2", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 5},
            {"seller_id": "seller3", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 3}
        ]
        best = select_best_offer(offers, sample_constraints, tie_breaker="responsiveness")
        assert best is not None
        assert best["seller_id"] == "seller2"
        assert best["message_count"] == 5
    
    def test_select_best_offer_tie_breaker_rounds(self, sample_constraints):
        """Test selection by fewer rounds."""
        offers = [
            {"seller_id": "seller1", "price": 1000.0, "quantity": 2, "round_number": 3, "message_count": 3},
            {"seller_id": "seller2", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 2},
            {"seller_id": "seller3", "price": 1000.0, "quantity": 2, "round_number": 2, "message_count": 4}
        ]
        best = select_best_offer(offers, sample_constraints, tie_breaker="rounds")
        assert best is not None
        assert best["seller_id"] == "seller2"
        assert best["round_number"] == 1
    
    def test_select_best_offer_price_tie_breaker_with_rounds(self, sample_constraints):
        """Test that price tie-breaker uses rounds as secondary criterion."""
        offers = [
            {"seller_id": "seller1", "price": 1000.0, "quantity": 2, "round_number": 3, "message_count": 3},
            {"seller_id": "seller2", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 2},
            {"seller_id": "seller3", "price": 1000.0, "quantity": 2, "round_number": 2, "message_count": 4}
        ]
        best = select_best_offer(offers, sample_constraints, tie_breaker="price")
        assert best is not None
        assert best["seller_id"] == "seller2"  # Same price, fewer rounds
        assert best["round_number"] == 1
    
    def test_select_best_offer_similar_price_grouping(self, sample_constraints):
        """Test that prices within $0.01 are grouped together."""
        offers = [
            {"seller_id": "seller1", "price": 1000.01, "quantity": 2, "round_number": 2, "message_count": 3},
            {"seller_id": "seller2", "price": 1000.00, "quantity": 2, "round_number": 1, "message_count": 2},
            {"seller_id": "seller3", "price": 1000.02, "quantity": 2, "round_number": 3, "message_count": 4}
        ]
        best = select_best_offer(offers, sample_constraints, tie_breaker="price")
        assert best is not None
        # Should select seller2 (lowest price group, fewest rounds)
        assert best["seller_id"] == "seller2"
    
    def test_select_best_offer_missing_fields(self, sample_constraints):
        """Test handling of offers with missing fields."""
        offers = [
            {"seller_id": "seller1", "price": 1000.0},  # Missing quantity
            {"seller_id": "seller2", "quantity": 2},  # Missing price
            {"seller_id": "seller3", "price": 1000.0, "quantity": 2, "round_number": 1, "message_count": 3}  # Valid
        ]
        best = select_best_offer(offers, sample_constraints)
        assert best is not None
        assert best["seller_id"] == "seller3"


class TestComputeTotalCost:
    """Test total cost computation."""
    
    def test_compute_total_cost_normal(self):
        """Test normal total cost calculation."""
        total = compute_total_cost(1000.0, 2)
        assert total == 2000.0
    
    def test_compute_total_cost_single_item(self):
        """Test total cost for single item."""
        total = compute_total_cost(500.0, 1)
        assert total == 500.0
    
    def test_compute_total_cost_large_quantity(self):
        """Test total cost for large quantity."""
        total = compute_total_cost(10.0, 100)
        assert total == 1000.0
    
    def test_compute_total_cost_zero_price(self):
        """Test total cost with zero price."""
        total = compute_total_cost(0.0, 5)
        assert total == 0.0

