"""
Summary service for Phase 3.

WHAT: Compute session and negotiation metrics for summaries
WHY: Provide aggregated statistics for frontend display
HOW: Query database and compute totals, averages, durations
"""

from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.models import (
    Session, NegotiationRun, NegotiationOutcome, Message, Offer,
    BuyerItem
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


def compute_session_summary(
    db: Session,
    session_id: str
) -> Dict:
    """
    Compute summary statistics for a session.
    
    WHAT: Aggregate metrics across all negotiation runs in a session
    WHY: Provide session-level statistics for frontend
    HOW: Query database and compute totals, averages, counts
    
    Args:
        db: Database session
        session_id: Session ID
    
    Returns:
        Dict with summary metrics
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return {}
    
    # Get all negotiation runs for this session
    runs = db.query(NegotiationRun).filter(
        NegotiationRun.session_id == session_id
    ).all()
    
    # Get all outcomes
    outcomes = db.query(NegotiationOutcome).join(
        NegotiationRun
    ).filter(
        NegotiationRun.session_id == session_id
    ).all()
    
    # Compute metrics
    total_runs = len(runs)
    completed_runs = len([r for r in runs if r.status == 'completed'])
    failed_runs = len([r for r in runs if r.status in ('no_sellers_available', 'aborted')])
    
    # Count successful deals
    successful_deals = len([o for o in outcomes if o.decision_type == 'deal'])
    
    # Total messages across all runs
    total_messages = db.query(func.count(Message.id)).join(
        NegotiationRun
    ).filter(
        NegotiationRun.session_id == session_id
    ).scalar() or 0
    
    # Average rounds (only for completed runs)
    completed_run_rounds = [r.current_round for r in runs if r.status == 'completed']
    avg_rounds = sum(completed_run_rounds) / len(completed_run_rounds) if completed_run_rounds else 0.0
    
    # Average duration (only for completed runs)
    completed_durations = []
    for run in runs:
        if run.status == 'completed' and run.started_at and run.ended_at:
            duration = (run.ended_at - run.started_at).total_seconds()
            completed_durations.append(duration)
    
    avg_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0.0
    
    # Total cost (sum of all successful deals)
    total_cost = sum(
        o.total_cost for o in outcomes 
        if o.decision_type == 'deal' and o.total_cost is not None
    ) or 0.0
    
    # Items purchased count
    items_purchased = successful_deals
    
    # Average savings (computed from buyer items max price vs final price)
    # This is a simplified calculation - in reality would need to compare against max_price_per_unit
    avg_savings = 0.0  # Placeholder - would need more complex calculation
    
    return {
        "session_id": session_id,
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs,
        "successful_deals": successful_deals,
        "total_messages": total_messages,
        "average_rounds": round(avg_rounds, 2),
        "average_duration_seconds": round(avg_duration, 2),
        "total_cost": round(total_cost, 2),
        "items_purchased": items_purchased,
        "average_savings_per_item": round(avg_savings, 2)
    }


def compute_run_summary(
    db: Session,
    run_id: str
) -> Dict:
    """
    Compute summary for a single negotiation run.
    
    Args:
        db: Database session
        run_id: Negotiation run ID
    
    Returns:
        Dict with run metrics
    """
    run = db.query(NegotiationRun).filter(NegotiationRun.id == run_id).first()
    if not run:
        return {}
    
    # Get outcome
    outcome = db.query(NegotiationOutcome).filter(
        NegotiationOutcome.negotiation_run_id == run_id
    ).first()
    
    # Count messages
    message_count = db.query(func.count(Message.id)).filter(
        Message.negotiation_run_id == run_id
    ).scalar() or 0
    
    # Count offers
    offer_count = db.query(func.count(Offer.id)).join(
        Message
    ).filter(
        Message.negotiation_run_id == run_id
    ).scalar() or 0
    
    # Duration
    duration = None
    if run.started_at and run.ended_at:
        duration = (run.ended_at - run.started_at).total_seconds()
    
    return {
        "run_id": run_id,
        "status": run.status,
        "current_round": run.current_round,
        "max_rounds": run.max_rounds,
        "message_count": message_count,
        "offer_count": offer_count,
        "duration_seconds": round(duration, 2) if duration else None,
        "outcome": {
            "decision_type": outcome.decision_type if outcome else None,
            "selected_seller_id": outcome.selected_seller_id if outcome else None,
            "final_price": outcome.final_price_per_unit if outcome else None,
            "quantity": outcome.quantity if outcome else None,
            "total_cost": outcome.total_cost if outcome else None
        } if outcome else None
    }


def get_purchase_summaries(
    db: Session,
    session_id: str
) -> List[Dict]:
    """
    Get purchase summaries for all successful deals in a session.
    
    Args:
        db: Database session
        session_id: Session ID
    
    Returns:
        List of purchase summary dicts
    """
    outcomes = db.query(NegotiationOutcome).join(
        NegotiationRun
    ).filter(
        NegotiationRun.session_id == session_id,
        NegotiationOutcome.decision_type == 'deal'
    ).all()
    
    summaries = []
    for outcome in outcomes:
        run = db.query(NegotiationRun).filter(
            NegotiationRun.id == outcome.negotiation_run_id
        ).first()
        
        if not run:
            continue
        
        buyer_item = db.query(BuyerItem).filter(
            BuyerItem.id == run.buyer_item_id
        ).first()
        
        # Get seller name
        seller_name = None
        if outcome.selected_seller_id:
            from ..core.models import Seller
            seller = db.query(Seller).filter(Seller.id == outcome.selected_seller_id).first()
            seller_name = seller.name if seller else None
        
        duration = None
        if run.started_at and run.ended_at:
            duration = (run.ended_at - run.started_at).total_seconds()
        
        summaries.append({
            "item_name": buyer_item.item_name if buyer_item else "Unknown",
            "quantity": outcome.quantity or 0,
            "selected_seller": seller_name or "Unknown",
            "final_price_per_unit": outcome.final_price_per_unit or 0.0,
            "total_cost": outcome.total_cost or 0.0,
            "negotiation_rounds": run.current_round,
            "duration_seconds": round(duration, 2) if duration else None
        })
    
    return summaries


def get_failed_items(
    db: Session,
    session_id: str
) -> List[Dict]:
    """
    Get failed items with reasons.
    
    Args:
        db: Database session
        session_id: Session ID
    
    Returns:
        List of failed item dicts with reasons
    """
    failed_runs = db.query(NegotiationRun).filter(
        NegotiationRun.session_id == session_id,
        NegotiationRun.status.in_(['no_sellers_available', 'aborted'])
    ).all()
    
    failed_items = []
    for run in failed_runs:
        buyer_item = db.query(BuyerItem).filter(
            BuyerItem.id == run.buyer_item_id
        ).first()
        
        reason = "no_sellers_available" if run.status == "no_sellers_available" else "aborted"
        
        failed_items.append({
            "item_name": buyer_item.item_name if buyer_item else "Unknown",
            "reason": reason
        })
    
    return failed_items

