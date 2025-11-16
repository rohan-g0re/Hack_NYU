"""
Unit tests for room building utilities.

WHAT: Test seller filtering by item_id
WHY: Ensure only relevant sellers are included in negotiations
HOW: Verify filter_sellers_by_item logic with various scenarios
"""

import pytest
from app.services.room_builder import filter_sellers_by_item
from app.models.negotiation import InventoryItem


@pytest.mark.phase2
class TestSellerFiltering:
    """Test seller filtering by item_id."""
    
    def test_filter_single_match(self):
        """Test filtering when one seller has the item."""
        inventories = {
            "seller1": [
                InventoryItem(
                    item_id="widget",
                    name="Widget",
                    quantity_available=100,
                    cost_price=5.0,
                    least_price=8.0,
                    selling_price=10.0
                )
            ],
            "seller2": [
                InventoryItem(
                    item_id="gadget",
                    name="Gadget",
                    quantity_available=50,
                    cost_price=3.0,
                    least_price=6.0,
                    selling_price=8.0
                )
            ]
        }
        
        result = filter_sellers_by_item("widget", inventories)
        
        assert result == ["seller1"]
    
    def test_filter_multiple_matches(self):
        """Test filtering when multiple sellers have the item."""
        inventories = {
            "seller1": [
                InventoryItem(
                    item_id="widget",
                    name="Widget",
                    quantity_available=100,
                    cost_price=5.0,
                    least_price=8.0,
                    selling_price=10.0
                )
            ],
            "seller2": [
                InventoryItem(
                    item_id="widget",
                    name="Widget",
                    quantity_available=200,
                    cost_price=4.5,
                    least_price=7.5,
                    selling_price=9.5
                )
            ],
            "seller3": [
                InventoryItem(
                    item_id="gadget",
                    name="Gadget",
                    quantity_available=50,
                    cost_price=3.0,
                    least_price=6.0,
                    selling_price=8.0
                )
            ]
        }
        
        result = filter_sellers_by_item("widget", inventories)
        
        assert set(result) == {"seller1", "seller2"}
        assert len(result) == 2
    
    def test_filter_no_matches(self):
        """Test filtering when no sellers have the item."""
        inventories = {
            "seller1": [
                InventoryItem(
                    item_id="widget",
                    name="Widget",
                    quantity_available=100,
                    cost_price=5.0,
                    least_price=8.0,
                    selling_price=10.0
                )
            ],
            "seller2": [
                InventoryItem(
                    item_id="gadget",
                    name="Gadget",
                    quantity_available=50,
                    cost_price=3.0,
                    least_price=6.0,
                    selling_price=8.0
                )
            ]
        }
        
        result = filter_sellers_by_item("nonexistent", inventories)
        
        assert result == []
    
    def test_filter_seller_with_multiple_items(self):
        """Test filtering when seller has multiple items including the target."""
        inventories = {
            "seller1": [
                InventoryItem(
                    item_id="widget",
                    name="Widget",
                    quantity_available=100,
                    cost_price=5.0,
                    least_price=8.0,
                    selling_price=10.0
                ),
                InventoryItem(
                    item_id="gadget",
                    name="Gadget",
                    quantity_available=50,
                    cost_price=3.0,
                    least_price=6.0,
                    selling_price=8.0
                )
            ],
            "seller2": [
                InventoryItem(
                    item_id="gadget",
                    name="Gadget",
                    quantity_available=75,
                    cost_price=3.5,
                    least_price=6.5,
                    selling_price=8.5
                )
            ]
        }
        
        result = filter_sellers_by_item("widget", inventories)
        
        assert result == ["seller1"]
    
    def test_filter_empty_inventories(self):
        """Test filtering with empty inventory dict."""
        inventories = {}
        
        result = filter_sellers_by_item("widget", inventories)
        
        assert result == []
    
    def test_filter_seller_with_empty_inventory(self):
        """Test filtering when seller has empty inventory list."""
        inventories = {
            "seller1": [],
            "seller2": [
                InventoryItem(
                    item_id="widget",
                    name="Widget",
                    quantity_available=100,
                    cost_price=5.0,
                    least_price=8.0,
                    selling_price=10.0
                )
            ]
        }
        
        result = filter_sellers_by_item("widget", inventories)
        
        assert result == ["seller2"]

