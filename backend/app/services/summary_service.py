"""
Summary and metrics calculation for negotiations.

WHAT: Calculate metrics for negotiations and sessions
WHY: Provide analytics and performance tracking
HOW: Aggregate message counts, duration, costs, and outcomes
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..models.negotiation import NegotiationRoomState
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NegotiationMetrics:
    """Metrics for a single negotiation."""
    room_id: str
    total_rounds: int
    total_messages: int
    buyer_messages: int
    seller_messages: int
    total_offers: int
    accepted_offer: Optional[Dict]
    selected_seller_id: Optional[str]
    selected_seller_name: Optional[str]
    duration_seconds: float
    outcome: str  # "completed", "aborted", "no_sellers"
    final_price_per_unit: Optional[float]
    final_quantity: Optional[int]
    final_total_cost: Optional[float]


@dataclass
class SessionSummary:
    """Summary for entire session."""
    session_id: str
    total_negotiations: int
    completed_negotiations: int
    aborted_negotiations: int
    no_sellers_negotiations: int
    average_rounds: float
    average_duration_seconds: float
    average_messages_per_negotiation: float
    total_cost: float  # Sum of accepted offers (price * quantity)
    cost_savings: float  # Total (max_price - accepted_price) * quantity
    success_rate: float  # Percentage of completed negotiations


def calculate_negotiation_metrics(room_state: NegotiationRoomState) -> NegotiationMetrics:
    """
    Calculate metrics for single negotiation.
    
    WHAT: Analyze negotiation room state and extract metrics
    WHY: Track performance of individual negotiations
    HOW: Count messages, offers, calculate duration and costs
    
    Args:
        room_state: Completed or aborted negotiation state
        
    Returns:
        NegotiationMetrics with all calculated values
    """
    # Count messages by type
    total_messages = len(room_state.conversation_history)
    buyer_messages = sum(
        1 for msg in room_state.conversation_history
        if msg.get("sender_type") == "buyer"
    )
    seller_messages = sum(
        1 for msg in room_state.conversation_history
        if msg.get("sender_type") == "seller"
    )
    
    # Count total offers
    total_offers = sum(
        1 for msg in room_state.conversation_history
        if msg.get("offer") is not None
    )
    
    # Calculate duration
    duration_seconds = 0.0
    if room_state.conversation_history:
        # Get first and last message timestamps
        first_msg = room_state.conversation_history[0]
        last_msg = room_state.conversation_history[-1]
        
        first_time = first_msg.get("timestamp")
        last_time = last_msg.get("timestamp")
        
        if first_time and last_time and isinstance(first_time, datetime) and isinstance(last_time, datetime):
            duration = last_time - first_time
            duration_seconds = duration.total_seconds()
    
    # Determine outcome
    outcome = room_state.status  # "completed", "aborted", "no_sellers_available", "pending", "active"
    if outcome not in ["completed", "aborted", "no_sellers_available"]:
        outcome = "aborted"  # Normalize other states
    
    # Get accepted offer details
    accepted_offer = None
    selected_seller_name = None
    final_price_per_unit = None
    final_quantity = None
    final_total_cost = None
    
    if room_state.status == "completed" and room_state.final_offer:
        accepted_offer = room_state.final_offer
        final_price_per_unit = accepted_offer.get("price")
        final_quantity = accepted_offer.get("quantity")
        
        if final_price_per_unit and final_quantity:
            final_total_cost = final_price_per_unit * final_quantity
        
        # Get seller name
        if room_state.selected_seller_id:
            for seller in room_state.sellers:
                if seller.seller_id == room_state.selected_seller_id:
                    selected_seller_name = seller.name
                    break
    
    metrics = NegotiationMetrics(
        room_id=room_state.room_id,
        total_rounds=room_state.current_round,
        total_messages=total_messages,
        buyer_messages=buyer_messages,
        seller_messages=seller_messages,
        total_offers=total_offers,
        accepted_offer=accepted_offer,
        selected_seller_id=room_state.selected_seller_id,
        selected_seller_name=selected_seller_name,
        duration_seconds=duration_seconds,
        outcome=outcome,
        final_price_per_unit=final_price_per_unit,
        final_quantity=final_quantity,
        final_total_cost=final_total_cost
    )
    
    logger.info(
        f"Calculated metrics for {room_state.room_id}: "
        f"{metrics.total_rounds} rounds, {metrics.total_messages} messages, "
        f"{metrics.total_offers} offers, outcome={metrics.outcome}"
    )
    
    return metrics


def calculate_session_summary(
    session_id: str,
    negotiations: List[NegotiationRoomState]
) -> SessionSummary:
    """
    Aggregate metrics across all negotiations in session.
    
    WHAT: Calculate summary statistics for entire session
    WHY: Provide high-level performance overview
    HOW: Aggregate individual negotiation metrics
    
    Args:
        session_id: Session identifier
        negotiations: List of all negotiations in session
        
    Returns:
        SessionSummary with aggregated metrics
    """
    total_negotiations = len(negotiations)
    
    if total_negotiations == 0:
        # Empty session
        return SessionSummary(
            session_id=session_id,
            total_negotiations=0,
            completed_negotiations=0,
            aborted_negotiations=0,
            no_sellers_negotiations=0,
            average_rounds=0.0,
            average_duration_seconds=0.0,
            average_messages_per_negotiation=0.0,
            total_cost=0.0,
            cost_savings=0.0,
            success_rate=0.0
        )
    
    # Calculate metrics for each negotiation
    metrics_list = [calculate_negotiation_metrics(room) for room in negotiations]
    
    # Count outcomes
    completed_negotiations = sum(1 for m in metrics_list if m.outcome == "completed")
    aborted_negotiations = sum(1 for m in metrics_list if m.outcome == "aborted")
    no_sellers_negotiations = sum(1 for m in metrics_list if m.outcome == "no_sellers_available")
    
    # Calculate averages
    total_rounds = sum(m.total_rounds for m in metrics_list)
    average_rounds = total_rounds / total_negotiations if total_negotiations > 0 else 0.0
    
    total_duration = sum(m.duration_seconds for m in metrics_list)
    average_duration_seconds = total_duration / total_negotiations if total_negotiations > 0 else 0.0
    
    total_messages = sum(m.total_messages for m in metrics_list)
    average_messages_per_negotiation = total_messages / total_negotiations if total_negotiations > 0 else 0.0
    
    # Calculate costs and savings
    total_cost = 0.0
    cost_savings = 0.0
    
    for metrics, room in zip(metrics_list, negotiations):
        if metrics.outcome == "completed" and metrics.final_total_cost:
            total_cost += metrics.final_total_cost
            
            # Calculate savings: (max_price - actual_price) * quantity
            if metrics.final_price_per_unit and metrics.final_quantity:
                max_possible_cost = room.buyer_constraints.max_price_per_unit * metrics.final_quantity
                actual_cost = metrics.final_price_per_unit * metrics.final_quantity
                savings = max_possible_cost - actual_cost
                cost_savings += savings
    
    # Calculate success rate
    success_rate = (completed_negotiations / total_negotiations * 100) if total_negotiations > 0 else 0.0
    
    summary = SessionSummary(
        session_id=session_id,
        total_negotiations=total_negotiations,
        completed_negotiations=completed_negotiations,
        aborted_negotiations=aborted_negotiations,
        no_sellers_negotiations=no_sellers_negotiations,
        average_rounds=average_rounds,
        average_duration_seconds=average_duration_seconds,
        average_messages_per_negotiation=average_messages_per_negotiation,
        total_cost=total_cost,
        cost_savings=cost_savings,
        success_rate=success_rate
    )
    
    logger.info(
        f"Session {session_id} summary: "
        f"{completed_negotiations}/{total_negotiations} completed ({success_rate:.1f}%), "
        f"total cost: ${total_cost:.2f}, savings: ${cost_savings:.2f}"
    )
    
    return summary


def format_summary_report(summary: SessionSummary) -> str:
    """
    Format session summary as human-readable report.
    
    WHAT: Create text report from summary data
    WHY: Easy consumption of summary metrics
    HOW: Format key metrics with labels
    
    Args:
        summary: SessionSummary to format
        
    Returns:
        Formatted text report
    """
    report_lines = [
        f"Session Summary: {summary.session_id}",
        "=" * 50,
        f"Total Negotiations: {summary.total_negotiations}",
        f"  - Completed: {summary.completed_negotiations} ({summary.success_rate:.1f}%)",
        f"  - Aborted: {summary.aborted_negotiations}",
        f"  - No Sellers: {summary.no_sellers_negotiations}",
        "",
        f"Average Performance:",
        f"  - Rounds per negotiation: {summary.average_rounds:.1f}",
        f"  - Messages per negotiation: {summary.average_messages_per_negotiation:.1f}",
        f"  - Duration: {summary.average_duration_seconds:.1f}s",
        "",
        f"Financial Summary:",
        f"  - Total Cost: ${summary.total_cost:.2f}",
        f"  - Total Savings: ${summary.cost_savings:.2f}",
        "=" * 50
    ]
    
    return "\n".join(report_lines)

