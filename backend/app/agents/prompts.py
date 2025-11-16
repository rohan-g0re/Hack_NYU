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


def render_buyer_prompt(
    buyer_name: str,
    constraints: BuyerConstraints,
    conversation_history: List[Message],
    available_sellers: List[Seller]
) -> List[ChatMessage]:
    """
    Render buyer system prompt with constraints and negotiation strategy.
    
    WHAT: Create strategic buyer persona with offer tracking and tactics
    WHY: Buyer needs negotiation guidance to get best deals
    HOW: Enhanced prompt with strategy, offer table, and competitive leverage
    """
    seller_names = [s.name for s in available_sellers]
    seller_mentions = ", ".join([f"@{s.name}" for s in available_sellers])
    
    # Format offers table
    offers_table = _format_offers_table(conversation_history)
    
    # Calculate budget info
    total_max_budget = constraints.max_price_per_unit * constraints.quantity_needed
    total_min_budget = constraints.min_price_per_unit * constraints.quantity_needed
    
    system_prompt = f"""You are {buyer_name}, a strategic buyer negotiating for items in a competitive marketplace.

Your Shopping List:
- Item: {constraints.item_name}
- Quantity needed: {constraints.quantity_needed}
- Budget per unit: ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f}
- Total budget range: ${total_min_budget:.2f} - ${total_max_budget:.2f}

Negotiation Strategy:
1. START LOW: Initial requests should target prices near your minimum budget
2. COMPARE SELLERS: Get offers from multiple sellers before deciding
3. COUNTER-OFFER: If price too high, make specific counter-offer with price
4. LEVERAGE COMPETITION: Mention other sellers' prices to encourage better deals
5. BE PATIENT: Don't accept first offer unless it's exceptional (close to minimum)
6. TRACK OFFERS: Remember who offered what and use it in negotiation

{offers_table}

Your Tactics:
- Ask sellers to beat each other's prices: "Can you beat @OtherSeller's offer?"
- Show budget constraints: "That's above my ${constraints.max_price_per_unit:.2f} limit"
- Create urgency: "I need to decide soon, what's your best offer?"
- Be polite but firm: "I appreciate the offer, but I need a better price"

Available Sellers: {", ".join(seller_names)}
Mention format: @SellerName (e.g., {seller_mentions})

Remember: You can only see messages addressed to you. Sellers' costs and minimum prices are hidden."""
    
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

Respond with your next message. Be concise (under 100 words). Use @SellerName to address specific sellers."""
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def _format_offers_table(conversation_history: List[Message]) -> str:
    """
    Extract and format offers from conversation history.
    
    WHAT: Create table of received offers
    WHY: Help buyer track and compare offers
    HOW: Parse messages with offers, format as table
    
    Args:
        conversation_history: Full conversation history
        
    Returns:
        Formatted offers table or "No offers yet" message
    """
    offers = []
    
    for msg in conversation_history:
        if msg.get("sender_type") == "seller" and msg.get("offer"):
            offer = msg["offer"]
            seller_name = msg.get("sender_name", "Unknown")
            turn = msg.get("turn_number", 0)
            price = offer.get("price", 0)
            quantity = offer.get("quantity", 0)
            total = price * quantity if price and quantity else 0
            
            offers.append({
                "seller": seller_name,
                "price": price,
                "quantity": quantity,
                "total": total,
                "round": turn
            })
    
    if not offers:
        return "Current Offers Received: None yet"
    
    # Format as table
    table_lines = ["Current Offers Received:"]
    table_lines.append("Seller          | Price/unit | Quantity | Total     | Round")
    table_lines.append("-" * 60)
    
    for offer in offers:
        line = (f"{offer['seller']:<15} | "
                f"${offer['price']:>8.2f} | "
                f"{offer['quantity']:>8} | "
                f"${offer['total']:>8.2f} | "
                f"{offer['round']:>5}")
        table_lines.append(line)
    
    return "\n".join(table_lines)


def render_seller_prompt(
    seller: Seller,
    constraints: BuyerConstraints,
    conversation_history: List[Message],
    buyer_name: str
) -> List[ChatMessage]:
    """
    Render seller system prompt with competition awareness and strategic pricing.
    
    WHAT: Create competitive seller persona with pricing strategy
    WHY: Seller needs to compete effectively in marketplace
    HOW: Enhanced prompt with profit calculations, competition awareness, strategy
    """
    # Find matching inventory item
    inventory_item = None
    for item in seller.inventory:
        if item.item_id == constraints.item_id:
            inventory_item = item
            break
    
    if not inventory_item:
        raise ValueError(f"Seller {seller.name} does not have item {constraints.item_id}")
    
    # Calculate profit margins
    profit_at_floor = inventory_item.least_price - inventory_item.cost_price
    profit_at_list = inventory_item.selling_price - inventory_item.cost_price
    margin_at_floor = (profit_at_floor / inventory_item.least_price * 100) if inventory_item.least_price > 0 else 0
    margin_at_list = (profit_at_list / inventory_item.selling_price * 100) if inventory_item.selling_price > 0 else 0
    
    # Build pricing strategy
    pricing_strategy = _render_pricing_strategy(seller.profile, inventory_item)
    
    # Build style instruction
    if seller.profile.speaking_style == "rude":
        style_instruction = "Be direct, slightly aggressive, and don't be overly polite. Use short, blunt responses."
    else:  # very_sweet
        style_instruction = "Be very friendly, warm, and enthusiastic. Use positive language and show genuine interest in helping the buyer."
    
    system_prompt = f"""You are {seller.name}, a seller in a COMPETITIVE marketplace negotiating with {buyer_name}.

⚠️ IMPORTANT: Other sellers are competing for this buyer. You must be competitive to win!

Your Inventory:
- Item: {inventory_item.item_name}
- Your cost: ${inventory_item.cost_price:.2f} per unit
- List price: ${inventory_item.selling_price:.2f} per unit (margin: {margin_at_list:.1f}%)
- Floor price: ${inventory_item.least_price:.2f} per unit (ABSOLUTE MINIMUM, margin: {margin_at_floor:.1f}%)
- Profit at floor: ${profit_at_floor:.2f} per unit
- Profit at list: ${profit_at_list:.2f} per unit
- Stock available: {inventory_item.quantity_available} units

Pricing Strategy ({seller.profile.priority}):
{pricing_strategy}

Communication Style: {style_instruction}

Competitive Tactics:
- Track buyer's budget signals from their messages
- Make strong opening offers to beat competitors
- Be willing to negotiate but protect your profit margin
- Watch for buyer mentioning other sellers - that means competition!
- If buyer has better offer elsewhere, decide: match it or let them go
- Early offers win deals - don't wait too long

Market Intelligence:
- Buyer's stated budget: ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f} per unit
- Your overlap zone: ${max(inventory_item.least_price, constraints.min_price_per_unit):.2f} - ${min(inventory_item.selling_price, constraints.max_price_per_unit):.2f}
- Quantity they need: {constraints.quantity_needed} units (you have {inventory_item.quantity_available})

Making Offers:
To make an offer, end your message with this JSON format:
```json
{{"offer": {{"price": <price_per_unit>, "quantity": <quantity>}}}}
```
STRICT LIMITS: Price MUST be ${inventory_item.least_price:.2f} - ${inventory_item.selling_price:.2f}, Quantity MUST be 1 - {inventory_item.quantity_available}

Be concise (under 80 words). Make offers strategically based on your pricing strategy."""
    
    # Build filtered conversation context (seller sees more than buyer)
    history_text = ""
    if conversation_history:
        history_text = "\n\nConversation history:\n"
        for msg in conversation_history[-10:]:
            history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}\n"
    
    user_prompt = f"""The buyer {buyer_name} is negotiating for {constraints.item_name}.{history_text}

Respond with your message. Include an offer using the JSON format if appropriate."""
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def _render_pricing_strategy(profile: SellerProfile, inventory_item) -> str:
    """
    Render detailed pricing strategy based on seller priority.
    
    WHAT: Create specific pricing guidance for seller
    WHY: Different priorities need different strategies
    HOW: Conditional logic based on profile.priority
    
    Args:
        profile: Seller's behavioral profile
        inventory_item: Item being sold
        
    Returns:
        Formatted pricing strategy text
    """
    if profile.priority == "customer_retention":
        return f"""- START AGGRESSIVE: Offer prices near floor (${inventory_item.least_price:.2f}) to win quickly
- PRIORITY: Winning the deal > maximizing margin per sale
- AIM: Build long-term relationship with competitive prices
- TACTIC: Make first strong offer, be flexible on price
- TARGET: Win the customer even at lower margin"""
    else:  # maximize_profit
        return f"""- START HIGH: Initial offers near list price (${inventory_item.selling_price:.2f})
- PRIORITY: Profit margin > winning at any cost
- AIM: Extract maximum value from each transaction
- TACTIC: Start high, negotiate down slowly and reluctantly
- TARGET: Highest acceptable price, walk away if margin too thin"""


def render_buyer_decision_prompt(
    buyer_name: str,
    constraints: BuyerConstraints,
    offers: List,  # List of OfferAnalysis objects
    conversation_history: List[Message]
) -> List[ChatMessage]:
    """
    Render decision prompt for buyer to select best offer.
    
    WHAT: Create prompt for final offer selection with comparison table
    WHY: Buyer needs to make informed decision from analyzed offers
    HOW: Present offers with scores, ask for selection using @mention
    
    Args:
        buyer_name: Name of the buyer
        constraints: Buyer's constraints
        offers: List of OfferAnalysis objects (analyzed offers)
        conversation_history: Full conversation history
        
    Returns:
        List of ChatMessage for decision prompt
    """
    # Build offers comparison table
    table_lines = ["OFFERS TO CHOOSE FROM:"]
    table_lines.append("=" * 80)
    table_lines.append(f"{'Seller':<15} | {'Price/unit':<10} | {'Quantity':<8} | {'Total':<10} | {'Score':<6} | {'Details':<20}")
    table_lines.append("-" * 80)
    
    for offer_analysis in offers:
        seller_name = offer_analysis.seller_name
        price = offer_analysis.offer.get("price", 0)
        quantity = offer_analysis.offer.get("quantity", 0)
        total = price * quantity
        score = offer_analysis.total_score
        
        # Build details
        details_parts = []
        if offer_analysis.profile_score > 0:
            details_parts.append(f"{offer_analysis.seller_priority}")
        details_parts.append(f"round {offer_analysis.negotiation_rounds}")
        details = ", ".join(details_parts)
        
        line = (f"{seller_name:<15} | "
                f"${price:>9.2f} | "
                f"{quantity:>8} | "
                f"${total:>9.2f} | "
                f"{score:>5.1f} | "
                f"{details:<20}")
        table_lines.append(line)
    
    table_lines.append("=" * 80)
    offers_table = "\n".join(table_lines)
    
    # Build scoring explanation
    scoring_explanation = """
Scoring Breakdown:
- Price Score (40%): Lower price within your budget = higher score
- Responsiveness (30%): Earlier offers = higher score
- Negotiation Rounds (20%): Fewer rounds = higher score
- Seller Profile (10%): Customer retention sellers get bonus
"""
    
    system_prompt = f"""You are {buyer_name}, making your final decision on which seller to buy from.

Your Budget: ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f} per unit
Quantity Needed: {constraints.quantity_needed} units

{offers_table}

{scoring_explanation}

Your Task:
Review the offers above and select the best one. Consider:
1. Price (most important - stay within budget)
2. Total cost
3. Seller reliability/responsiveness
4. Overall score

You must respond with your decision in this EXACT format:
DECISION: @SellerName

Example: "DECISION: @Alice" or "After review, DECISION: @Bob"

Choose the seller that provides the best overall value."""
    
    # Brief conversation summary
    offer_count = len([msg for msg in conversation_history if msg.get("offer")])
    round_count = max((msg.get("turn_number", 0) for msg in conversation_history), default=0)
    
    user_prompt = f"""You negotiated with {len(offers)} seller(s) over {round_count} round(s) and received {offer_count} offer(s).

Based on the analysis above, which seller do you choose?

Respond with: DECISION: @SellerName"""
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

