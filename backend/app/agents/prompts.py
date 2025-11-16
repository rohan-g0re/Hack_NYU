"""
Prompt templates for buyer and seller agents.

WHAT: System prompts and rendering helpers for agent personas
WHY: Consistent tone, constraints, and behavior across negotiations
HOW: Template strings with context injection, return ChatMessage lists
"""

from typing import List
from ..llm.types import ChatMessage
from ..models.agent import BuyerConstraints, Seller, SellerProfile
from ..models.message import Message
from ..utils.history_truncation import truncate_conversation_history


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

Important Instructions:
- Do NOT reveal your chain-of-thought or internal reasoning
- NEVER output <think>...</think> tags or similar reasoning blocks
- Respond ONLY with your final message to the sellers
- You can only see messages addressed to you or public messages
- Sellers' private information (costs, minimum prices) is hidden from you"""
    
    # Build conversation context with intelligent truncation
    history_text = ""
    if conversation_history:
        # Truncate history to prevent context overflow (max 10 messages, 4000 chars)
        truncated_history = truncate_conversation_history(
            conversation_history,
            max_messages=10,
            max_chars=4000
        )
        history_text = "\n\nRecent conversation:\n"
        for msg in truncated_history:
            visibility_note = ""
            if msg.get("sender_type") == "seller" and msg.get("sender_id") not in msg.get("visibility", []):
                visibility_note = " [Private - not visible to you]"
            history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}{visibility_note}\n"
    
    user_prompt = f"""You are negotiating for {constraints.item_name}.{history_text}

Respond with your next message. Be concise (under 100 words). Mention sellers using @SellerName if you want to address them specifically."""
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def render_seller_prompt(
    seller: Seller,
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
    # Find matching inventory item by item_name (case-insensitive)
    inventory_item = None
    for item in seller.inventory:
        if item.item_name.lower().strip() == constraints.item_name.lower().strip():
            inventory_item = item
            break
    
    if not inventory_item:
        raise ValueError(f"Seller {seller.name} does not have item {constraints.item_name}")
    
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
- You can see all public messages and messages addressed to you

Important Instructions:
- Do NOT reveal your chain-of-thought or internal reasoning
- NEVER output <think>...</think> tags or similar reasoning blocks
- Respond ONLY with your final message (and optional offer JSON)

Optional Offer Format:
If you want to make a specific offer, include a JSON block at the end:
```json
{{"offer": {{"price": <price_per_unit>, "quantity": <quantity>}}}}
```
The offer will be automatically parsed. Price must be between ${inventory_item.least_price:.2f} and ${inventory_item.selling_price:.2f}."""
    
    # Build filtered conversation context with intelligent truncation
    # Seller sees only buyer messages (filtered by visibility_filter)
    history_text = ""
    if conversation_history:
        # Truncate history to prevent context overflow (max 10 messages, 4000 chars)
        truncated_history = truncate_conversation_history(
            conversation_history,
            max_messages=10,
            max_chars=4000
        )
        history_text = "\n\nConversation history:\n"
        for msg in truncated_history:
            history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}\n"
    
    user_prompt = f"""The buyer {buyer_name} is negotiating for {constraints.item_name}.{history_text}

IMPORTANT: Do NOT repeat or echo the conversation history above. Generate YOUR OWN response as {seller.name}.
Do NOT copy the buyer's message or other sellers' messages. Write a fresh response based on the context.

Respond with your message. You can make an offer by including the JSON block format shown above."""
    
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

Important:
- Do NOT reveal your chain-of-thought or internal reasoning
- NEVER output <think>...</think> tags or similar reasoning blocks
- Respond ONLY with "ACCEPT [SellerName]" or "CONTINUE"

Be decisive but thoughtful."""

    # Add recent conversation context with intelligent truncation
    history_text = ""
    if conversation_history:
        # Truncate history for decision context (max 5 messages, 2000 chars)
        truncated_history = truncate_conversation_history(
            conversation_history,
            max_messages=5,
            max_chars=2000
        )
        history_text = "\n\nRecent conversation:\n"
        for msg in truncated_history:
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

