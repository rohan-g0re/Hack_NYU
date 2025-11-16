"""
Prompt templates for buyer and seller agents.

WHAT: System prompts and message rendering for LLM interactions
WHY: Consistent tone, constraints enforcement, and structured offers
HOW: Template strings with constraint injection and history conversion
"""

from typing import List
from ..llm.types import ChatMessage
from ..models.negotiation import (
    NegotiationRoomState,
    BuyerConstraints,
    SellerProfile,
    InventoryItem,
    Message
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


def render_buyer_prompt(room_state: NegotiationRoomState, visible_history: List[Message]) -> List[ChatMessage]:
    """
    Render buyer agent prompt with constraints and conversation history.
    
    Args:
        room_state: Current negotiation state
        visible_history: Messages visible to buyer (pre-filtered)
    
    Returns:
        List of ChatMessage for LLM provider
    """
    constraints = room_state.buyer_constraints
    
    # Get current seller context
    current_seller_id = None
    current_seller_name = None
    if room_state.active_sellers and room_state.current_seller_index < len(room_state.active_sellers):
        current_seller_id = room_state.active_sellers[room_state.current_seller_index]
        profile = room_state.seller_profiles.get(current_seller_id)
        current_seller_name = profile.display_name if profile else current_seller_id
    
    # Build system message with constraints
    system_content = f"""You are the Buyer negotiating to purchase items from sellers.

**Your Constraints:**
- Item needed: {constraints.item_name}
- Quantity needed: {constraints.quantity_needed} units
- Price range per unit: ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f}"""
    
    if constraints.budget_per_item:
        system_content += f"\n- Budget for this item: ${constraints.budget_per_item:.2f} (total cost must not exceed this)"
    
    system_content += f"\n- Communication style: {constraints.tone}"
    
    # Add current negotiation context
    if current_seller_name and current_seller_id:
        exchanges_done = room_state.exchanges_completed.get(current_seller_id, 0)
        system_content += f"""

**Current Negotiation:**
- You are NOW negotiating with: {current_seller_name}
- Exchange {exchanges_done + 1} of {room_state.max_rounds} with this seller
- Address this seller directly in your message"""
    
    # Fast dev mode: stricter instructions
    is_fast_dev = room_state.metadata.get("fast_dev", False)
    
    if is_fast_dev:
        system_content = "You are in FAST DEV MODE. Respond in at most 30 words. Do NOT use <think> or any hidden reasoning sections.\n\n" + system_content
    
    system_content += f"""

**Instructions:**
1. Negotiate with {current_seller_name or 'the current seller'} to get the best deal
2. Keep responses extremely concise - MAXIMUM 30 words per message
3. Do NOT use <think> or any hidden reasoning sections - reply directly in natural language
4. Do NOT repeat information you already know or have mentioned - focus on NEW information, questions, or decisions
5. Never reveal internal information like seller costs or least prices
6. Evaluate this seller's offer based on price, quantity, and terms
7. You can accept an offer if it meets your constraints

**Current Round:** {room_state.current_round + 1} of {room_state.max_rounds}
"""
    
    if constraints.priority_notes:
        system_content += f"\n**Additional Context:** {constraints.priority_notes}"
    
    messages: List[ChatMessage] = [
        {"role": "system", "content": system_content}
    ]
    
    # Add conversation history
    for msg in visible_history:
        if msg.sender_type == "buyer":
            messages.append({"role": "assistant", "content": msg.content})
        elif msg.sender_type == "seller":
            seller_name = _get_seller_display_name(room_state, msg.sender_id)
            messages.append({
                "role": "user",
                "content": f"[{seller_name}]: {msg.content}"
            })
        elif msg.sender_type == "system":
            messages.append({"role": "user", "content": f"[System]: {msg.content}"})
    
    return messages


def render_seller_prompt(
    room_state: NegotiationRoomState,
    seller_id: str,
    visible_history: List[Message]
) -> List[ChatMessage]:
    """
    Render seller agent prompt with profile, inventory, and history.
    
    Args:
        room_state: Current negotiation state
        seller_id: ID of this seller
        visible_history: Messages visible to this seller (pre-filtered)
    
    Returns:
        List of ChatMessage for LLM provider
    """
    profile = room_state.seller_profiles.get(seller_id)
    if not profile:
        raise ValueError(f"Seller profile not found: {seller_id}")
    
    inventory = room_state.seller_inventories.get(seller_id, [])
    
    # Build system message with personality and inventory
    system_content = f"""You are {profile.display_name}, a seller in this marketplace negotiation.

**Your Personality:**
- Priority: {_format_priority(profile.priority)}
- Speaking style: {_format_speaking_style(profile.speaking_style)}"""
    
    if profile.persona_notes:
        system_content += f"\n- Notes: {profile.persona_notes}"
    
    system_content += "\n\n**Your Inventory:**"
    
    if inventory:
        for item in inventory:
            system_content += f"""
- {item.name}:
  * Available: {item.quantity_available} units
  * Target price: ${item.selling_price:.2f}/unit
  * Minimum acceptable: ${item.least_price:.2f}/unit (NEVER go below this)
  * Cost: ${item.cost_price:.2f}/unit (internal only)"""
    else:
        system_content += "\n- No inventory available"
    
    # Fast dev mode: stricter instructions
    is_fast_dev = room_state.metadata.get("fast_dev", False)
    if is_fast_dev:
        system_content = "You are in FAST DEV MODE. Respond in at most 30 words. Do NOT use <think> or any hidden reasoning sections.\n\n" + system_content
    
    system_content += """

**Instructions:**
1. Respond to buyer inquiries in your characteristic style
2. NEVER offer prices below your minimum acceptable price (least_price)
3. Do not exceed available inventory quantities
4. When making a concrete offer, format it as:
   ```offer
   {"price": 10.50, "quantity": 100, "item_id": "item_name"}
   ```
5. Keep responses extremely concise - MAXIMUM 30 words per message
6. Do NOT use <think> or any hidden reasoning sections - reply directly in natural language
7. Do NOT repeat information already known or mentioned - focus on NEW offers, counter-offers, or responses to the buyer's current message"""
    
    # Style-specific instructions
    if profile.speaking_style == "rude":
        system_content += "\n8. Be blunt and transactional - no pleasantries needed"
    elif profile.speaking_style == "very_sweet":
        system_content += "\n8. Be warm, appreciative, and enthusiastic in your communication"
    else:
        system_content += "\n8. Maintain a professional, balanced tone"
    
    if profile.priority == "maximize_profit":
        system_content += "\n9. Focus on getting the highest price possible"
    else:
        system_content += "\n9. Focus on building a positive relationship, be flexible on price within reason"
    
    system_content += f"\n\n**Current Round:** {room_state.current_round + 1} of {room_state.max_rounds}"
    
    messages: List[ChatMessage] = [
        {"role": "system", "content": system_content}
    ]
    
    # Add conversation history
    for msg in visible_history:
        if msg.sender_type == "buyer":
            messages.append({"role": "user", "content": f"[Buyer]: {msg.content}"})
        elif msg.sender_type == "seller" and msg.sender_id == seller_id:
            messages.append({"role": "assistant", "content": msg.content})
        elif msg.sender_type == "system":
            messages.append({"role": "user", "content": f"[System]: {msg.content}"})
    
    return messages


def _get_seller_display_name(room_state: NegotiationRoomState, seller_id: str) -> str:
    """Get seller display name or fallback to ID."""
    profile = room_state.seller_profiles.get(seller_id)
    return profile.display_name if profile else seller_id


def _format_priority(priority: str) -> str:
    """Format priority for prompt display."""
    if priority == "maximize_profit":
        return "Maximize profit - get the best price possible"
    elif priority == "customer_retention":
        return "Customer retention - build relationships, be flexible"
    return priority


def _format_speaking_style(style: str) -> str:
    """Format speaking style for prompt display."""
    style_descriptions = {
        "rude": "Direct and blunt - no time for pleasantries",
        "neutral": "Professional and balanced",
        "very_sweet": "Warm, friendly, and appreciative"
    }
    return style_descriptions.get(style, style)

