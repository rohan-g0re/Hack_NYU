"""Validate prompt quality and constraints."""
from app.agents.prompts import render_buyer_prompt, render_seller_prompt
from app.models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem

# Test buyer prompt
constraints = BuyerConstraints(
    item_id="widget",
    item_name="Widget",
    quantity_needed=10,
    min_price_per_unit=5.0,
    max_price_per_unit=15.0
)

buyer_msgs = render_buyer_prompt("Bob", constraints, [], [])
print("=== BUYER PROMPT ===")
print(buyer_msgs[0]['content'])
print("\n" + "="*50 + "\n")

# Test seller prompt
seller = Seller(
    seller_id="s1",
    name="Alice",
    profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
    inventory=[
        InventoryItem(
            item_id="widget",
            item_name="Widget",
            cost_price=4.0,
            selling_price=12.0,
            least_price=7.0,
            quantity_available=20
        )
    ]
)

seller_msgs = render_seller_prompt(seller, constraints, [], "Bob")
print("=== SELLER PROMPT ===")
print(seller_msgs[0]['content'])

