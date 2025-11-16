"""
Demo script to run a complete negotiation and display events in terminal + markdown.

WHAT: Interactive demonstration of Phase 2 negotiation with real LM Studio
WHY: Visual verification of agent behavior and negotiation flow
HOW: Run complete negotiation with detailed event logging and markdown export
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path if running directly
sys.path.insert(0, str(Path(__file__).parent))

from app.llm.provider_factory import get_provider
from app.agents.graph_builder import NegotiationGraph
from app.agents.buyer_agent import BuyerAgent
from app.agents.seller_agent import SellerAgent
from app.models.negotiation import (
    NegotiationRoomState,
    BuyerConstraints,
    SellerProfile,
    InventoryItem
)
from app.services.room_builder import filter_sellers_by_item
from app.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

# Global markdown content accumulator
markdown_content = []


def add_to_markdown(text: str):
    """Add text to markdown content."""
    markdown_content.append(text)


def print_banner(text: str, char: str = "="):
    """Print a formatted banner."""
    width = 80
    banner = f"\n{char * width}\n{text.center(width)}\n{char * width}\n"
    print(banner)
    add_to_markdown(f"\n## {text}\n\n")


def print_event(event: dict):
    """Pretty print a negotiation event and add to markdown."""
    event_type = event["type"]
    data = event["data"]
    
    if event_type == "buyer_message":
        print_banner("BUYER MESSAGE", "-")
        round_num = data['round'] + 1
        seller_id = data.get('seller_id', 'ALL')
        message = data['content']
        
        print(f"[BUYER] Round: {round_num}")
        print(f"Negotiating with: {seller_id}")
        print(f"Message: {message}")
        print()
        
        add_to_markdown(f"### Round {round_num} - Buyer → {seller_id}\n\n")
        add_to_markdown(f"**Buyer:** {message}\n\n")
    
    elif event_type == "seller_response":
        seller_id = data['seller_id']
        print_banner(f"SELLER RESPONSE: {seller_id}", "-")
        round_num = data['round'] + 1
        exchange_num = data.get('exchange_number', '?')
        message = data['content']
        
        print(f"[SELLER] Round: {round_num}")
        print(f"Exchange #{exchange_num} with this seller")
        print(f"Message: {message[:200]}{'...' if len(message) > 200 else ''}")
        
        md_message = message
        if data.get('offer'):
            offer = data['offer']
            print(f"\n[OFFER] DETAILS:")
            print(f"   Price: ${offer['price']:.2f} per unit")
            print(f"   Quantity: {offer['quantity']} units")
            print(f"   Total: ${offer['price'] * offer['quantity']:.2f}")
            
            md_message += f"\n\n**OFFER:** ${offer['price']:.2f} per unit × {offer['quantity']} units = ${offer['price'] * offer['quantity']:.2f} total"
        
        if data.get('violations'):
            violations = ', '.join(data['violations'])
            print(f"[WARNING] Violations: {violations}")
            md_message += f"\n\n⚠️ **Violations:** {violations}"
        
        print()
        add_to_markdown(f"**{seller_id}:** {md_message}\n\n")
    
    elif event_type == "negotiation_complete":
        print_banner("*** NEGOTIATION COMPLETE ***", "=")
        total_rounds = data['total_rounds']
        print(f"Total Rounds: {total_rounds}")
        
        add_to_markdown(f"## Negotiation Complete\n\n")
        add_to_markdown(f"**Total Rounds:** {total_rounds}\n\n")
        
        if data.get('exchanges_completed'):
            print(f"\nExchanges per seller:")
            add_to_markdown("**Exchanges per seller:**\n\n")
            for seller_id, count in data['exchanges_completed'].items():
                print(f"  {seller_id}: {count} exchanges")
                add_to_markdown(f"- {seller_id}: {count} exchanges\n")
            add_to_markdown("\n")
        
        if data['winner_id']:
            winner = data['winner_id']
            print(f"\n[SUCCESS] WINNER: {winner}")
            add_to_markdown(f"### 🏆 Winner: {winner}\n\n")
            
            if data['winning_offer']:
                offer = data['winning_offer']
                print(f"\n[WINNING OFFER]:")
                print(f"   Seller: {offer['seller_id']}")
                print(f"   Price: ${offer['price']:.2f} per unit")
                print(f"   Quantity: {offer['quantity']} units")
                print(f"   Total Cost: ${offer['price'] * offer['quantity']:.2f}")
                
                add_to_markdown("**Winning Offer:**\n\n")
                add_to_markdown(f"- Seller: {offer['seller_id']}\n")
                add_to_markdown(f"- Price: ${offer['price']:.2f} per unit\n")
                add_to_markdown(f"- Quantity: {offer['quantity']} units\n")
                add_to_markdown(f"- Total Cost: ${offer['price'] * offer['quantity']:.2f}\n\n")
        else:
            print(f"\n[RESULT] NO WINNER")
            add_to_markdown("**Result:** No winner - no acceptable offers found\n\n")
        
        reason = data['reason']
        print(f"\nReason: {reason}")
        add_to_markdown(f"**Reason:** {reason}\n\n")
        print()
    
    elif event_type == "error":
        print_banner("*** ERROR ***", "-")
        agent = data.get('agent', 'unknown')
        seller_id = data.get('seller_id', '')
        error_msg = data['error']
        recoverable = data.get('recoverable', False)
        
        print(f"Agent: {agent}")
        if seller_id:
            print(f"Seller ID: {seller_id}")
        print(f"Error: {error_msg}")
        print(f"Recoverable: {recoverable}")
        print()
        
        add_to_markdown(f"### ⚠️ Error\n\n")
        add_to_markdown(f"- Agent: {agent}\n")
        if seller_id:
            add_to_markdown(f"- Seller: {seller_id}\n")
        add_to_markdown(f"- Error: {error_msg}\n")
        add_to_markdown(f"- Recoverable: {recoverable}\n\n")
    
    elif event_type == "heartbeat":
        current_seller = data.get('current_seller', 'N/A')
        heartbeat_msg = f"[HEARTBEAT] Round {data['round'] + 1} | Current: {current_seller} | Messages: {data['messages_count']} | Offers: {data['offers_count']}"
        print(heartbeat_msg)


async def run_demo_negotiation(fast_dev: bool = False):
    """Run a demonstration negotiation.
    
    Args:
        fast_dev: If True, use aggressive timeouts and short responses for faster iteration
    """
    
    # Initialize markdown with header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_to_markdown(f"# Multi-Agent Negotiation Demo\n\n")
    add_to_markdown(f"**Date:** {timestamp}\n\n")
    if fast_dev:
        add_to_markdown("**Mode:** FAST DEV MODE (aggressive timeouts, short responses)\n\n")
    add_to_markdown("---\n\n")
    
    print_banner("*** MULTI-AGENT NEGOTIATION DEMO ***", "=")
    if fast_dev:
        print("Using REAL LM Studio for all agents (FAST DEV MODE)\n")
    else:
        print("Using REAL LM Studio for all agents\n")
    
    # Get LM Studio provider
    try:
        provider = get_provider(fast_dev=fast_dev)
        status = await provider.ping()
        
        if not status.available:
            print("[ERROR] LM Studio is not available!")
            print(f"Error: {status.error}")
            print("\nPlease ensure:")
            print("1. LM Studio is running")
            print("2. A model is loaded")
            print("3. Server is accessible at http://127.0.0.1:1234")
            return False
        
        print(f"[SUCCESS] LM Studio Connected!")
        print(f"   Models available: {', '.join(status.models) if status.models else 'unknown'}")
        print(f"   Base URL: {status.base_url}")
        
    except Exception as e:
        print(f"[ERROR] Failed to connect to LM Studio: {e}")
        return False
    
    # Setup negotiation scenario with realistic items
    print_banner("SCENARIO SETUP", "-")
    
    constraints = BuyerConstraints(
        item_id="ballpoint_pens",
        item_name="Ballpoint Pens",
        quantity_needed=500,
        min_price_per_unit=0.50,
        max_price_per_unit=1.50,
        budget_per_item=600.0,
        tone="neutral"
    )
    
    add_to_markdown("## Scenario Setup\n\n")
    add_to_markdown("### Buyer Requirements\n\n")
    
    print("[BUYER] REQUIREMENTS:")
    print(f"   Item: {constraints.item_name}")
    print(f"   Quantity Needed: {constraints.quantity_needed} units")
    print(f"   Price Range: ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f} per unit")
    print(f"   Budget for this item: ${constraints.budget_per_item:.2f}")
    print()
    
    add_to_markdown(f"- **Item:** {constraints.item_name}\n")
    add_to_markdown(f"- **Quantity Needed:** {constraints.quantity_needed} units\n")
    add_to_markdown(f"- **Price Range:** ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f} per unit\n")
    add_to_markdown(f"- **Budget:** ${constraints.budget_per_item:.2f}\n\n")
    
    # Setup sellers with realistic business profiles
    seller1_profile = SellerProfile(
        seller_id="office_supply_co",
        display_name="Office Supply Co",
        priority="maximize_profit",
        speaking_style="neutral"
    )
    
    seller2_profile = SellerProfile(
        seller_id="friendly_stationery",
        display_name="Friendly Stationery",
        priority="customer_retention",
        speaking_style="very_sweet"
    )
    
    seller3_profile = SellerProfile(
        seller_id="budget_wholesale",
        display_name="Budget Wholesale",
        priority="maximize_profit",
        speaking_style="rude"
    )
    
    inventory1 = [
        InventoryItem(
            item_id="ballpoint_pens",
            name="Ballpoint Pens",
            quantity_available=600,
            cost_price=0.40,
            least_price=0.80,
            selling_price=1.20
        )
    ]
    
    inventory2 = [
        InventoryItem(
            item_id="ballpoint_pens",
            name="Ballpoint Pens",
            quantity_available=800,
            cost_price=0.35,
            least_price=0.70,
            selling_price=1.00
        )
    ]
    
    inventory3 = [
        InventoryItem(
            item_id="ballpoint_pens",
            name="Ballpoint Pens",
            quantity_available=550,
            cost_price=0.45,
            least_price=0.85,
            selling_price=1.15
        )
    ]
    
    # Add a seller who doesn't have the requested item (to demonstrate filtering)
    seller4_profile = SellerProfile(
        seller_id="coffee_shop",
        display_name="Coffee Shop",
        priority="maximize_profit",
        speaking_style="neutral"
    )
    
    inventory4 = [
        InventoryItem(
            item_id="coffee_cups",
            name="Coffee Cups",
            quantity_available=200,
            cost_price=2.0,
            least_price=3.50,
            selling_price=5.00
        )
    ]
    
    add_to_markdown("### Sellers\n\n")
    
    print("[SELLERS] (all sellers in marketplace):")
    print(f"\n1. {seller1_profile.display_name}")
    print(f"   Priority: {seller1_profile.priority}")
    print(f"   Style: {seller1_profile.speaking_style}")
    print(f"   Price Range: ${inventory1[0].least_price:.2f} - ${inventory1[0].selling_price:.2f}")
    print(f"   Stock: {inventory1[0].quantity_available} units")
    
    add_to_markdown(f"#### 1. {seller1_profile.display_name}\n\n")
    add_to_markdown(f"- Priority: {seller1_profile.priority}\n")
    add_to_markdown(f"- Style: {seller1_profile.speaking_style}\n")
    add_to_markdown(f"- Price Range: ${inventory1[0].least_price:.2f} - ${inventory1[0].selling_price:.2f}\n")
    add_to_markdown(f"- Stock: {inventory1[0].quantity_available} units\n\n")
    
    print(f"\n2. {seller2_profile.display_name}")
    print(f"   Priority: {seller2_profile.priority}")
    print(f"   Style: {seller2_profile.speaking_style}")
    print(f"   Price Range: ${inventory2[0].least_price:.2f} - ${inventory2[0].selling_price:.2f}")
    print(f"   Stock: {inventory2[0].quantity_available} units")
    
    add_to_markdown(f"#### 2. {seller2_profile.display_name}\n\n")
    add_to_markdown(f"- Priority: {seller2_profile.priority}\n")
    add_to_markdown(f"- Style: {seller2_profile.speaking_style}\n")
    add_to_markdown(f"- Price Range: ${inventory2[0].least_price:.2f} - ${inventory2[0].selling_price:.2f}\n")
    add_to_markdown(f"- Stock: {inventory2[0].quantity_available} units\n\n")
    
    print(f"\n3. {seller3_profile.display_name}")
    print(f"   Priority: {seller3_profile.priority}")
    print(f"   Style: {seller3_profile.speaking_style}")
    print(f"   Price Range: ${inventory3[0].least_price:.2f} - ${inventory3[0].selling_price:.2f}")
    print(f"   Stock: {inventory3[0].quantity_available} units")
    
    add_to_markdown(f"#### 3. {seller3_profile.display_name}\n\n")
    add_to_markdown(f"- Priority: {seller3_profile.priority}\n")
    add_to_markdown(f"- Style: {seller3_profile.speaking_style}\n")
    add_to_markdown(f"- Price Range: ${inventory3[0].least_price:.2f} - ${inventory3[0].selling_price:.2f}\n")
    add_to_markdown(f"- Stock: {inventory3[0].quantity_available} units\n\n")
    
    print(f"\n4. {seller4_profile.display_name} (does NOT have Ballpoint Pens)")
    print(f"   Priority: {seller4_profile.priority}")
    print(f"   Style: {seller4_profile.speaking_style}")
    print(f"   Has: {inventory4[0].name} (different item)")
    print()
    
    add_to_markdown(f"#### 4. {seller4_profile.display_name} (does NOT have Ballpoint Pens)\n\n")
    add_to_markdown(f"- Priority: {seller4_profile.priority}\n")
    add_to_markdown(f"- Style: {seller4_profile.speaking_style}\n")
    add_to_markdown(f"- Has: {inventory4[0].name} (different item)\n\n")
    
    # Setup seller inventories dict (includes all sellers)
    seller_inventories = {
        "office_supply_co": inventory1,
        "friendly_stationery": inventory2,
        "budget_wholesale": inventory3,
        "coffee_shop": inventory4  # This seller doesn't have the requested item
    }
    
    # Filter sellers to only those who have the requested item
    print("[SETUP] Filtering sellers by item availability...")
    active_sellers = filter_sellers_by_item(
        constraints.item_id,
        seller_inventories
    )
    
    if not active_sellers:
        print(f"[ERROR] No sellers found with item '{constraints.item_id}'!")
        print("Cannot proceed with negotiation.")
        return False
    
    print(f"[SUCCESS] Found {len(active_sellers)} seller(s) with item '{constraints.item_id}': {', '.join(active_sellers)}")
    print(f"[INFO] Excluded sellers without this item: {set(seller_inventories.keys()) - set(active_sellers)}")
    print()
    
    # Create agents (only for active sellers to save resources)
    print("[SETUP] Creating AI agents for active sellers...")
    
    # Fast dev mode: use smaller max_tokens and lower temperature
    if fast_dev:
        buyer_max_tokens = 64
        seller_max_tokens = 48
        temp = 0.4
        print("[FAST DEV] Using aggressive settings: max_tokens=64/48, temp=0.4")
    else:
        buyer_max_tokens = 200
        seller_max_tokens = 150
        temp = 0.7
    
    buyer_agent = BuyerAgent(provider, constraints, temperature=temp, max_tokens=buyer_max_tokens)
    
    seller_agents_dict = {}
    if "office_supply_co" in active_sellers:
        seller_agents_dict["office_supply_co"] = SellerAgent(provider, seller1_profile, inventory1, temperature=temp, max_tokens=seller_max_tokens)
    if "friendly_stationery" in active_sellers:
        seller_agents_dict["friendly_stationery"] = SellerAgent(provider, seller2_profile, inventory2, temperature=temp, max_tokens=seller_max_tokens)
    if "budget_wholesale" in active_sellers:
        seller_agents_dict["budget_wholesale"] = SellerAgent(provider, seller3_profile, inventory3, temperature=temp, max_tokens=seller_max_tokens)
    if "coffee_shop" in active_sellers:
        seller_agents_dict["coffee_shop"] = SellerAgent(provider, seller4_profile, inventory4, temperature=temp, max_tokens=seller_max_tokens)
    
    # Create graph
    graph = NegotiationGraph(
        buyer_agent=buyer_agent,
        seller_agents=seller_agents_dict
    )
    
    # Setup room state (include all seller profiles, but only active sellers participate)
    room_state = NegotiationRoomState(
        buyer_id="buyer_demo",
        buyer_constraints=constraints,
        seller_profiles={
            "office_supply_co": seller1_profile,
            "friendly_stationery": seller2_profile,
            "budget_wholesale": seller3_profile,
            "coffee_shop": seller4_profile
        },
        seller_inventories=seller_inventories,
        active_sellers=active_sellers,  # Only sellers with the requested item
        max_rounds=5,
        seed=42
    )
    
    # Set fast_dev flag in metadata for agents/prompts to read
    room_state.metadata["fast_dev"] = fast_dev
    
    print("[SUCCESS] Ready to negotiate!\n")
    print("Starting negotiation in 2 seconds...\n")
    await asyncio.sleep(2)
    
    # Run negotiation
    add_to_markdown("## Negotiation Conversation\n\n")
    print_banner("*** STARTING NEGOTIATION ***", "=")
    
    start_time = datetime.now()
    event_count = 0
    
    try:
        async for event in graph.run(room_state):
            event_count += 1
            print_event(event)
            
            # Small delay for readability
            await asyncio.sleep(0.1)
            
            if event["type"] == "negotiation_complete":
                break
    
    except KeyboardInterrupt:
        print("\n\n[WARNING] Negotiation interrupted by user")
        return False
    except Exception as e:
        print(f"\n\n[ERROR] Error during negotiation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Summary
    add_to_markdown("## Summary\n\n")
    print_banner("*** NEGOTIATION SUMMARY ***", "=")
    
    duration_str = f"{duration:.1f} seconds"
    print(f"Duration: {duration_str}")
    print(f"Total Events: {event_count}")
    print(f"Total Rounds: {room_state.current_round}")
    print(f"Messages Exchanged: {len(room_state.message_history)}")
    print(f"Offers Made: {len(room_state.offer_history)}")
    print(f"Final Status: {room_state.status}")
    print()
    
    add_to_markdown(f"- **Duration:** {duration_str}\n")
    add_to_markdown(f"- **Total Events:** {event_count}\n")
    add_to_markdown(f"- **Total Rounds:** {room_state.current_round}\n")
    add_to_markdown(f"- **Messages Exchanged:** {len(room_state.message_history)}\n")
    add_to_markdown(f"- **Offers Made:** {len(room_state.offer_history)}\n")
    add_to_markdown(f"- **Final Status:** {room_state.status}\n\n")
    
    # Show all offers
    if room_state.offer_history:
        print("[OFFERS] ALL OFFERS RECEIVED:")
        add_to_markdown("### All Offers Received\n\n")
        offers_by_seller = {}
        for offer in room_state.offer_history:
            if offer.seller_id not in offers_by_seller:
                offers_by_seller[offer.seller_id] = []
            offers_by_seller[offer.seller_id].append(offer)
        
        for seller_id, offers in offers_by_seller.items():
            profile = room_state.seller_profiles.get(seller_id)
            seller_name = profile.display_name if profile else seller_id
            print(f"\n   {seller_name}:")
            add_to_markdown(f"#### {seller_name}\n\n")
            for i, offer in enumerate(offers, 1):
                offer_line = f"      Round {offer.round_number + 1}: ${offer.price:.2f}/unit x {offer.quantity} = ${offer.price * offer.quantity:.2f} [{offer.status}]"
                print(offer_line)
                add_to_markdown(f"- Round {offer.round_number + 1}: ${offer.price:.2f}/unit × {offer.quantity} = ${offer.price * offer.quantity:.2f} [{offer.status}]\n")
            add_to_markdown("\n")
    
    print("\n" + "=" * 80 + "\n")
    
    # Save markdown to file
    output_file = Path(__file__).parent.parent / "conversations.md"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("".join(markdown_content))
        print(f"\n[SUCCESS] Conversation saved to: {output_file}")
    except Exception as e:
        print(f"\n[WARNING] Failed to save markdown: {e}")
    
    return True


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run multi-agent negotiation demo")
    parser.add_argument(
        "--fast-dev",
        action="store_true",
        help="Use fast dev mode: aggressive timeouts, short responses, no <think> sections"
    )
    args = parser.parse_args()
    
    try:
        success = await run_demo_negotiation(fast_dev=args.fast_dev)
        return 0 if success else 1
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INFO] Demo interrupted by user")
        sys.exit(1)

