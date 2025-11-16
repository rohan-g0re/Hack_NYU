"""
Error handling and edge case tests for Phase 2.

WHAT: Test error handling and edge case scenarios
WHY: Ensure robustness under adverse conditions
HOW: Test various failure modes and boundary conditions
"""

import pytest
from app.agents.prompts import render_seller_prompt
from app.agents.buyer_agent import BuyerAgent
from app.agents.seller_agent import SellerAgent
from app.services.seller_selection import select_sellers_for_item
from app.services.decision_engine import analyze_offers
from app.models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem
from app.models.negotiation import NegotiationRoomState
from app.llm.types import LLMResult, ProviderStatus


class ErrorProvider:
    """Provider that always raises errors."""
    async def generate(self, messages, *, temperature, max_tokens, stop=None):
        raise Exception("Simulated provider error")


class MockProvider:
    """Mock provider for testing."""
    def __init__(self, response="Test response"):
        self.response = response
    
    async def generate(self, messages, *, temperature, max_tokens, stop=None):
        return LLMResult(text=self.response, usage={}, model="mock")


# Edge Case: Seller with no matching inventory

@pytest.mark.phase2
@pytest.mark.unit
def test_seller_prompt_raises_error_when_no_matching_inventory():
    """Test seller prompt raises error if seller doesn't have requested item."""
    seller = Seller(
        seller_id="s1",
        name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[
            InventoryItem(
                item_id="item2",  # Different item
                item_name="Gadget",
                cost_price=5.0,
                selling_price=15.0,
                least_price=10.0,
                quantity_available=10
            )
        ]
    )
    
    constraints = BuyerConstraints(
        item_id="item1",  # Requesting different item
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    with pytest.raises(ValueError, match="does not have item"):
        render_seller_prompt(
            seller=seller,
            constraints=constraints,
            conversation_history=[],
            buyer_name="Bob"
        )


# Edge Case: All sellers fail to respond

@pytest.mark.phase2
@pytest.mark.unit
def test_decision_engine_handles_no_offers():
    """Test decision engine handles case where no sellers make offers."""
    room_state = NegotiationRoomState(
        room_id="room1",
        buyer_id="buyer1",
        buyer_name="Bob",
        buyer_constraints=BuyerConstraints(
            item_id="item1",
            item_name="Widget",
            quantity_needed=5,
            min_price_per_unit=10.0,
            max_price_per_unit=20.0
        ),
        sellers=[],
        current_round=1
    )
    
    seller_results = {
        "seller1": {"message": "Not interested", "offer": None},
        "seller2": {"message": "Too risky", "offer": None}
    }
    
    analyses = analyze_offers(room_state, seller_results)
    
    # Should return empty list
    assert analyses == []


# Edge Case: Invalid mention format from buyer

@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_buyer_agent_handles_invalid_mention_format():
    """Test buyer agent handles messages with malformed mentions."""
    mock = MockProvider("I want to talk to @ and @@@ and @")
    
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    room_state = NegotiationRoomState(
        room_id="r1",
        buyer_id="b1",
        buyer_name="Bob",
        buyer_constraints=constraints,
        sellers=[]
    )
    
    buyer_agent = BuyerAgent(provider=mock, constraints=constraints)
    result = await buyer_agent.run_turn(room_state)
    
    # Should handle gracefully without crashing
    assert "message" in result
    assert "mentioned_sellers" in result
    assert isinstance(result["mentioned_sellers"], list)


# Edge Case: Malformed offer JSON from seller

@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_handles_malformed_offer_json():
    """Test seller agent handles malformed JSON gracefully."""
    mock = MockProvider('Here is my offer: {"offer": {invalid json}}')
    
    seller = Seller(
        seller_id="s1",
        name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[InventoryItem(
            item_id="item1",
            item_name="Widget",
            cost_price=8.0,
            selling_price=18.0,
            least_price=12.0,
            quantity_available=10
        )]
    )
    
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    room_state = NegotiationRoomState(
        room_id="r1",
        buyer_id="b1",
        buyer_name="Bob",
        buyer_constraints=constraints,
        sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    # Should handle gracefully, offer should be None
    assert result["offer"] is None
    assert "message" in result


# Edge Case: Quantity needed exceeds all sellers' combined inventory

@pytest.mark.phase2
@pytest.mark.unit
def test_seller_selection_when_total_inventory_insufficient():
    """Test seller selection when combined inventory still insufficient."""
    sellers = [
        Seller(
            seller_id="s1",
            name="Alice",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
            inventory=[InventoryItem(
                item_id="item1",
                item_name="Widget",
                cost_price=8.0,
                selling_price=18.0,
                least_price=12.0,
                quantity_available=3  # Only 3
            )]
        ),
        Seller(
            seller_id="s2",
            name="Bob",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[InventoryItem(
                item_id="item1",
                item_name="Widget",
                cost_price=7.0,
                selling_price=17.0,
                least_price=11.0,
                quantity_available=2  # Only 2
            )]
        )
    ]
    
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=10,  # Need 10 but only 5 available total
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    result = select_sellers_for_item(constraints, sellers)
    
    # Both should be skipped due to insufficient quantity
    assert len(result.selected_sellers) == 0
    assert len(result.skipped_sellers) == 2


# Edge Case: Timeout in decision node

@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_buyer_agent_timeout_handling():
    """Test buyer agent handles timeout gracefully."""
    class TimeoutProvider:
        async def generate(self, messages, *, temperature, max_tokens, stop=None):
            import asyncio
            await asyncio.sleep(10)  # Simulate timeout
            raise asyncio.TimeoutError("Request timeout")
    
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    room_state = NegotiationRoomState(
        room_id="r1",
        buyer_id="b1",
        buyer_name="Bob",
        buyer_constraints=constraints,
        sellers=[]
    )
    
    buyer_agent = BuyerAgent(provider=TimeoutProvider(), constraints=constraints)
    result = await buyer_agent.run_turn(room_state)
    
    # Should return fallback message
    assert "message" in result
    assert len(result["message"]) > 0


# Edge Case: Empty conversation history

@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_handle_empty_conversation_history():
    """Test agents handle empty conversation history."""
    mock = MockProvider("Hello")
    
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    seller = Seller(
        seller_id="s1",
        name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[InventoryItem(
            item_id="item1",
            item_name="Widget",
            cost_price=8.0,
            selling_price=18.0,
            least_price=12.0,
            quantity_available=10
        )]
    )
    
    room_state = NegotiationRoomState(
        room_id="r1",
        buyer_id="b1",
        buyer_name="Bob",
        buyer_constraints=constraints,
        sellers=[seller],
        conversation_history=[]  # Empty
    )
    
    # Test buyer agent
    buyer_agent = BuyerAgent(provider=mock, constraints=constraints)
    buyer_result = await buyer_agent.run_turn(room_state)
    assert "message" in buyer_result
    
    # Test seller agent
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=seller.inventory[0])
    seller_result = await seller_agent.respond(room_state, "Bob", constraints)
    assert "message" in seller_result


# Edge Case: Zero price range (min == max)

@pytest.mark.phase2
@pytest.mark.unit
def test_decision_engine_handles_zero_price_range():
    """Test decision engine handles case where buyer's min == max price."""
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=15.0,
        max_price_per_unit=15.0  # Same as min
    )
    
    sellers = [
        Seller(
            seller_id="s1",
            name="Alice",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
            inventory=[InventoryItem(
                item_id="item1",
                item_name="Widget",
                cost_price=8.0,
                selling_price=18.0,
                least_price=12.0,
                quantity_available=10
            )]
        )
    ]
    
    room_state = NegotiationRoomState(
        room_id="r1",
        buyer_id="b1",
        buyer_name="Bob",
        buyer_constraints=constraints,
        sellers=sellers,
        current_round=1
    )
    
    seller_results = {
        "s1": {"message": "Here's my offer", "offer": {"price": 15.0, "quantity": 5}}
    }
    
    analyses = analyze_offers(room_state, seller_results)
    
    # Should handle gracefully, offer at exact price should be valid
    assert len(analyses) == 1
    assert analyses[0].price_score >= 0  # Should not error


# Edge Case: Negative or zero quantities

@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_rejects_invalid_quantities():
    """Test seller agent rejects offers with invalid quantities."""
    mock = MockProvider('{"offer": {"price": 15.0, "quantity": 0}}')  # Zero quantity
    
    seller = Seller(
        seller_id="s1",
        name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[InventoryItem(
            item_id="item1",
            item_name="Widget",
            cost_price=8.0,
            selling_price=18.0,
            least_price=12.0,
            quantity_available=10
        )]
    )
    
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )
    
    room_state = NegotiationRoomState(
        room_id="r1",
        buyer_id="b1",
        buyer_name="Bob",
        buyer_constraints=constraints,
        sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    # Should reject or clamp to valid quantity (>=1)
    if result["offer"]:
        assert result["offer"]["quantity"] >= 1
    else:
        # Or reject entirely
        assert result["offer"] is None

