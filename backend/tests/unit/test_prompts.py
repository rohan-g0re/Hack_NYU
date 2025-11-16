"""
Tests for prompt rendering.

WHAT: Test buyer/seller prompt generation
WHY: Ensure prompts contain required constraints and instructions
HOW: Snapshot-style assertions on rendered prompts
"""

import pytest
from app.agents.prompts import render_buyer_prompt, render_seller_prompt
from app.models.negotiation import (
    NegotiationRoomState,
    BuyerConstraints,
    SellerProfile,
    InventoryItem,
    Message
)


@pytest.mark.phase2
@pytest.mark.unit
class TestBuyerPromptRendering:
    """Test buyer prompt rendering."""
    
    def test_buyer_prompt_contains_constraints(self):
        """Test that buyer prompt includes all constraints."""
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Premium Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0,
            budget_ceiling=950.0,
            tone="neutral"
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            current_round=0,
            max_rounds=10
        )
        
        messages = render_buyer_prompt(room_state, [])
        
        # Should have system message
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"
        
        system_content = messages[0]["content"]
        
        # Check constraints are mentioned
        assert "Premium Widget" in system_content
        assert "100" in system_content  # quantity
        assert "$5.00" in system_content  # min price
        assert "$10.00" in system_content  # max price
        assert "$950.00" in system_content  # budget
        assert "neutral" in system_content.lower()  # tone
    
    def test_buyer_prompt_mentions_convention(self):
        """Test that buyer prompt explains @mention convention."""
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=50,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints
        )
        
        messages = render_buyer_prompt(room_state, [])
        system_content = messages[0]["content"]
        
        # Check mention instructions
        assert "@" in system_content
        assert "seller" in system_content.lower()
    
    def test_buyer_prompt_includes_history(self):
        """Test that buyer prompt includes conversation history."""
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=50,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        history = [
            Message(
                sender_id="buyer1",
                sender_type="buyer",
                content="Hello sellers!",
                round_number=0,
                visible_to=["all"]
            ),
            Message(
                sender_id="seller1",
                sender_type="seller",
                content="Hi, I can help!",
                round_number=0,
                visible_to=["all"]
            )
        ]
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={
                "seller1": SellerProfile(
                    seller_id="seller1",
                    display_name="SellerOne"
                )
            }
        )
        
        messages = render_buyer_prompt(room_state, history)
        
        # Should have system + history messages
        assert len(messages) == 3
        assert messages[1]["role"] == "assistant"
        assert "Hello sellers!" in messages[1]["content"]
        assert messages[2]["role"] == "user"
        assert "Hi, I can help!" in messages[2]["content"]


@pytest.mark.phase2
@pytest.mark.unit
class TestSellerPromptRendering:
    """Test seller prompt rendering."""
    
    def test_seller_prompt_contains_profile(self):
        """Test that seller prompt includes personality and priorities."""
        profile = SellerProfile(
            seller_id="seller1",
            display_name="AggressiveSeller",
            priority="maximize_profit",
            speaking_style="rude"
        )
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Premium Widget",
                quantity_available=200,
                cost_price=4.0,
                least_price=6.0,
                selling_price=12.0
            )
        ]
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=50,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"seller1": profile},
            seller_inventories={"seller1": inventory}
        )
        
        messages = render_seller_prompt(room_state, "seller1", [])
        
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"
        
        system_content = messages[0]["content"]
        
        # Check profile elements
        assert "AggressiveSeller" in system_content
        assert "maximize" in system_content.lower() or "profit" in system_content.lower()
        assert "rude" in system_content.lower() or "blunt" in system_content.lower()
    
    def test_seller_prompt_contains_inventory(self):
        """Test that seller prompt includes inventory details."""
        profile = SellerProfile(
            seller_id="seller1",
            display_name="Seller",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Premium Widget",
                quantity_available=150,
                cost_price=5.0,
                least_price=7.0,
                selling_price=10.0
            )
        ]
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=50,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"seller1": profile},
            seller_inventories={"seller1": inventory}
        )
        
        messages = render_seller_prompt(room_state, "seller1", [])
        system_content = messages[0]["content"]
        
        # Check inventory details
        assert "Premium Widget" in system_content
        assert "150" in system_content  # quantity available
        assert "$7.00" in system_content  # least price
        assert "$10.00" in system_content  # selling price
    
    def test_seller_prompt_enforces_least_price(self):
        """Test that seller prompt explicitly mentions least price constraint."""
        profile = SellerProfile(
            seller_id="seller1",
            display_name="Seller"
        )
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=100,
                cost_price=5.0,
                least_price=7.0,
                selling_price=10.0
            )
        ]
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=50,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"seller1": profile},
            seller_inventories={"seller1": inventory}
        )
        
        messages = render_seller_prompt(room_state, "seller1", [])
        system_content = messages[0]["content"]
        
        # Check least price warning
        assert "NEVER" in system_content or "never" in system_content
        assert "below" in system_content.lower()
        assert "minimum" in system_content.lower() or "least" in system_content.lower()
    
    def test_seller_prompt_includes_offer_format(self):
        """Test that seller prompt explains offer formatting."""
        profile = SellerProfile(
            seller_id="seller1",
            display_name="Seller"
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=50,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"seller1": profile},
            seller_inventories={"seller1": []}
        )
        
        messages = render_seller_prompt(room_state, "seller1", [])
        system_content = messages[0]["content"]
        
        # Check offer format instructions
        assert "```offer" in system_content or "offer" in system_content.lower()
        assert "price" in system_content.lower()
        assert "quantity" in system_content.lower()

