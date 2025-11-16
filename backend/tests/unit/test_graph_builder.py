"""
Tests for negotiation graph.

WHAT: Test negotiation orchestration and event emission
WHY: Ensure correct multi-agent coordination
HOW: Use mock agents and assert event sequences
"""

import pytest
from tests.fixtures.mock_llm import MockLLMProvider
from app.agents.graph_builder import NegotiationGraph
from app.agents.buyer_agent import BuyerAgent
from app.agents.seller_agent import SellerAgent
from app.models.negotiation import (
    NegotiationRoomState,
    BuyerConstraints,
    SellerProfile,
    InventoryItem
)


@pytest.mark.phase2
@pytest.mark.unit
class TestNegotiationGraph:
    """Test negotiation graph orchestration."""
    
    @pytest.mark.asyncio
    async def test_basic_negotiation_flow(self):
        """Test basic negotiation with buyer and seller turns."""
        # Setup provider with scripted responses
        buyer_responses = ["@Seller1 what's your best price for 100 widgets?"]
        seller_responses = [
            '''I can offer you:
```offer
{"price": 8.5, "quantity": 100, "item_id": "widget"}
```'''
        ]
        
        buyer_provider = MockLLMProvider(responses=buyer_responses)
        seller_provider = MockLLMProvider(responses=seller_responses)
        
        # Setup agents
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        
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
        
        seller_agent = SellerAgent(seller_provider, profile, inventory)
        
        # Setup graph
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={"s1": seller_agent}
        )
        
        # Setup state
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory},
            active_sellers=["s1"],
            max_rounds=3,
            seed=42
        )
        
        # Run negotiation
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Should have emitted events
        assert len(events) > 0
        
        # Check event types
        event_types = [e["type"] for e in events]
        assert "buyer_message" in event_types
        assert "seller_response" in event_types
        assert "negotiation_complete" in event_types
    
    @pytest.mark.asyncio
    async def test_multiple_sellers_parallel(self):
        """Test that multiple sellers respond in parallel."""
        buyer_responses = ["@Seller1 @Seller2 send your best offers"]
        seller1_responses = ["Seller 1 here with offer"]
        seller2_responses = ["Seller 2 ready to help"]
        
        buyer_provider = MockLLMProvider(responses=buyer_responses)
        seller1_provider = MockLLMProvider(responses=seller1_responses)
        seller2_provider = MockLLMProvider(responses=seller2_responses)
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        
        profile1 = SellerProfile(seller_id="s1", display_name="Seller1")
        profile2 = SellerProfile(seller_id="s2", display_name="Seller2")
        
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
        
        seller1_agent = SellerAgent(seller1_provider, profile1, inventory)
        seller2_agent = SellerAgent(seller2_provider, profile2, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={"s1": seller1_agent, "s2": seller2_agent}
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={"s1": profile1, "s2": profile2},
            seller_inventories={"s1": inventory, "s2": inventory},
            active_sellers=["s1", "s2"],
            max_rounds=2,
            seed=42
        )
        
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Should have responses from both sellers
        seller_responses = [e for e in events if e["type"] == "seller_response"]
        seller_ids = [e["data"]["seller_id"] for e in seller_responses]
        
        assert "s1" in seller_ids
        assert "s2" in seller_ids
    
    @pytest.mark.asyncio
    async def test_max_rounds_termination(self):
        """Test that negotiation terminates after max rounds."""
        # No acceptable offers, should hit max rounds
        buyer_responses = ["Send offers"] * 5
        seller_responses = ["Can't help"] * 5
        
        buyer_provider = MockLLMProvider(responses=buyer_responses)
        seller_provider = MockLLMProvider(responses=seller_responses)
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        
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
        
        seller_agent = SellerAgent(seller_provider, profile, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={"s1": seller_agent}
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory},
            active_sellers=["s1"],
            max_rounds=3,
            seed=42
        )
        
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Should complete due to max rounds
        complete_events = [e for e in events if e["type"] == "negotiation_complete"]
        assert len(complete_events) == 1
        assert "max rounds" in complete_events[0]["data"]["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_acceptable_offer_triggers_completion(self):
        """Test that acceptable offer completes negotiation."""
        buyer_responses = ["@Seller1 send offer"]
        seller_responses = [
            '''Here you go:
```offer
{"price": 8.0, "quantity": 100, "item_id": "widget"}
```'''
        ]
        
        buyer_provider = MockLLMProvider(responses=buyer_responses)
        seller_provider = MockLLMProvider(responses=seller_responses)
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0  # 8.0 is within range
        )
        
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        
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
        
        seller_agent = SellerAgent(seller_provider, profile, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={"s1": seller_agent}
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory},
            active_sellers=["s1"],
            max_rounds=5,
            seed=42
        )
        
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Should complete with accepted offer
        complete_events = [e for e in events if e["type"] == "negotiation_complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["data"]["winner_id"] == "s1"
        assert complete_events[0]["data"]["winning_offer"] is not None
    
    @pytest.mark.asyncio
    async def test_heartbeat_events_emitted(self):
        """Test that heartbeat events are emitted during rounds."""
        buyer_responses = ["Send offers"] * 2
        seller_responses = ["No offer yet"] * 2
        
        buyer_provider = MockLLMProvider(responses=buyer_responses)
        seller_provider = MockLLMProvider(responses=seller_responses)
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        
        profile = SellerProfile(seller_id="s1", display_name="Seller1")
        inventory = []
        
        seller_agent = SellerAgent(seller_provider, profile, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={"s1": seller_agent}
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={"s1": profile},
            seller_inventories={"s1": inventory},
            active_sellers=["s1"],
            max_rounds=2,
            seed=42
        )
        
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Should have heartbeat events
        heartbeat_events = [e for e in events if e["type"] == "heartbeat"]
        assert len(heartbeat_events) > 0
    
    @pytest.mark.asyncio
    async def test_deterministic_with_seed(self):
        """Test that same seed produces deterministic results."""
        buyer_responses = ["@Seller1 offer"]
        seller_responses = ["Response"]
        
        async def run_negotiation(seed):
            buyer_provider = MockLLMProvider(responses=buyer_responses)
            seller_provider = MockLLMProvider(responses=seller_responses)
            
            constraints = BuyerConstraints(
                item_id="widget",
                item_name="Widget",
                quantity_needed=100,
                min_price_per_unit=5.0,
                max_price_per_unit=10.0
            )
            
            buyer_agent = BuyerAgent(buyer_provider, constraints)
            profile = SellerProfile(seller_id="s1", display_name="Seller1")
            inventory = []
            seller_agent = SellerAgent(seller_provider, profile, inventory)
            
            graph = NegotiationGraph(
                buyer_agent=buyer_agent,
                seller_agents={"s1": seller_agent}
            )
            
            room_state = NegotiationRoomState(
                buyer_id="buyer1",
                buyer_constraints=constraints,
                seller_profiles={"s1": profile},
                seller_inventories={"s1": inventory},
                active_sellers=["s1"],
                max_rounds=1,
                seed=seed
            )
            
            events = []
            async for event in graph.run(room_state):
                events.append(event)
            
            return events
        
        # Run with same seed twice
        events1 = await run_negotiation(42)
        events2 = await run_negotiation(42)
        
        # Should be identical
        assert len(events1) == len(events2)
        assert [e["type"] for e in events1] == [e["type"] for e in events2]
    
    @pytest.mark.asyncio
    async def test_sequential_seller_exchanges(self):
        """Verify sellers are negotiated with sequentially, not in parallel."""
        # Setup - all agents share one provider with scripted responses
        # Order: buyer message, seller response, buyer message, seller response, ...
        responses = [
            "Hello seller 1",           # Buyer to s1
            "I am seller 1",            # Seller s1 response
            "Hello seller 2",           # Buyer to s2
            "I am seller 2",            # Seller s2 response
            "Hello seller 3",           # Buyer to s3
            "I am seller 3",            # Seller s3 response
            "Hello seller 1 again",     # Buyer to s1 (round 2)
            "I am seller 1 round 2",    # Seller s1 response
            "Hello seller 2 again",     # Buyer to s2 (round 2)
            "I am seller 2 round 2",    # Seller s2 response
            "Hello seller 3 again",     # Buyer to s3 (round 2)
            "I am seller 3 round 2",    # Seller s3 response
        ]
        
        provider = MockLLMProvider(responses=responses)
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=10,
            min_price_per_unit=5.0,
            max_price_per_unit=15.0
        )
        
        buyer_agent = BuyerAgent(provider, constraints)
        
        # Create 3 sellers
        sellers = {}
        for i in [1, 2, 3]:
            seller_id = f"s{i}"
            profile = SellerProfile(seller_id=seller_id, display_name=f"Seller{i}")
            inventory = [InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=10,
                cost_price=5.0,
                least_price=8.0,
                selling_price=12.0
            )]
            sellers[seller_id] = SellerAgent(provider, profile, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents=sellers
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer",
            buyer_constraints=constraints,
            seller_profiles={sid: sellers[sid].profile for sid in sellers},
            seller_inventories={sid: sellers[sid].inventory for sid in sellers},
            active_sellers=["s1", "s2", "s3"],
            max_rounds=2,  # 2 exchanges per seller
            seed=42
        )
        
        # Run negotiation
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Extract buyer_message and seller_response events
        buyer_events = [e for e in events if e["type"] == "buyer_message"]
        seller_events = [e for e in events if e["type"] == "seller_response"]
        
        # Verify: 6 buyer messages (3 sellers × 2 rounds)
        assert len(buyer_events) == 6
        
        # Verify: 6 seller responses (3 sellers × 2 rounds)
        assert len(seller_events) == 6
        
        # Verify sequential order: buyer→s1, s1→buyer, buyer→s2, s2→buyer, buyer→s3, s3→buyer, repeat
        expected_sequence = [
            ("buyer_message", "s1", 0),  # Round 0, Seller 1
            ("seller_response", "s1", 0),
            ("buyer_message", "s2", 0),  # Round 0, Seller 2
            ("seller_response", "s2", 0),
            ("buyer_message", "s3", 0),  # Round 0, Seller 3
            ("seller_response", "s3", 0),
            ("buyer_message", "s1", 1),  # Round 1, Seller 1
            ("seller_response", "s1", 1),
            ("buyer_message", "s2", 1),  # Round 1, Seller 2
            ("seller_response", "s2", 1),
            ("buyer_message", "s3", 1),  # Round 1, Seller 3
            ("seller_response", "s3", 1),
        ]
        
        actual_sequence = []
        for e in events:
            if e["type"] in ["buyer_message", "seller_response"]:
                actual_sequence.append((
                    e["type"],
                    e["data"]["seller_id"],
                    e["data"]["round"]
                ))
        
        assert actual_sequence == expected_sequence
        
        # Verify each seller got exactly 2 exchanges
        assert room_state.exchanges_completed == {"s1": 2, "s2": 2, "s3": 2}
    
    @pytest.mark.asyncio
    async def test_early_exit_on_decision(self):
        """Verify negotiation can end after round 0 when buyer accepts offer."""
        # Setup - scripted responses for round 0 (all 3 sellers)
        responses = [
            "What's your offer?",  # Buyer to s1
            "I can offer at $20 per unit",  # Seller 1 gives bad offer (too high)
            "What's your offer?",  # Buyer to s2
            """I can offer a great deal!

```offer
{
  "price": 10.0,
  "quantity": 10,
  "item_id": "widget"
}
```""",  # Seller 2 gives good offer
            "What's your offer?",  # Buyer to s3
            """Standard pricing:

```offer
{
  "price": 12.0,
  "quantity": 10,
  "item_id": "widget"
}
```""",  # Seller 3 gives acceptable offer (but not as good as s2)
            # After round 0 completes, negotiation should end (s2 has best offer)
        ]
        
        provider = MockLLMProvider(responses=responses)
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=10,
            min_price_per_unit=5.0,
            max_price_per_unit=15.0,
            budget_per_item=150.0  # Total budget: 10 * $15 max
        )
        
        buyer_agent = BuyerAgent(provider, constraints)
        
        # Create 3 sellers (but negotiation should end after s2)
        sellers = {}
        for i in [1, 2, 3]:
            seller_id = f"s{i}"
            profile = SellerProfile(seller_id=seller_id, display_name=f"Seller{i}")
            inventory = [InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=10,
                cost_price=5.0,
                least_price=8.0,
                selling_price=12.0
            )]
            sellers[seller_id] = SellerAgent(provider, profile, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents=sellers
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer",
            buyer_constraints=constraints,
            seller_profiles={sid: sellers[sid].profile for sid in sellers},
            seller_inventories={sid: sellers[sid].inventory for sid in sellers},
            active_sellers=["s1", "s2", "s3"],
            max_rounds=5,
            seed=42
        )
        
        # Run negotiation
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Find completion event
        complete_events = [e for e in events if e["type"] == "negotiation_complete"]
        assert len(complete_events) == 1
        
        completion = complete_events[0]["data"]
        
        # Verify: Should have winner (s2 with best offer at $10)
        assert completion["winner_id"] == "s2"
        assert completion["winning_offer"] is not None
        assert completion["winning_offer"]["seller_id"] == "s2"
        assert completion["winning_offer"]["price"] == 10.0
        
        # Verify: All sellers got their turn in round 0
        seller_events = [e for e in events if e["type"] == "seller_response"]
        seller_ids_responded = [e["data"]["seller_id"] for e in seller_events]
        assert "s1" in seller_ids_responded
        assert "s2" in seller_ids_responded
        assert "s3" in seller_ids_responded  # All sellers got round 0
        
        # Verify exchange counts: all got 1 exchange (round 0), then negotiation ended
        assert room_state.exchanges_completed["s1"] == 1
        assert room_state.exchanges_completed["s2"] == 1
        assert room_state.exchanges_completed["s3"] == 1
        
        # Verify negotiation ended after round 0 (not round 1)
        assert completion["total_rounds"] == 1  # Only completed 1 round

