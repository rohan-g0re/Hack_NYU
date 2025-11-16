"""
Analysis service for negotiation evaluation.

WHAT: Generate AI-powered analysis of negotiation runs
WHY: Provide insights on deal quality and negotiation effectiveness
HOW: Use LLM to analyze conversation history and outcomes
"""

from typing import Optional, Dict
from sqlalchemy.orm import Session

from ..core.models import (
    NegotiationRun, NegotiationOutcome, Message, Buyer, BuyerItem, Seller
)
from ..agents.prompts import render_analysis_prompt
from ..models.agent import BuyerConstraints
from ..llm.provider import LLMProvider
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def analyze_negotiation_run(
    db: Session,
    run_id: str,
    llm_provider: LLMProvider,
    model: str,
    temperature: float,
    max_tokens: int
) -> Optional[str]:
    """
    Analyze a negotiation run using LLM.
    
    WHAT: Generate analysis of a single negotiation conversation
    WHY: Provide insights on negotiation quality for summary page
    HOW: Fetch conversation history, call LLM with analysis prompt
    
    Args:
        db: Database session
        run_id: Negotiation run ID
        llm_provider: LLM provider instance
        model: LLM model to use
        temperature: Temperature setting
        max_tokens: Max tokens for response
        
    Returns:
        Analysis text or None if analysis fails
    """
    try:
        # Get negotiation run
        run = db.query(NegotiationRun).filter(NegotiationRun.id == run_id).first()
        if not run:
            logger.warning(f"Negotiation run {run_id} not found for analysis")
            return None
        
        # Get buyer info and constraints
        buyer_item = db.query(BuyerItem).filter(BuyerItem.id == run.buyer_item_id).first()
        if not buyer_item:
            logger.warning(f"Buyer item not found for run {run_id}")
            return None
        
        buyer = db.query(Buyer).filter(Buyer.id == buyer_item.buyer_id).first()
        buyer_name = buyer.name if buyer else "Unknown Buyer"
        
        constraints = BuyerConstraints(
            item_id=buyer_item.item_id,
            item_name=buyer_item.item_name,
            quantity_needed=buyer_item.quantity_needed,
            min_price_per_unit=buyer_item.min_price_per_unit,
            max_price_per_unit=buyer_item.max_price_per_unit
        )
        
        # Get all messages for this run
        messages = db.query(Message).filter(
            Message.negotiation_run_id == run_id
        ).order_by(Message.turn_number).all()
        
        # Convert to dict format for prompt
        conversation_history = []
        for msg in messages:
            conversation_history.append({
                'sender_name': msg.sender_name,
                'sender_type': msg.sender_type,
                'content': msg.message_text
            })
        
        # Get outcome
        outcome_record = db.query(NegotiationOutcome).filter(
            NegotiationOutcome.negotiation_run_id == run_id
        ).first()
        
        outcome = {}
        seller_info = {}
        
        if outcome_record:
            outcome = {
                'decision_type': outcome_record.decision_type,
                'final_price_per_unit': outcome_record.final_price_per_unit,
                'quantity': outcome_record.quantity,
                'reason': outcome_record.decision_reason
            }
            
            # Get seller info if deal was made
            if outcome_record.selected_seller_id:
                seller = db.query(Seller).filter(
                    Seller.id == outcome_record.selected_seller_id
                ).first()
                if seller:
                    seller_info = {
                        'name': seller.name,
                        'seller_name': seller.name
                    }
                    outcome['seller_name'] = seller.name
        else:
            # No outcome record - negotiation may have been aborted
            outcome = {
                'decision_type': 'no_deal',
                'reason': f'Status: {run.status}'
            }
        
        # Generate analysis prompt
        prompt_messages = render_analysis_prompt(
            buyer_name=buyer_name,
            constraints=constraints,
            conversation_history=conversation_history,
            outcome=outcome,
            seller_info=seller_info
        )
        
        # Call LLM
        logger.info(f"Generating analysis for run {run_id} using {model}")
        response = await llm_provider.generate(
            messages=prompt_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        analysis_text = response.get('content', '').strip()
        
        if not analysis_text:
            logger.warning(f"Empty analysis response for run {run_id}")
            return None
        
        logger.info(f"Successfully generated analysis for run {run_id} ({len(analysis_text)} chars)")
        return analysis_text
        
    except Exception as e:
        logger.error(f"Failed to analyze negotiation run {run_id}: {e}", exc_info=True)
        return None

