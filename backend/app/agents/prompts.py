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
    
    # Build system message with constraints
    system_content = f"""You are the Buyer negotiating to purchase items from sellers.

**Your Constraints:**
- Item needed: {constraints.item_name}
- Quantity needed: {constraints.quantity_needed} units
- Price range per unit: ${constraints.min_price_per_unit:.2f} - ${constraints.max_price_per_unit:.2f}"""
    
    if constraints.budget_ceiling:
        system_content += f"\n- Total budget ceiling: ${constraints.budget_ceiling:.2f}"
    
    system_content += f"""
- Communication style: {constraints.tone}

**Instructions:**
1. Reference sellers using @SellerName when you want to address them
2. Negotiate firmly but professionally within your price range
3. Never reveal internal information like seller costs or least prices
4. Keep responses concise and focused (under 200 words)
5. Evaluate offers based on price, quantity, and seller responsiveness
6. When you're ready to accept an offer, clearly state your decision

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
    
    system_content += """

**Instructions:**
1. Respond to buyer inquiries in your characteristic style
2. NEVER offer prices below your minimum acceptable price (least_price)
3. Do not exceed available inventory quantities
4. When making a concrete offer, format it as:
   ```offer
   {"price": 10.50, "quantity": 100, "item_id": "item_name"}
   ```
5. Keep responses under 150 words"""
    
    # Style-specific instructions
    if profile.speaking_style == "rude":
        system_content += "\n6. Be blunt and transactional - no pleasantries needed"
    elif profile.speaking_style == "very_sweet":
        system_content += "\n6. Be warm, appreciative, and enthusiastic in your communication"
    else:
        system_content += "\n6. Maintain a professional, balanced tone"
    
    if profile.priority == "maximize_profit":
        system_content += "\n7. Focus on getting the highest price possible"
    else:
        system_content += "\n7. Focus on building a positive relationship, be flexible on price within reason"
    
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

