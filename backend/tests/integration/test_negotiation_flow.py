"""
Integration tests for Phase 2 negotiation flow.

WHAT: End-to-end negotiation scenarios without HTTP layer
WHY: Validate complete buyer-seller-graph orchestration
HOW: Use mock providers with full NegotiationGraph execution
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
@pytest.mark.integration
class TestNegotiationFlowIntegration:
    """Integration tests for complete negotiation scenarios."""
    
    @pytest.mark.asyncio
    async def test_happy_path_negotiation_with_winner(self):
        """Test successful negotiation ending with an accepted offer."""
        # Setup buyer with acceptable price range
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Premium Widget",
            quantity_needed=100,
            min_price_per_unit=7.0,
            max_price_per_unit=12.0,
            budget_per_item=1200.0  # 9.5 * 120 = 1140, so 1200 allows it
        )
        
        # Setup 3 sellers with different inventories
        seller1_profile = SellerProfile(
            seller_id="aggressive_seller",
            display_name="AggressiveCorp",
            priority="maximize_profit",
            speaking_style="rude"
        )
        
        seller2_profile = SellerProfile(
            seller_id="friendly_seller",
            display_name="FriendlyInc",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        
        seller3_profile = SellerProfile(
            seller_id="balanced_seller",
            display_name="BalancedLLC",
            priority="maximize_profit",
            speaking_style="neutral"
        )
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Premium Widget",
                quantity_available=150,
                cost_price=6.0,
                least_price=8.0,
                selling_price=12.0
            )
        ]
        
        # Setup mock providers with scripted responses
        # Sequential: buyer sends to each seller one at a time
        buyer_responses = [
            "What's your best price for 100 units?",  # To aggressive_seller
            "What's your best price for 100 units?",  # To friendly_seller
            "What's your best price for 100 units?",  # To balanced_seller
        ]
        
        seller1_responses = [
            '''Price is $11 per unit.
```offer
{"price": 11.0, "quantity": 100, "item_id": "widget"}
```'''
        ]
        
        seller2_responses = [
            '''I'd be delighted to help! Here's my offer:
```offer
{"price": 9.5, "quantity": 120, "item_id": "widget"}
```
Thank you for considering us!'''
        ]
        
        seller3_responses = [
            '''Standard offer:
```offer
{"price": 10.0, "quantity": 100, "item_id": "widget"}
```'''
        ]
        
        buyer_provider = MockLLMProvider(responses=buyer_responses)
        seller1_provider = MockLLMProvider(responses=seller1_responses)
        seller2_provider = MockLLMProvider(responses=seller2_responses)
        seller3_provider = MockLLMProvider(responses=seller3_responses)
        
        # Create agents
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        seller1_agent = SellerAgent(seller1_provider, seller1_profile, inventory)
        seller2_agent = SellerAgent(seller2_provider, seller2_profile, inventory)
        seller3_agent = SellerAgent(seller3_provider, seller3_profile, inventory)
        
        # Create graph
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={
                "aggressive_seller": seller1_agent,
                "friendly_seller": seller2_agent,
                "balanced_seller": seller3_agent
            }
        )
        
        # Setup room state
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={
                "aggressive_seller": seller1_profile,
                "friendly_seller": seller2_profile,
                "balanced_seller": seller3_profile
            },
            seller_inventories={
                "aggressive_seller": inventory,
                "friendly_seller": inventory,
                "balanced_seller": inventory
            },
            active_sellers=["aggressive_seller", "friendly_seller", "balanced_seller"],
            max_rounds=5,
            seed=42
        )
        
        # Run negotiation
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Validate event sequence
        event_types = [e["type"] for e in events]
        assert "buyer_message" in event_types
        assert "seller_response" in event_types
        assert "negotiation_complete" in event_types
        
        # Validate sequential order: buyer→seller1, seller1→buyer, buyer→seller2, seller2→buyer, buyer→seller3, seller3→buyer
        message_sequence = []
        for e in events:
            if e["type"] == "buyer_message":
                message_sequence.append(("buyer", e["data"]["seller_id"]))
            elif e["type"] == "seller_response":
                message_sequence.append(("seller", e["data"]["seller_id"]))
        
        # Expected: buyer→aggressive, aggressive→buyer, buyer→friendly, friendly→buyer, buyer→balanced, balanced→buyer
        expected_sequence = [
            ("buyer", "aggressive_seller"),
            ("seller", "aggressive_seller"),
            ("buyer", "friendly_seller"),
            ("seller", "friendly_seller"),
            ("buyer", "balanced_seller"),
            ("seller", "balanced_seller"),
        ]
        
        assert message_sequence == expected_sequence, f"Expected {expected_sequence}, got {message_sequence}"
        
        # Validate we got seller responses
        seller_response_events = [e for e in events if e["type"] == "seller_response"]
        assert len(seller_response_events) == 3  # Exactly 3 sellers, one response each (early exit after round 0)
        
        # Validate completion
        complete_events = [e for e in events if e["type"] == "negotiation_complete"]
        assert len(complete_events) == 1
        
        completion = complete_events[0]["data"]
        # Debug: print completion info if winner not found
        if completion["winner_id"] is None:
            print(f"Completion: {completion}")
            print(f"Offers: {[e['data'].get('offer') for e in seller_response_events]}")
        
        # With offers at 9.5, 10.0, and 11.0, lowest is 9.5 from friendly_seller
        assert completion["winner_id"] == "friendly_seller"  # Lowest price at 9.5
        assert completion["winning_offer"] is not None
        assert completion["winning_offer"]["price"] == 9.5
        
        # Verify exchanges_completed tracking
        assert "exchanges_completed" in completion
        assert completion["exchanges_completed"]["aggressive_seller"] == 1
        assert completion["exchanges_completed"]["friendly_seller"] == 1
        assert completion["exchanges_completed"]["balanced_seller"] == 1
        
        # Validate state
        assert room_state.status == "completed"
        assert len(room_state.message_history) > 0
        assert len(room_state.offer_history) >= 3
    
    @pytest.mark.asyncio
    async def test_partial_seller_failure_continues_negotiation(self):
        """Test that one seller failing doesn't stop others."""
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=50,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        seller1_profile = SellerProfile(seller_id="s1", display_name="Seller1")
        seller2_profile = SellerProfile(seller_id="s2", display_name="Seller2")
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=100,
                cost_price=4.0,
                least_price=6.0,
                selling_price=10.0
            )
        ]
        
        buyer_responses = ["@Seller1 @Seller2 send offers"]
        seller1_responses = ["Unable to respond"]  # Will fail
        seller2_responses = [
            '''Here's my offer:
```offer
{"price": 8.0, "quantity": 60, "item_id": "widget"}
```'''
        ]
        
        buyer_provider = MockLLMProvider(responses=buyer_responses)
        seller1_provider = MockLLMProvider(should_fail=True)  # This one fails
        seller2_provider = MockLLMProvider(responses=seller2_responses)
        
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        seller1_agent = SellerAgent(seller1_provider, seller1_profile, inventory)
        seller2_agent = SellerAgent(seller2_provider, seller2_profile, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={"s1": seller1_agent, "s2": seller2_agent}
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={"s1": seller1_profile, "s2": seller2_profile},
            seller_inventories={"s1": inventory, "s2": inventory},
            active_sellers=["s1", "s2"],
            max_rounds=3,
            seed=42
        )
        
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Should have at least one error event for failed seller
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1
        assert any(e["data"]["agent"] == "seller" and e["data"]["seller_id"] == "s1" for e in error_events)
        
        # Should still have successful seller response
        seller_responses = [e for e in events if e["type"] == "seller_response"]
        assert len(seller_responses) >= 1
        assert any(e["data"]["seller_id"] == "s2" for e in seller_responses)
        
        # Should complete with s2's offer
        complete_events = [e for e in events if e["type"] == "negotiation_complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["data"]["winner_id"] == "s2"
        
        # In sequential mode, failed sellers remain in active_sellers but negotiation continues
        # The negotiation completed successfully with s2's offer
        assert room_state.status == "completed"
    
    @pytest.mark.asyncio
    async def test_no_acceptable_offers_max_rounds(self):
        """Test negotiation ending without acceptable offers."""
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=7.0  # Too low
        )
        
        seller_profile = SellerProfile(seller_id="s1", display_name="Seller1")
        
        inventory = [
            InventoryItem(
                item_id="widget",
                name="Widget",
                quantity_available=200,
                cost_price=6.0,
                least_price=8.0,  # Above buyer's max
                selling_price=12.0
            )
        ]
        
        buyer_responses = ["Send offer", "Any better price?", "Final offer?"]
        seller_responses = [
            '''My price is firm:
```offer
{"price": 9.0, "quantity": 100, "item_id": "widget"}
```''',
            "Price remains $9 per unit.",
            "Cannot go lower than $9."
        ]
        
        buyer_provider = MockLLMProvider(responses=buyer_responses)
        seller_provider = MockLLMProvider(responses=seller_responses)
        
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        seller_agent = SellerAgent(seller_provider, seller_profile, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={"s1": seller_agent}
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={"s1": seller_profile},
            seller_inventories={"s1": inventory},
            active_sellers=["s1"],
            max_rounds=3,
            seed=42
        )
        
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Should complete
        complete_events = [e for e in events if e["type"] == "negotiation_complete"]
        assert len(complete_events) == 1
        
        completion = complete_events[0]["data"]
        assert completion["winner_id"] is None
        assert completion["winning_offer"] is None
        assert "max rounds" in completion["reason"].lower() or "without" in completion["reason"].lower()
        
        # Should have reached max rounds (max_rounds=3 means rounds 0, 1, 2, so current_round ends at 2)
        assert room_state.current_round == 2  # Completed 3 rounds (0-indexed: 0, 1, 2)
        assert room_state.status == "completed"
        # Verify all exchanges completed
        assert room_state.exchanges_completed["s1"] == 3
    
    @pytest.mark.asyncio
    async def test_buyer_failure_stops_negotiation(self):
        """Test that buyer failure stops the negotiation."""
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=50,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        seller_profile = SellerProfile(seller_id="s1", display_name="Seller1")
        inventory = []
        
        buyer_provider = MockLLMProvider(should_fail=True)
        seller_provider = MockLLMProvider(responses=["Ready"])
        
        buyer_agent = BuyerAgent(buyer_provider, constraints)
        seller_agent = SellerAgent(seller_provider, seller_profile, inventory)
        
        graph = NegotiationGraph(
            buyer_agent=buyer_agent,
            seller_agents={"s1": seller_agent}
        )
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={"s1": seller_profile},
            seller_inventories={"s1": inventory},
            active_sellers=["s1"],
            max_rounds=5,
            seed=42
        )
        
        events = []
        async for event in graph.run(room_state):
            events.append(event)
        
        # Should have error event for buyer
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1
        assert any(e["data"]["agent"] == "buyer" for e in error_events)
        
        # Should mark as failed
        assert room_state.status == "failed"
        
        # Should not have completion event
        complete_events = [e for e in events if e["type"] == "negotiation_complete"]
        assert len(complete_events) == 0

