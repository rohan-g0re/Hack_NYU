"""
Integration tests for agents using live LLM provider.

WHAT: Test buyer and seller agents with real provider
WHY: Validate agent behavior with actual LLM calls
HOW: Use get_provider(), skip if unavailable, test generate/respond
"""

import pytest
from app.llm.provider_factory import get_provider
from app.agents.buyer_agent import BuyerAgent
from app.agents.seller_agent import SellerAgent
from app.models.agent import (
    BuyerConstraints, Seller, SellerProfile, InventoryItem
)
from app.models.negotiation import NegotiationRoomState


@pytest.fixture(scope="module")
def provider():
    """Get LLM provider, skip if unavailable."""
    try:
        prov = get_provider()
        # Try to ping to verify availability
        import asyncio
        status = asyncio.run(prov.ping())
        if not status.available:
            pytest.skip("LLM provider not available")
        return prov
    except Exception as e:
        pytest.skip(f"Could not get provider: {e}")


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
    """Sample seller."""
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


@pytest.fixture
def sample_room_state(sample_buyer_constraints, sample_seller):
    """Sample negotiation room state."""
    return NegotiationRoomState(
        room_id="room1",
        buyer_id="buyer1",
        buyer_name="Bob",
        buyer_constraints=sample_buyer_constraints,
        sellers=[sample_seller],
        conversation_history=[],
        current_round=0,
        max_rounds=10
    )


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_buyer_agent_generates_message(provider, sample_buyer_constraints, sample_room_state):
    """Test buyer agent generates non-empty message."""
    buyer_agent = BuyerAgent(
        provider=provider,
        constraints=sample_buyer_constraints,
        temperature=0.0,
        max_tokens=128
    )
    
    result = await buyer_agent.run_turn(sample_room_state)
    
    assert "message" in result
    assert isinstance(result["message"], str)
    assert len(result["message"]) > 0
    assert "mentioned_sellers" in result
    assert isinstance(result["mentioned_sellers"], list)


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_buyer_agent_mentions_sellers(provider, sample_buyer_constraints, sample_room_state):
    """Test buyer agent can mention sellers."""
    # Add instruction to mention seller
    sample_room_state.conversation_history = []
    
    buyer_agent = BuyerAgent(
        provider=provider,
        constraints=sample_buyer_constraints,
        temperature=0.0,
        max_tokens=128
    )
    
    result = await buyer_agent.run_turn(sample_room_state)
    
    # Should return valid structure (may or may not mention sellers)
    assert "mentioned_sellers" in result
    assert isinstance(result["mentioned_sellers"], list)
    
    # If mentioned, should be valid seller ID
    if result["mentioned_sellers"]:
        assert result["mentioned_sellers"][0] in [s.seller_id for s in sample_room_state.sellers]


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_seller_agent_generates_response(provider, sample_seller, sample_buyer_constraints, sample_room_state):
    """Test seller agent generates response."""
    inventory_item = sample_seller.inventory[0]
    
    seller_agent = SellerAgent(
        provider=provider,
        seller=sample_seller,
        inventory_item=inventory_item,
        temperature=0.0,
        max_tokens=128
    )
    
    result = await seller_agent.respond(
        sample_room_state,
        "Bob",
        sample_buyer_constraints
    )
    
    assert "message" in result
    assert isinstance(result["message"], str)
    assert len(result["message"]) > 0
    assert "offer" in result
    # Offer may be None or a dict


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_seller_agent_offer_within_constraints(provider, sample_seller, sample_buyer_constraints, sample_room_state):
    """Test seller agent offer respects constraints."""
    inventory_item = sample_seller.inventory[0]
    
    seller_agent = SellerAgent(
        provider=provider,
        seller=sample_seller,
        inventory_item=inventory_item,
        temperature=0.0,
        max_tokens=128
    )
    
    result = await seller_agent.respond(
        sample_room_state,
        "Bob",
        sample_buyer_constraints
    )
    
    # If offer exists, check constraints
    if result.get("offer"):
        offer = result["offer"]
        assert "price" in offer
        assert "quantity" in offer
        
        price = offer["price"]
        quantity = offer["quantity"]
        
        # Price should be within bounds
        assert inventory_item.least_price <= price <= inventory_item.selling_price
        
        # Quantity should be valid
        assert 1 <= quantity <= inventory_item.quantity_available


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_seller_agent_no_offer_is_valid(provider, sample_seller, sample_buyer_constraints, sample_room_state):
    """Test seller agent can respond without making an offer."""
    inventory_item = sample_seller.inventory[0]
    
    seller_agent = SellerAgent(
        provider=provider,
        seller=sample_seller,
        inventory_item=inventory_item,
        temperature=0.0,
        max_tokens=128
    )
    
    result = await seller_agent.respond(
        sample_room_state,
        "Bob",
        sample_buyer_constraints
    )
    
    # Should always return message, offer may be None
    assert "message" in result
    assert "offer" in result
    # Offer can be None - that's valid

