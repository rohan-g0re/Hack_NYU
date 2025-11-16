"""
Unit tests for seller selection service.

WHAT: Test seller selection and validation logic
WHY: Ensure only qualified sellers participate
HOW: Test various inventory and constraint scenarios
"""

import pytest
from app.services.seller_selection import (
    select_sellers_for_item, validate_seller_inventory, SelectionResult
)
from app.models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem


@pytest.fixture
def sample_sellers():
    """Create sample sellers with varied inventory."""
    return [
        Seller(
            seller_id="seller1",
            name="Alice",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
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
        ),
        Seller(
            seller_id="seller2",
            name="Bob",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[
                InventoryItem(
                    item_id="item1",
                    item_name="Widget",
                    cost_price=7.0,
                    selling_price=25.0,  # Least price will be high
                    least_price=22.0,  # Above buyer's max
                    quantity_available=8
                )
            ]
        ),
        Seller(
            seller_id="seller3",
            name="Charlie",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
            inventory=[
                InventoryItem(
                    item_id="item2",  # Different item
                    item_name="Gadget",
                    cost_price=5.0,
                    selling_price=15.0,
                    least_price=10.0,
                    quantity_available=20
                )
            ]
        ),
        Seller(
            seller_id="seller4",
            name="Diana",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[
                InventoryItem(
                    item_id="item1",
                    item_name="Widget",
                    cost_price=6.0,
                    selling_price=17.0,
                    least_price=11.0,
                    quantity_available=3  # Insufficient quantity
                )
            ]
        )
    ]


@pytest.mark.phase2
@pytest.mark.unit
def test_select_sellers_includes_valid_sellers(sample_sellers):
    """Test select_sellers includes sellers with matching inventory."""
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    result = select_sellers_for_item(constraints, sample_sellers)
    
    # seller1 should be selected (has item, quantity OK, price OK)
    assert len(result.selected_sellers) >= 1
    seller_ids = [s.seller_id for s in result.selected_sellers]
    assert "seller1" in seller_ids


@pytest.mark.phase2
@pytest.mark.unit
def test_select_sellers_skips_no_inventory(sample_sellers):
    """Test select_sellers skips sellers without matching item."""
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    result = select_sellers_for_item(constraints, sample_sellers)
    
    # seller3 should be skipped (has item2, not item1)
    assert "seller3" in result.skipped_sellers
    assert "no_inventory" in result.skipped_sellers["seller3"]


@pytest.mark.phase2
@pytest.mark.unit
def test_select_sellers_skips_insufficient_quantity(sample_sellers):
    """Test select_sellers skips sellers with insufficient quantity."""
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    result = select_sellers_for_item(constraints, sample_sellers)
    
    # seller4 should be skipped (has only 3, needs 5)
    assert "seller4" in result.skipped_sellers
    assert "insufficient_quantity" in result.skipped_sellers["seller4"]


@pytest.mark.phase2
@pytest.mark.unit
def test_select_sellers_skips_price_mismatch(sample_sellers):
    """Test select_sellers skips sellers with price mismatch."""
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    result = select_sellers_for_item(constraints, sample_sellers)
    
    # seller2 should be skipped (least_price=22 > buyer's max=20)
    assert "seller2" in result.skipped_sellers
    assert "price_mismatch" in result.skipped_sellers["seller2"]


@pytest.mark.phase2
@pytest.mark.unit
def test_select_sellers_returns_reason_codes(sample_sellers):
    """Test select_sellers provides skip reasons for all skipped sellers."""
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    result = select_sellers_for_item(constraints, sample_sellers)
    
    # All skipped sellers should have reasons
    for seller_id, reason in result.skipped_sellers.items():
        assert isinstance(reason, str)
        assert len(reason) > 0


@pytest.mark.phase2
@pytest.mark.unit
def test_validate_seller_inventory_valid_seller():
    """Test validate_seller_inventory returns True for valid seller."""
    seller = Seller(
        seller_id="s1",
        name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
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
    
    can_participate, reason = validate_seller_inventory(
        seller=seller,
        item_id="item1",
        quantity_needed=5,
        max_price=20.0
    )
    
    assert can_participate is True
    assert reason is None


@pytest.mark.phase2
@pytest.mark.unit
def test_validate_seller_inventory_no_item():
    """Test validate_seller_inventory returns False for missing item."""
    seller = Seller(
        seller_id="s1",
        name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[
            InventoryItem(
                item_id="item2",  # Different item
                item_name="Gadget",
                cost_price=8.0,
                selling_price=18.0,
                least_price=12.0,
                quantity_available=10
            )
        ]
    )
    
    can_participate, reason = validate_seller_inventory(
        seller=seller,
        item_id="item1",
        quantity_needed=5,
        max_price=20.0
    )
    
    assert can_participate is False
    assert reason == "no_inventory"


@pytest.mark.phase2
@pytest.mark.unit
def test_validate_seller_inventory_insufficient_quantity():
    """Test validate_seller_inventory returns False for insufficient stock."""
    seller = Seller(
        seller_id="s1",
        name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[
            InventoryItem(
                item_id="item1",
                item_name="Widget",
                cost_price=8.0,
                selling_price=18.0,
                least_price=12.0,
                quantity_available=3  # Less than needed
            )
        ]
    )
    
    can_participate, reason = validate_seller_inventory(
        seller=seller,
        item_id="item1",
        quantity_needed=5,
        max_price=20.0
    )
    
    assert can_participate is False
    assert "insufficient_quantity" in reason


@pytest.mark.phase2
@pytest.mark.unit
def test_validate_seller_inventory_price_too_high():
    """Test validate_seller_inventory returns False when price too high."""
    seller = Seller(
        seller_id="s1",
        name="Alice",
        profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
        inventory=[
            InventoryItem(
                item_id="item1",
                item_name="Widget",
                cost_price=20.0,
                selling_price=30.0,
                least_price=25.0,  # Above buyer's max
                quantity_available=10
            )
        ]
    )
    
    can_participate, reason = validate_seller_inventory(
        seller=seller,
        item_id="item1",
        quantity_needed=5,
        max_price=20.0
    )
    
    assert can_participate is False
    assert "price_mismatch" in reason

