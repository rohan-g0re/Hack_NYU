"""
Conversation visibility filtering.

WHAT: Filter messages based on agent visibility rules
WHY: Implement opaque negotiation where agents see different views
HOW: Filter message list based on sender, mentions, and visibility field
"""

from typing import List, Literal
from ..models.message import Message


def filter_conversation(
    history: List[Message],
    agent_id: str,
    agent_type: Literal["buyer", "seller"]
) -> List[Message]:
    """
    Filter conversation history for a specific agent's visibility.
    
    WHAT: Return messages visible to the given agent
    WHY: Implement opaque negotiation model
    HOW: Apply visibility rules based on agent type
    
    Visibility Rules:
    - Buyer sees: all buyer messages, seller messages where buyer is in visibility list
    - Seller sees: ONLY buyer messages (sellers cannot see other sellers' messages)
    
    Args:
        history: Full conversation history
        agent_id: ID of the agent viewing
        agent_type: Type of agent ("buyer" or "seller")
        
    Returns:
        Filtered list of messages visible to the agent
    """
    if not history:
        return []
    
    filtered = []
    
    for msg in history:
        sender_id = msg.get("sender_id", "")
        sender_type = msg.get("sender_type", "")
        visibility = msg.get("visibility", [])
        
        if agent_type == "buyer":
            # Buyer sees:
            # 1. All buyer messages
            # 2. Seller messages where buyer_id is in visibility list
            if sender_type == "buyer":
                filtered.append(msg)
            elif sender_type == "seller" and agent_id in visibility:
                filtered.append(msg)
        
        elif agent_type == "seller":
            # Seller sees ONLY buyer messages (not other sellers' messages)
            if sender_type == "buyer":
                filtered.append(msg)
    
    return filtered

