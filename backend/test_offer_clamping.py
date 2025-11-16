"""Test seller offer clamping logic."""
import asyncio
from app.llm.provider_factory import get_provider
from app.agents.seller_agent import SellerAgent
from app.models.agent import Seller, SellerProfile, InventoryItem, BuyerConstraints
from app.models.negotiation import NegotiationRoomState

async def test_clamping():
    provider = get_provider()
    
    inventory_item = InventoryItem(
        item_id="item1",
        item_name="Test Item",
        cost_price=50.0,
        selling_price=100.0,
        least_price=70.0,
        quantity_available=5
    )
    
    seller = Seller(
        seller_id="s1",
        name="TestSeller",
        profile=SellerProfile("maximize_profit", "rude"),
        inventory=[inventory_item]
    )
    
    agent = SellerAgent(provider, seller, inventory_item)
    
    # Test manual clamping
    test_offers = [
        {"price": 65.0, "quantity": 3},  # Below least_price
        {"price": 120.0, "quantity": 3},  # Above selling_price
        {"price": 80.0, "quantity": 10},  # Quantity > available
        {"price": 85.0, "quantity": 3},   # Valid
    ]
    
    print("=== Offer Clamping Tests ===\n")
    for offer in test_offers:
        clamped = agent._clamp_offer(offer)
        print(f"Input: {offer} -> Clamped: {clamped}")

if __name__ == "__main__":
    asyncio.run(test_clamping())

