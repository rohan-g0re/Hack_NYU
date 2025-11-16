"""
Tests for seller agent.

WHAT: Test seller agent behavior and offer validation
WHY: Ensure seller operates within constraints
HOW: Use mock provider and assert offer validation
"""

import pytest
from tests.fixtures.mock_llm import MockLLMProvider
from app.agents.seller_agent import SellerAgent
from app.models.negotiation import (
    NegotiationRoomState,
    BuyerConstraints,
    SellerProfile,
    InventoryItem
)


@pytest.mark.phase2
@pytest.mark.unit
class TestSellerAgent:
    """Test seller agent functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_response(self):
        """Test seller can generate basic response."""
        provider = MockLLMProvider(responses=["Happy to help with your request!"])
        
        profile = SellerProfile(
            seller_id="s1",
            display_name="Seller1",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=200,
                cost_price=5.0,
                least_price=7.0,
                selling_price=10.0
            )
        ]
        
        agent = SellerAgent(provider, profile, inventory)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=100,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory}
        )
        
        result = await agent.respond(room_state)
        
        assert result.seller_id == "s1"
        assert len(result.message) > 0
        assert result.raw_text is not None
    
    @pytest.mark.asyncio
    async def test_offer_extraction_and_validation(self):
        """Test offer is extracted and validated."""
        offer_text = '''I can offer you a great deal!
```offer
{"price": 8.5, "quantity": 150, "item_id": "widget"}
```
Let me know if interested.'''
        
        provider = MockLLMProvider(responses=[offer_text])
        
        profile = SellerProfile(
            seller_id="s1",
            display_name="Seller1"
        )
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=200,
                cost_price=5.0,
                least_price=7.0,
                selling_price=10.0
            )
        ]
        
        agent = SellerAgent(provider, profile, inventory)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=100,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory}
        )
        
        result = await agent.respond(room_state)
        
        assert result.offer is not None
        assert result.offer.price == 8.5
        assert result.offer.quantity == 150
        assert result.offer.seller_id == "s1"
        assert len(result.violations) == 0
    
    @pytest.mark.asyncio
    async def test_offer_below_least_price_rejected(self):
        """Test that offers below least_price are rejected."""
        offer_text = '''Best I can do.
```offer
{"price": 6.0, "quantity": 100, "item_id": "widget"}
```'''
        
        provider = MockLLMProvider(responses=[offer_text])
        
        profile = SellerProfile(seller_id="s1", display_name="Seller1")
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=200,
                cost_price=5.0,
                least_price=7.0,  # Offer is below this
                selling_price=10.0
            )
        ]
        
        agent = SellerAgent(provider, profile, inventory)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=100,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory}
        )
        
        result = await agent.respond(room_state)
        
        # Offer should be rejected
        assert result.offer is None
        assert len(result.violations) > 0
        assert any("least_price" in v.lower() or "below" in v.lower() for v in result.violations)
    
    @pytest.mark.asyncio
    async def test_offer_exceeding_inventory_capped(self):
        """Test that offers exceeding inventory are capped."""
        offer_text = '''I'll sell you everything!
```offer
{"price": 9.0, "quantity": 300, "item_id": "widget"}
```'''
        
        provider = MockLLMProvider(responses=[offer_text])
        
        profile = SellerProfile(seller_id="s1", display_name="Seller1")
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=200,  # Only 200 available
                cost_price=5.0,
                least_price=7.0,
                selling_price=10.0
            )
        ]
        
        agent = SellerAgent(provider, profile, inventory)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=100,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory}
        )
        
        result = await agent.respond(room_state)
        
        # Offer should be capped at available quantity
        assert result.offer is not None
        assert result.offer.quantity == 200  # Capped
        assert len(result.violations) > 0
        assert any("exceed" in v.lower() for v in result.violations)
    
    @pytest.mark.asyncio
    async def test_no_offer_in_response(self):
        """Test response without offer."""
        provider = MockLLMProvider(
            responses=["I need more information before making an offer."]
        )
        
        profile = SellerProfile(seller_id="s1", display_name="Seller1")
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=200,
                cost_price=5.0,
                least_price=7.0,
                selling_price=10.0
            )
        ]
        
        agent = SellerAgent(provider, profile, inventory)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=100,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory}
        )
        
        result = await agent.respond(room_state)
        
        # No offer is okay
        assert result.offer is None
        assert len(result.violations) == 0
    
    @pytest.mark.asyncio
    async def test_rude_style_enforcement(self):
        """Test rude speaking style is enforced."""
        provider = MockLLMProvider(
            responses=["I'm so happy to help! Please let me know how I can assist you. Thank you!"]
        )
        
        profile = SellerProfile(
            seller_id="s1",
            display_name="Seller1",
            speaking_style="rude"
        )
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=200,
                cost_price=5.0,
                least_price=7.0,
                selling_price=10.0
            )
        ]
        
        agent = SellerAgent(provider, profile, inventory)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=100,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory}
        )
        
        result = await agent.respond(room_state)
        
        # Rude style should have removed pleasantries
        message_lower = result.message.lower()
        assert "please" not in message_lower
        assert "thank you" not in message_lower or "thank" not in message_lower
    
    @pytest.mark.asyncio
    async def test_provider_error_handling(self):
        """Test that provider errors are wrapped correctly."""
        from app.utils.exceptions import SellerAgentError
        
        provider = MockLLMProvider(should_fail=True)
        
        profile = SellerProfile(seller_id="s1", display_name="Seller1")
        inventory = []
        
        agent = SellerAgent(provider, profile, inventory)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=100,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            ),
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory},
            room_id="test_room",
            current_round=3
        )
        
        with pytest.raises(SellerAgentError) as exc_info:
            await agent.respond(room_state)
        
        # Should wrap with context
        assert exc_info.value.seller_id == "s1"
        assert exc_info.value.room_id == "test_room"
        assert exc_info.value.round_number == 3

