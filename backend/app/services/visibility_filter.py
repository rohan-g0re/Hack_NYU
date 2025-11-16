"""
Visibility filtering for negotiation conversations.

WHAT: Filter message history based on agent roles and permissions
WHY: Maintain information asymmetry in negotiations
HOW: Check visible_to field against agent scope tokens
"""

from typing import List, Literal
from ..models.negotiation import Message
from ..utils.logger import get_logger

logger = get_logger(__name__)


def calculate_visible_scope(agent_id: str, agent_type: Literal["buyer", "seller", "system"]) -> List[str]:
    """
    Calculate visibility scope tokens for an agent.
    
    WHAT: Determine what visibility tokens this agent can see
    WHY: Standardize visibility checking across filtering logic
    HOW: Generate list of scope patterns this agent matches
    
    Args:
        agent_id: Unique identifier for the agent
        agent_type: Type of agent (buyer/seller/system)
    
    Returns:
        List of visibility scope tokens this agent can match
    """
    scopes = ["all"]  # Everyone sees "all" marked messages
    
    if agent_type == "buyer":
        scopes.append("buyer")
        scopes.append(f"buyer:{agent_id}")
    elif agent_type == "seller":
        scopes.append("seller")
        scopes.append(f"seller:{agent_id}")
    elif agent_type == "system":
        # System sees everything (for logging/debugging)
        scopes.append("system")
        scopes.append("buyer")
        scopes.append("seller")
    
    return scopes


def is_visible(message: Message, agent_scope: List[str]) -> bool:
    """
    Check if a message is visible to an agent with given scope.
    
    WHAT: Determine if message should be shown to agent
    WHY: Enforce visibility rules per message
    HOW: Check if any message visible_to token matches agent scope
    
    Args:
        message: Message to check
        agent_scope: List of scope tokens the agent has
    
    Returns:
        True if message is visible, False otherwise
    """
    if not message.visible_to:
        # Default: visible to all if not specified
        return True
    
    # Check if any of the message's visibility tokens match agent scope
    for visibility_token in message.visible_to:
        if visibility_token in agent_scope:
            return True
        
        # Handle wildcard patterns like "seller:*"
        if visibility_token.endswith(":*"):
            prefix = visibility_token[:-2]
            if any(scope.startswith(prefix + ":") for scope in agent_scope):
                return True
    
    return False


def filter_conversation(
    history: List[Message],
    agent_id: str,
    agent_type: Literal["buyer", "seller", "system"]
) -> List[Message]:
    """
    Filter conversation history for a specific agent.
    
    WHAT: Return only messages visible to this agent
    WHY: Agents should only see messages they're permitted to see
    HOW: Calculate agent scope and filter messages via is_visible
    
    Args:
        history: Full message history
        agent_id: ID of the agent viewing the history
        agent_type: Type of agent (buyer/seller/system)
    
    Returns:
        Filtered list of messages visible to this agent
    """
    agent_scope = calculate_visible_scope(agent_id, agent_type)
    
    visible_messages = [
        msg for msg in history
        if is_visible(msg, agent_scope)
    ]
    
    logger.debug(
        f"Filtered {len(history)} messages to {len(visible_messages)} "
        f"for {agent_type}:{agent_id}"
    )
    
    return visible_messages


def filter_for_buyer(history: List[Message], buyer_id: str = "buyer") -> List[Message]:
    """
    Convenience function to filter history for buyer.
    
    Args:
        history: Full message history
        buyer_id: Buyer identifier
    
    Returns:
        Messages visible to buyer
    """
    return filter_conversation(history, buyer_id, "buyer")


def filter_for_seller(history: List[Message], seller_id: str) -> List[Message]:
    """
    Convenience function to filter history for a seller.
    
    Args:
        history: Full message history
        seller_id: Seller identifier
    
    Returns:
        Messages visible to this seller
    """
    return filter_conversation(history, seller_id, "seller")

