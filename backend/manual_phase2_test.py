"""
Manual Phase 2 test script - Run a complete negotiation.

WHAT: End-to-end test of negotiation graph with real provider
WHY: Validate complete negotiation flow and event emission
HOW: Create test scenario and run NegotiationGraph
"""

import asyncio
from app.llm.provider_factory import get_provider
from app.agents.graph_builder import NegotiationGraph
from app.models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem
from app.models.negotiation import NegotiationRoomState


async def main():
    print("=== Phase 2 Manual Test ===\n")
    
    # Get provider
    try:
        provider = get_provider()
        status = await provider.ping()
        print(f"Provider Status: {status.available}")
        print(f"Base URL: {status.base_url}")
        if status.models:
            print(f"Available Models: {len(status.models)} models")
            print(f"Sample Models: {status.models[:3]}\n")
        else:
            print("No models available\n")
        
        if not status.available:
            print("ERROR: Provider not available. Please start LM Studio.")
            return
    except Exception as e:
        print(f"ERROR: Could not get provider: {e}")
        return
    
    # Create test scenario
    buyer_constraints = BuyerConstraints(
        item_id="laptop",
        item_name="Gaming Laptop",
        quantity_needed=2,
        min_price_per_unit=800.0,
        max_price_per_unit=1200.0
    )
    
    sellers = [
        Seller(
            seller_id="seller1",
            name="TechStore",
            profile=SellerProfile(
                priority="customer_retention",
                speaking_style="very_sweet"
            ),
            inventory=[
                InventoryItem(
                    item_id="laptop",
                    item_name="Gaming Laptop",
                    cost_price=700.0,
                    selling_price=1100.0,
                    least_price=900.0,
                    quantity_available=5
                )
            ]
        ),
        Seller(
            seller_id="seller2",
            name="BargainPCs",
            profile=SellerProfile(
                priority="maximize_profit",
                speaking_style="rude"
            ),
            inventory=[
                InventoryItem(
                    item_id="laptop",
                    item_name="Gaming Laptop",
                    cost_price=650.0,
                    selling_price=1150.0,
                    least_price=850.0,
                    quantity_available=3
                )
            ]
        )
    ]
    
    room_state = NegotiationRoomState(
        room_id="test_room",
        buyer_id="buyer1",
        buyer_name="Alice",
        buyer_constraints=buyer_constraints,
        sellers=sellers,
        conversation_history=[],
        current_round=0,
        max_rounds=3,
        seed=42
    )
    
    # Run negotiation
    print("Starting negotiation...\n")
    graph = NegotiationGraph(provider)
    
    events = []
    try:
        async for event in graph.run(room_state):
            events.append(event)
            print(f"[{event['type'].upper()}]")
            print(f"  Data: {event['data']}")
            print(f"  Time: {event['timestamp']}\n")
            
            # Stop after completion
            if event['type'] == 'negotiation_complete':
                break
            
            # Safety limit
            if len(events) > 20:
                print("WARNING: Stopping after 20 events (safety limit)")
                break
    except Exception as e:
        print(f"ERROR during negotiation: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Print final state
    print("\n=== Final State ===")
    print(f"Status: {room_state.status}")
    print(f"Rounds: {room_state.current_round}")
    print(f"Selected Seller: {room_state.selected_seller_id}")
    print(f"Final Offer: {room_state.final_offer}")
    print(f"Decision Reason: {room_state.decision_reason}")
    print(f"Total Messages: {len(room_state.conversation_history)}")
    print(f"Total Events: {len(events)}")
    
    # Event summary
    event_types = {}
    for event in events:
        event_type = event['type']
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print("\n=== Event Summary ===")
    for event_type, count in event_types.items():
        print(f"  {event_type}: {count}")


if __name__ == "__main__":
    asyncio.run(main())

