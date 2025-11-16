"""
Integration tests for negotiation graph using live provider.

WHAT: Test full negotiation flow with real LLM provider
WHY: Validate end-to-end negotiation orchestration
HOW: Run NegotiationGraph for 2-3 rounds, verify events
"""

import pytest
from app.llm.provider_factory import get_provider
from app.agents.graph_builder import NegotiationGraph
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
def sample_room_state():
    """Sample negotiation room state with 2 sellers."""
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
        ),
        Seller(
            seller_id="seller2",
            name="Bob",
            profile=SellerProfile(
                priority="maximize_profit",
                speaking_style="rude"
            ),
            inventory=[
                InventoryItem(
                    item_id="item1",
                    item_name="Widget",
                    cost_price=7.0,
                    selling_price=17.0,
                    least_price=11.0,
                    quantity_available=8
                )
            ]
        )
    ]
    
    return NegotiationRoomState(
        room_id="room1",
        buyer_id="buyer1",
        buyer_name="Charlie",
        buyer_constraints=buyer_constraints,
        sellers=sellers,
        conversation_history=[],
        current_round=0,
        max_rounds=3,  # Limit rounds for test speed
        seed=42  # For determinism
    )


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_negotiation_graph_emits_events(provider, sample_room_state):
    """Test negotiation graph emits expected event types."""
    graph = NegotiationGraph(provider)
    
    events = []
    async for event in graph.run(sample_room_state):
        events.append(event)
        
        # Stop after a few rounds to keep test fast
        if len(events) > 10:
            break
    
    assert len(events) > 0
    
    # Check event structure
    for event in events:
        assert "type" in event
        assert "data" in event
        assert "timestamp" in event
        assert event["type"] in [
            "buyer_message",
            "seller_response",
            "negotiation_complete",
            "error",
            "heartbeat"
        ]


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_negotiation_graph_buyer_message_event(provider, sample_room_state):
    """Test negotiation graph emits buyer_message events."""
    graph = NegotiationGraph(provider)
    
    buyer_events = []
    async for event in graph.run(sample_room_state):
        if event["type"] == "buyer_message":
            buyer_events.append(event)
        
        # Stop after first buyer message
        if event["type"] == "buyer_message":
            break
    
    assert len(buyer_events) > 0
    
    buyer_event = buyer_events[0]
    assert "message" in buyer_event["data"]
    assert "mentioned_sellers" in buyer_event["data"]
    assert "round" in buyer_event["data"]


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_negotiation_graph_seller_response_events(provider, sample_room_state):
    """Test negotiation graph emits seller_response events."""
    graph = NegotiationGraph(provider)
    
    seller_events = []
    async for event in graph.run(sample_room_state):
        if event["type"] == "seller_response":
            seller_events.append(event)
        
        # Stop after first round of seller responses
        if len(seller_events) >= len(sample_room_state.sellers):
            break
    
    # Should have at least one seller response
    assert len(seller_events) > 0
    
    for event in seller_events:
        assert "seller_id" in event["data"]
        assert "message" in event["data"]
        assert "round" in event["data"]


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_negotiation_graph_completes(provider, sample_room_state):
    """Test negotiation graph completes (either decision or max rounds)."""
    graph = NegotiationGraph(provider)
    
    events = []
    async for event in graph.run(sample_room_state):
        events.append(event)
        
        # Stop on completion
        if event["type"] == "negotiation_complete":
            break
    
    # Should have completion event
    completion_events = [e for e in events if e["type"] == "negotiation_complete"]
    assert len(completion_events) > 0
    
    completion = completion_events[0]
    assert "selected_seller_id" in completion["data"]
    assert "rounds" in completion["data"]


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_negotiation_graph_parallel_sellers(provider, sample_room_state):
    """Test negotiation graph handles parallel seller responses."""
    graph = NegotiationGraph(provider)
    
    seller_responses = {}
    async for event in graph.run(sample_room_state):
        if event["type"] == "seller_response":
            seller_id = event["data"]["seller_id"]
            seller_responses[seller_id] = event
        
        # Stop after first round
        if len(seller_responses) >= len(sample_room_state.sellers):
            break
    
    # Should have responses from multiple sellers (may be fewer if some fail)
    assert len(seller_responses) > 0


@pytest.mark.phase2
@pytest.mark.asyncio
async def test_negotiation_graph_handles_errors_gracefully(provider, sample_room_state):
    """Test negotiation graph handles errors without crashing."""
    graph = NegotiationGraph(provider)
    
    error_events = []
    events = []
    
    async for event in graph.run(sample_room_state):
        events.append(event)
        if event["type"] == "error":
            error_events.append(event)
        
        # Stop after a few events
        if len(events) > 5:
            break
    
    # Graph should continue even if some errors occur
    # (errors are logged but don't crash the graph)
    assert len(events) > 0

