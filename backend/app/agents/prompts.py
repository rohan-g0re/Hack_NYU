"""
Prompt templates for buyer and seller agents.

WHAT: System prompts and rendering helpers for agent personas
WHY: Consistent tone, constraints, and behavior across negotiations
HOW: Template strings with context injection, return ChatMessage lists
"""

from typing import List
from ..llm.types import ChatMessage
from ..models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem
from ..models.message import Message


def render_buyer_prompt(
    buyer_name: str,
    constraints: BuyerConstraints,
    conversation_history: List[Message],
    available_sellers: List[Seller]
) -> List[ChatMessage]:
    """
    Render buyer system prompt with constraints and context.
    
    WHAT: Create buyer persona prompt with shopping constraints
    WHY: Buyer needs clear instructions on goals and mention convention
    HOW: System message with constraints, user message with history context
    """
    seller_names = [s.name for s in available_sellers]
    seller_mentions = ", ".join([f"@{s.name}" for s in available_sellers])
    
    system_prompt = f"""You are {buyer_name}, a buyer negotiating for items.

Your Shopping List:
- Item: {constraints.item_name}
- Quantity needed: {constraints.quantity_needed}
- Price range: ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f} per unit

Your Goals:
1. Negotiate with sellers to get the best price within your budget
2. Mention sellers by name using @SellerName format (e.g., {seller_mentions})
3. Be polite, concise, and direct
4. Compare offers from different sellers

Available Sellers: {", ".join(seller_names)}

Remember: You can only see messages addressed to you or public messages. Sellers' private information (costs, minimum prices) is hidden from you."""
    
    # Build conversation context
    history_text = ""
    if conversation_history:
        history_text = "\n\nRecent conversation:\n"
        for msg in conversation_history[-10:]:  # Last 10 messages
            visibility_note = ""
            if msg.get("sender_type") == "seller" and msg.get("sender_id") not in msg.get("visibility", []):
                visibility_note = " [Private - not visible to you]"
            history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}{visibility_note}\n"
    
    user_prompt = f"""You are negotiating for {constraints.item_name}.{history_text}

CRITICAL: Write ONLY the actual message you want to send. DO NOT write about what you're going to do.
DO NOT start with "Okay", "Let me", "I need to", "I should", etc.
DO NOT explain your thinking or strategy.
Just write the direct message as if you're talking to the sellers right now.

Good example: "@GadgetHub and @CompuWorld, I need 5 mice. My budget is $15-25 per unit. What can you offer?"
BAD example: "Okay, the user wants me to negotiate for a mouse. Let me check..."

Write your message NOW (under 100 words):"""
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def render_seller_prompt(
    seller: Seller,
    inventory_item: InventoryItem,
    constraints: BuyerConstraints,
    conversation_history: List[Message],
    buyer_name: str
) -> List[ChatMessage]:
    """
    Render seller system prompt with inventory and behavioral profile.
    
    WHAT: Create seller persona prompt with inventory bounds and style
    WHY: Seller needs pricing constraints and behavioral instructions
    HOW: System message with inventory/priority/style, user message with filtered history
    """
    # Build priority instruction
    if seller.profile.priority == "customer_retention":
        priority_instruction = "Your priority is building long-term customer relationships. Be willing to offer competitive prices to keep the buyer happy."
    else:  # maximize_profit
        priority_instruction = "Your priority is maximizing profit. Try to get the highest price possible while still making a sale."
    
    # Build style instruction
    if seller.profile.speaking_style == "rude":
        style_instruction = "Be direct, slightly aggressive, and don't be overly polite. Use short, blunt responses."
    else:  # very_sweet
        style_instruction = "Be very friendly, warm, and enthusiastic. Use positive language and show genuine interest in helping the buyer."
    
    system_prompt = f"""You are {seller.name}, a seller negotiating with {buyer_name}.

Your Inventory:
- Item: {inventory_item.item_name}
- Cost price: ${inventory_item.cost_price:.2f} per unit (your cost)
- Selling price: ${inventory_item.selling_price:.2f} per unit (list price)
- Minimum acceptable price: ${inventory_item.least_price:.2f} per unit (you cannot go below this)
- Quantity available: {inventory_item.quantity_available}

Pricing Rules:
- You CANNOT offer below ${inventory_item.least_price:.2f} per unit
- You CANNOT offer above ${inventory_item.selling_price:.2f} per unit
- You CANNOT offer more than {inventory_item.quantity_available} units

Your Behavior:
- {priority_instruction}
- {style_instruction}
- Be concise (under 80 words)
- You can ONLY see messages from the buyer and your own messages
- You CANNOT see other sellers, their messages, or their offers

IMPORTANT VISIBILITY RULES:
- You DO NOT know about other sellers unless the buyer explicitly mentions them
- You DO NOT see what other sellers are offering
- Only respond based on what the buyer says to you directly

Optional Offer Format:
If you want to make a specific offer, include a JSON block at the end:
```json
{{"offer": {{"price": <price_per_unit>, "quantity": <quantity>}}}}
```
The offer will be automatically parsed. Price must be between ${inventory_item.least_price:.2f} and ${inventory_item.selling_price:.2f}."""
    
    # Build filtered conversation context - seller ONLY sees buyer messages and their own messages
    history_text = ""
    if conversation_history:
        history_text = "\n\nConversation history:\n"
        for msg in conversation_history[-10:]:
            sender_type = msg.get('sender_type', '')
            sender_id = msg.get('sender_id', '')
            
            # Seller can only see:
            # 1. Messages from the buyer (sender_type == "buyer")
            # 2. Their own messages (sender_id == seller.seller_id)
            if sender_type == "buyer" or sender_id == seller.seller_id:
                history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}\n"
    
    user_prompt = f"""The buyer {buyer_name} is negotiating for {constraints.item_name}.{history_text}

CRITICAL: Write ONLY your actual response to the buyer. DO NOT think out loud.
DO NOT start with "Okay", "Let's see", "The user", etc.
DO NOT explain what you're going to do.
Just respond directly as if you're talking to the buyer right now.

Good example: "I can offer $20 per unit for 50 mice. Free shipping included!"
BAD example: "Okay, let's see. The user mentioned... I need to check..."

Write your response NOW (under 80 words):"""
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def render_decision_prompt(
    buyer_name: str,
    constraints: BuyerConstraints,
    valid_offers: List[dict],
    conversation_history: List[Message],
    current_round: int,
    min_rounds: int
) -> List[ChatMessage]:
    """
    Render decision prompt for buyer to decide if they want to accept an offer.
    
    WHAT: Create prompt asking buyer if they want to accept or continue negotiating
    WHY: Buyer agent should make the decision based on conversation context
    HOW: Present valid offers and ask for decision
    
    Args:
        buyer_name: Name of buyer
        constraints: Buyer's constraints
        valid_offers: List of valid offers with seller_id, seller_name, price, quantity
        conversation_history: Full conversation history
        current_round: Current round number
        min_rounds: Minimum rounds before buyer can decide
        
    Returns:
        List of ChatMessage for decision prompt
    """
    system_prompt = f"""You are {buyer_name}, a buyer making a decision about offers.

Your Requirements:
- Item: {constraints.item_name}
- Quantity needed: {constraints.quantity_needed}
- Budget: ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f} per unit

Current Round: {current_round}
Minimum Rounds Required: {min_rounds}

You have received the following valid offers that meet your requirements:"""

    offers_text = ""
    for i, offer in enumerate(valid_offers, 1):
        seller_name = offer.get("seller_name", offer.get("seller_id", "Unknown"))
        price = offer.get("price", 0)
        quantity = offer.get("quantity", 0)
        offers_text += f"\n{i}. {seller_name}: ${price:.2f} per unit, {quantity} units"

    system_prompt += offers_text

    system_prompt += f"""

Decision Instructions:
- If you want to ACCEPT an offer, respond with: "ACCEPT [SellerName]" (e.g., "ACCEPT TechStore")
- If you want to CONTINUE negotiating, respond with: "CONTINUE" or "KEEP NEGOTIATING"
- Consider: price, seller responsiveness, conversation quality, and whether you've negotiated enough rounds
- You should negotiate at least {min_rounds} rounds before accepting unless the offer is exceptional

Be decisive but thoughtful."""

    # Add recent conversation context
    history_text = ""
    if conversation_history:
        history_text = "\n\nRecent conversation:\n"
        for msg in conversation_history[-5:]:  # Last 5 messages for decision context
            history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}\n"

    user_prompt = f"""You are at round {current_round}.{history_text}

Do you want to ACCEPT one of the offers above, or CONTINUE negotiating?

Respond with either:
- "ACCEPT [SellerName]" to accept an offer
- "CONTINUE" or "KEEP NEGOTIATING" to continue"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

