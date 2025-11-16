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
    
    system_prompt = f"""You are {buyer_name} shopping for {constraints.item_name}.

NEED: {constraints.quantity_needed} units
BUDGET: ${constraints.min_price_per_unit:.2f}-${constraints.max_price_per_unit:.2f} per unit

{offers_table}

SELLERS: {", ".join(seller_names)}
Use @Name to address sellers (e.g., @{seller_names[0]})

CRITICAL RULES:
- You ARE the buyer. Start your own complete thoughts.
- NEVER continue or complete someone else's sentence.
- Write COMPLETE, STANDALONE messages that make sense on their own.
- NO thinking out loud. NO narrating. NO meta-commentary.
- Ask prices, compare offers, negotiate, decide.
- Keep under 60 words.

EXAMPLES:
Good: "Hey @{seller_names[0]}! Need {constraints.quantity_needed} {constraints.item_name}. Best price?"
Good: "@{seller_names[0]}, that's too high. Can you do $X?"
Bad: "Okay let's see..." or "I need to..." or "The user wants..."
Bad: "...and what about delivery?" (incomplete continuation)
"""
    
    # Build conversation context
    history_text = ""
    if conversation_history:
        history_text = "\n\nRecent conversation:\n"
        for msg in conversation_history[-6:]:  # Last 6 messages (reduced to prevent context bleeding)
            visibility_note = ""
            if msg.get("sender_type") == "seller" and msg.get("sender_id") not in msg.get("visibility", []):
                visibility_note = " [Private - not visible to you]"
            history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}{visibility_note}\n"
    
    user_prompt = f"""Continue negotiating.{history_text}

Your message (under 60 words):"""
    
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
    # Find matching inventory item by name (case-insensitive)
    inventory_item = None
    item_name_lower = constraints.item_name.lower().strip()
    for item in seller.inventory:
        if item.item_name.lower().strip() == item_name_lower:
            inventory_item = item
            break
    
    if not inventory_item:
        raise ValueError(f"Seller {seller.name} does not have item '{constraints.item_name}'")
    
    # Calculate profit margins
    profit_at_floor = inventory_item.least_price - inventory_item.cost_price
    profit_at_list = inventory_item.selling_price - inventory_item.cost_price
    margin_at_floor = (profit_at_floor / inventory_item.least_price * 100) if inventory_item.least_price > 0 else 0
    margin_at_list = (profit_at_list / inventory_item.selling_price * 100) if inventory_item.selling_price > 0 else 0
    
    # Build pricing strategy
    pricing_strategy = _render_pricing_strategy(seller.profile, inventory_item)
    
    # Determine conversation stage and strategy
    message_count = len([m for m in conversation_history if m.get('sender_id') == seller.seller_id])
    is_first_contact = message_count == 0
    has_made_offer = any(m.get('sender_id') == seller.seller_id and m.get('offer') for m in conversation_history)
    
    # Build style instruction with more detail
    if seller.profile.speaking_style == "rude":
        style_instruction = """SPEAKING STYLE - Direct & Blunt:
- No pleasantries, get straight to business
- Use short, punchy sentences
- Be confident and assertive
- Show you're busy and this is business
Example: "Yeah, I got it. $95/unit, 15 available. Other buyers waiting. Interested or not?"
"""
        example_message = 'DO: "Hey! Rough day? I got 15 units, decent quality. What\'s your budget looking like?"'
    else:  # very_sweet
        style_instruction = """SPEAKING STYLE - Friendly & Warm:
- Be personable and build rapport
- Use enthusiastic, positive language
- Show genuine interest in helping
- Make the buyer feel valued
Example: "Hey there! Great choice on the laptop! I'd love to help you out. I have excellent quality units in stock. What's your target price?"
"""
        example_message = 'DO: "Hi there! I\'m so glad you reached out! I have some beautiful units in stock. Tell me more about what you need!"'
    
    # Build negotiation strategy based on stage
    if is_first_contact:
        negotiation_stage = """FIRST CONTACT STRATEGY:
- Start with a greeting and acknowledge their needs
- Ask clarifying questions about their requirements
- Highlight your product quality/availability
- DON'T make an offer yet - build rapport first
- Set the stage for negotiation
"""
    elif not has_made_offer:
        negotiation_stage = """NEGOTIATION STRATEGY - Pre-Offer:
- Reference previous conversation
- Address any questions they asked
- Emphasize value proposition (quality, reliability, stock)
- Gauge their interest and urgency
- Consider making an initial offer if they seem ready
"""
    else:
        negotiation_stage = """NEGOTIATION STRATEGY - Active Deal:
- Reference your previous offer
- Counter their objections or requests
- Adjust pricing strategically if needed
- Create urgency (limited stock, other buyers)
- Try to close the deal
"""
    
    system_prompt = f"""You are {seller.name}, an experienced seller of {inventory_item.item_name}.

INVENTORY: {inventory_item.item_name}
Price range: ${inventory_item.least_price:.2f} (floor) to ${inventory_item.selling_price:.2f} (list)
Available stock: {inventory_item.quantity_available} units
Cost basis: ${inventory_item.cost_price:.2f}/unit

{style_instruction}

BUSINESS GOAL: {"Win the customer - prioritize deal over maximum profit" if seller.profile.priority == "customer_retention" else "Maximize profit - defend margins aggressively"}

BUYER INFO: {buyer_name} needs {constraints.quantity_needed} units

{negotiation_stage}

CONVERSATION RULES:
- Speak naturally as yourself (first person)
- Write COMPLETE, STANDALONE messages that make sense on their own
- NEVER continue or complete someone else's sentence
- NO meta-commentary like "Okay let me think..." or "I should..."
- Start your own thoughts - don't finish others' sentences
- Be conversational but strategic
- Keep responses under 80 words
- Compete with other sellers in the room

MAKING OFFERS:
- Only include an offer when strategically appropriate
- Format: End your message with {{"offer": {{"price": PRICE, "quantity": QUANTITY}}}}
- Price MUST be between ${inventory_item.least_price:.2f} and ${inventory_item.selling_price:.2f}
- Quantity MUST be between 1 and {inventory_item.quantity_available}

PRICING STRATEGY:
{pricing_strategy}

EXAMPLES:
{example_message}
DON'T: "Okay, the buyer wants..." or "Let me think about this..."
"""
    
    # Build filtered conversation context (seller sees more than buyer)
    history_text = ""
    if conversation_history:
        history_text = "\n\nRECENT CONVERSATION:\n"
        for msg in conversation_history[-6:]:  # Limit to last 6 messages (reduced to prevent context bleeding)
            sender = msg.get('sender_name', 'Unknown')
            content = msg.get('content', '')
            offer_info = ""
            if msg.get('offer'):
                offer_info = f" [Offered: ${msg['offer'].get('price', 0):.2f} x {msg['offer'].get('quantity', 0)} units]"
            history_text += f"{sender}: {content}{offer_info}\n"
    
    user_prompt = f"""{history_text}

Your response (natural conversation, under 80 words):"""
    
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
    
    system_prompt = f"""You are {buyer_name}. Choose which seller to buy from.

BUDGET: ${constraints.min_price_per_unit:.2f}-${constraints.max_price_per_unit:.2f}/unit
NEED: {constraints.quantity_needed} units

{offers_table}

RULES:
- Pick the best offer (price, responsiveness, value)
- State decision: "DECISION: @SellerName"
- Keep under 30 words

Example: "DECISION: @Alice - best price!"
"""
    
    user_prompt = f"""Choose best offer from {len(offers)} seller(s).

Your decision:"""
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

