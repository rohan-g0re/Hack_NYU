"""
Aggressive test script for negotiation with OpenRouter.

WHAT: Comprehensive test of negotiation flow with real OpenRouter provider
WHY: Validate buyer agent decision-making and seller offer parsing
HOW: Run multiple negotiation scenarios and observe behavior
"""

import asyncio
import os
import sys
from datetime import datetime

# Add backend to path (when running from tests/manual/)
# Go up from tests/manual/ -> tests/ -> backend/
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.llm.provider_factory import get_provider
from app.agents.graph_builder import NegotiationGraph
from app.models.agent import (
    BuyerConstraints, Seller, SellerProfile, InventoryItem
)
from app.models.negotiation import NegotiationRoomState
from app.core.config import settings


def print_event(event, verbose=True):
    """Print negotiation event in readable format."""
    event_type = event.get("type", "unknown")
    data = event.get("data", {})
    timestamp = event.get("timestamp", datetime.now())
    
    if event_type == "heartbeat":
        if verbose:
            print(f"\n[HEARTBEAT] {data.get('message', '')}")
    elif event_type == "buyer_message":
        print(f"\n[BUYER] ({data.get('round', '?')}): {data.get('message', '')}")
        mentions = data.get('mentioned_sellers', [])
        if mentions:
            print(f"   [MENTIONS] {mentions}")
    elif event_type == "seller_response":
        seller_id = data.get('seller_id', '?')
        message = data.get('message', '')
        offer = data.get('offer')
        round_num = data.get('round', '?')
        print(f"\n[SELLER {seller_id}] (Round {round_num}): {message}")
        if offer:
            print(f"   [OFFER] ${offer.get('price', 0):.2f} per unit, {offer.get('quantity', 0)} units")
    elif event_type == "negotiation_complete":
        print(f"\n{'='*60}")
        print(f"[COMPLETE] NEGOTIATION COMPLETE")
        print(f"{'='*60}")
        selected = data.get('selected_seller_id')
        final_offer = data.get('final_offer')
        reason = data.get('reason', '')
        rounds = data.get('rounds', 0)
        
        if selected:
            print(f"Selected Seller: {selected}")
            if final_offer:
                print(f"Final Offer: ${final_offer.get('price', 0):.2f} per unit, {final_offer.get('quantity', 0)} units")
            print(f"Reason: {reason}")
        else:
            print(f"Status: No deal reached (max rounds: {rounds})")
        print(f"Total Rounds: {rounds}")
        print(f"{'='*60}\n")
    elif event_type == "error":
        print(f"\n[ERROR] {data.get('error', 'Unknown error')}")


async def test_scenario_1():
    """Test Scenario 1: Competitive pricing with 2 sellers."""
    print("\n" + "="*60)
    print("SCENARIO 1: Competitive Pricing (2 Sellers)")
    print("="*60)
    
    buyer_constraints = BuyerConstraints(
        item_id="laptop",
        item_name="Gaming Laptop",
        quantity_needed=1,
        min_price_per_unit=800.0,
        max_price_per_unit=1200.0
    )
    
    sellers = [
        Seller(
            seller_id="techstore",
            name="TechStore",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[
                InventoryItem(
                    item_id="laptop", item_name="Gaming Laptop",
                    cost_price=700.0, selling_price=1300.0,
                    least_price=900.0, quantity_available=5
                )
            ]
        ),
        Seller(
            seller_id="budgetelec",
            name="BudgetElectronics",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
            inventory=[
                InventoryItem(
                    item_id="laptop", item_name="Gaming Laptop",
                    cost_price=650.0, selling_price=1100.0,
                    least_price=850.0, quantity_available=3
                )
            ]
        )
    ]
    
    room_state = NegotiationRoomState(
        room_id="test_scenario_1",
        buyer_id="buyer_alice",
        buyer_name="Alice",
        buyer_constraints=buyer_constraints,
        sellers=sellers,
        max_rounds=5,
        seed=42
    )
    
    provider = get_provider()
    graph = NegotiationGraph(provider)
    
    print(f"\nBuyer: {room_state.buyer_name}")
    print(f"Item: {buyer_constraints.item_name}")
    print(f"Budget: ${buyer_constraints.min_price_per_unit:.2f} - ${buyer_constraints.max_price_per_unit:.2f}")
    print(f"Min Rounds: {settings.MIN_NEGOTIATION_ROUNDS}")
    print(f"Max Rounds: {room_state.max_rounds}")
    print(f"\nSellers:")
    for seller in sellers:
        inv = seller.inventory[0]
        print(f"  - {seller.name}: ${inv.least_price:.2f} - ${inv.selling_price:.2f} (style: {seller.profile.speaking_style})")
    
    print("\n" + "-"*60)
    print("Starting negotiation...")
    print("-"*60)
    
    async for event in graph.run(room_state):
        print_event(event)
    
    return room_state


async def test_scenario_2():
    """Test Scenario 2: Single seller, buyer needs to negotiate down."""
    print("\n" + "="*60)
    print("SCENARIO 2: Single Seller Negotiation")
    print("="*60)
    
    buyer_constraints = BuyerConstraints(
        item_id="phone",
        item_name="Smartphone",
        quantity_needed=1,
        min_price_per_unit=400.0,
        max_price_per_unit=600.0
    )
    
    sellers = [
        Seller(
            seller_id="phonestore",
            name="PhoneStore",
            profile=SellerProfile(priority="maximize_profit", speaking_style="very_sweet"),
            inventory=[
                InventoryItem(
                    item_id="phone", item_name="Smartphone",
                    cost_price=350.0, selling_price=650.0,
                    least_price=450.0, quantity_available=10
                )
            ]
        )
    ]
    
    room_state = NegotiationRoomState(
        room_id="test_scenario_2",
        buyer_id="buyer_bob",
        buyer_name="Bob",
        buyer_constraints=buyer_constraints,
        sellers=sellers,
        max_rounds=6,
        seed=123
    )
    
    provider = get_provider()
    graph = NegotiationGraph(provider)
    
    print(f"\nBuyer: {room_state.buyer_name}")
    print(f"Item: {buyer_constraints.item_name}")
    print(f"Budget: ${buyer_constraints.min_price_per_unit:.2f} - ${buyer_constraints.max_price_per_unit:.2f}")
    print(f"\nSeller: {sellers[0].name} (${sellers[0].inventory[0].least_price:.2f} - ${sellers[0].inventory[0].selling_price:.2f})")
    
    print("\n" + "-"*60)
    print("Starting negotiation...")
    print("-"*60)
    
    async for event in graph.run(room_state):
        print_event(event)
    
    return room_state


async def test_scenario_3():
    """Test Scenario 3: Multiple sellers, buyer needs to compare."""
    print("\n" + "="*60)
    print("SCENARIO 3: Multiple Sellers Comparison")
    print("="*60)
    
    buyer_constraints = BuyerConstraints(
        item_id="tablet",
        item_name="Tablet",
        quantity_needed=2,
        min_price_per_unit=200.0,
        max_price_per_unit=400.0
    )
    
    sellers = [
        Seller(
            seller_id="seller1",
            name="ElectronicsHub",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
            inventory=[
                InventoryItem(
                    item_id="tablet", item_name="Tablet",
                    cost_price=180.0, selling_price=380.0,
                    least_price=250.0, quantity_available=5
                )
            ]
        ),
        Seller(
            seller_id="seller2",
            name="TechDeals",
            profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
            inventory=[
                InventoryItem(
                    item_id="tablet", item_name="Tablet",
                    cost_price=170.0, selling_price=370.0,
                    least_price=240.0, quantity_available=4
                )
            ]
        ),
        Seller(
            seller_id="seller3",
            name="BudgetTech",
            profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
            inventory=[
                InventoryItem(
                    item_id="tablet", item_name="Tablet",
                    cost_price=175.0, selling_price=360.0,
                    least_price=230.0, quantity_available=6
                )
            ]
        )
    ]
    
    room_state = NegotiationRoomState(
        room_id="test_scenario_3",
        buyer_id="buyer_charlie",
        buyer_name="Charlie",
        buyer_constraints=buyer_constraints,
        sellers=sellers,
        max_rounds=7,
        seed=456
    )
    
    provider = get_provider()
    graph = NegotiationGraph(provider)
    
    print(f"\nBuyer: {room_state.buyer_name}")
    print(f"Item: {buyer_constraints.item_name} (Qty: {buyer_constraints.quantity_needed})")
    print(f"Budget: ${buyer_constraints.min_price_per_unit:.2f} - ${buyer_constraints.max_price_per_unit:.2f}")
    print(f"\nSellers ({len(sellers)}):")
    for seller in sellers:
        inv = seller.inventory[0]
        print(f"  - {seller.name}: ${inv.least_price:.2f} - ${inv.selling_price:.2f}")
    
    print("\n" + "-"*60)
    print("Starting negotiation...")
    print("-"*60)
    
    async for event in graph.run(room_state):
        print_event(event)
    
    return room_state


async def run_all_tests():
    """Run all test scenarios."""
    print("\n" + "="*60)
    print("OPENROUTER NEGOTIATION TEST SUITE")
    print("="*60)
    print(f"Provider: {settings.LLM_PROVIDER}")
    print(f"OpenRouter Enabled: {settings.LLM_ENABLE_OPENROUTER}")
    print(f"Min Rounds: {settings.MIN_NEGOTIATION_ROUNDS}")
    print(f"Max Rounds: {settings.MAX_NEGOTIATION_ROUNDS}")
    print("="*60)
    
    # Verify provider
    try:
        provider = get_provider()
        status = await provider.ping()
        if not status.available:
            print("[ERROR] Provider not available!")
            return
        print(f"[OK] Provider available: {status.base_url}")
        if status.models:
            print(f"   Models: {len(status.models)} available")
    except Exception as e:
        print(f"[ERROR] Error getting provider: {e}")
        return
    
    results = []
    
    try:
        print("\n>>> Running Scenario 1...")
        result1 = await test_scenario_1()
        results.append(("Scenario 1", result1))
        
        print("\n>>> Running Scenario 2...")
        result2 = await test_scenario_2()
        results.append(("Scenario 2", result2))
        
        print("\n>>> Running Scenario 3...")
        result3 = await test_scenario_3()
        results.append(("Scenario 3", result3))
        
    except KeyboardInterrupt:
        print("\n\n[WARNING] Tests interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Error during tests: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, room_state in results:
        status = room_state.status
        rounds = room_state.current_round
        selected = room_state.selected_seller_id
        print(f"\n{name}:")
        print(f"  Status: {status}")
        print(f"  Rounds: {rounds}")
        if selected:
            print(f"  Selected: {selected}")
            if room_state.final_offer:
                print(f"  Final Offer: ${room_state.final_offer.get('price', 0):.2f}")
        else:
            print(f"  Result: No deal")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())

