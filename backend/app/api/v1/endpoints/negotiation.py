"""
Negotiation control endpoints for Phase 4.

WHAT: Start, control, and query negotiation runs
WHY: Enable frontend to manage negotiation lifecycle
HOW: FastAPI endpoints wrapping SessionManager and NegotiationGraph
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime
import json

from ....core.session_manager import session_manager, active_rooms
from ....core.database import get_db
from ....core.models import (
    NegotiationRun, Message, Offer, Buyer, BuyerItem, Seller
)
from ....models.api_schemas import (
    SendMessageRequest,
    SendMessageResponse,
    NegotiationStateResponse,
    Offer as OfferSchema,
    BuyerConstraints
)
from ....services.message_router import parse_mentions
from ....utils.exceptions import (
    SessionNotFoundError,
    RoomNotFoundError,
    NegotiationAlreadyActiveError
)
from ....utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/negotiation/{room_id}/start")
async def start_negotiation(room_id: str) -> Dict:
    """
    Start a negotiation run.
    
    WHAT: Activate negotiation and prepare for streaming
    WHY: Begin agent interactions
    HOW: Call SessionManager.start_negotiation
    
    Args:
        room_id: Negotiation run ID (room_id)
        
    Returns:
        Dict with status and stream_url
        
    Raises:
        RoomNotFoundError: If room doesn't exist
        NegotiationAlreadyActiveError: If already active
    """
    logger.info(f"POST /negotiation/{room_id}/start - Starting negotiation")
    logger.info(f"Current active_rooms: {list(active_rooms.keys())}")
    
    # Check if already active
    if room_id in active_rooms:
        logger.warning(f"Room {room_id} already in active_rooms, raising 409")
        raise NegotiationAlreadyActiveError(
            message=f"Negotiation {room_id} is already active",
            code="NEGOTIATION_ALREADY_ACTIVE"
        )
    
    logger.info(f"Calling session_manager.start_negotiation for {room_id}")
    result = session_manager.start_negotiation(room_id)
    logger.info(f"start_negotiation returned: {result}")
    
    if "error" in result:
        if "not found" in result["error"].lower():
            raise RoomNotFoundError(
                message=f"Room {room_id} not found",
                code="ROOM_NOT_FOUND"
            )
        elif "already" in result["error"].lower():
            raise NegotiationAlreadyActiveError(
                message=result["error"],
                code="NEGOTIATION_ALREADY_ACTIVE"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    
    return {
        "status": "active",
        "stream_url": f"/api/v1/negotiation/{room_id}/stream",
        "run_id": room_id,
        "started_at": result.get("started_at")
    }


@router.post("/negotiation/{room_id}/message", status_code=status.HTTP_202_ACCEPTED)
async def send_message(room_id: str, request: SendMessageRequest) -> SendMessageResponse:
    """
    Send a manual buyer message (optional feature).
    
    WHAT: Inject buyer message into negotiation
    WHY: Allow manual override of agent messages
    HOW: Record message and parse mentions
    
    Args:
        room_id: Negotiation run ID
        request: SendMessageRequest with message text
        
    Returns:
        SendMessageResponse with message_id and mentioned sellers
        
    Raises:
        RoomNotFoundError: If room doesn't exist
    """
    logger.info(f"Sending manual message to room {room_id}")
    
    with get_db() as db:
        run = db.query(NegotiationRun).filter(NegotiationRun.id == room_id).first()
        if not run:
            raise RoomNotFoundError(
                message=f"Room {room_id} not found",
                code="ROOM_NOT_FOUND"
            )
        
        # Get room state to parse mentions
        room_state = None
        if room_id in active_rooms:
            room_state, _ = active_rooms[room_id]
        
        mentioned_sellers = []
        if room_state:
            mentioned_sellers = parse_mentions(request.message, room_state.sellers)
        
        # Record message
        buyer_item = db.query(BuyerItem).filter(BuyerItem.id == run.buyer_item_id).first()
        buyer = db.query(Buyer).filter(Buyer.id == buyer_item.buyer_id).first() if buyer_item else None
        
        message = session_manager.record_message(
            run_id=room_id,
            turn_number=run.current_round + 1,
            sender_type="buyer",
            sender_id=buyer.id if buyer else "manual",
            sender_name=buyer.name if buyer else "Buyer",
            message_text=request.message,
            mentioned_agents=mentioned_sellers
        )
        
        return SendMessageResponse(
            message_id=message.id,
            timestamp=message.timestamp,
            mentioned_sellers=mentioned_sellers,
            processing=True
        )


@router.post("/negotiation/{room_id}/decide")
async def force_decision(
    room_id: str,
    decision_type: str,
    selected_seller_id: Optional[str] = None,
    final_price_per_unit: Optional[float] = None,
    quantity: Optional[int] = None,
    decision_reason: Optional[str] = None
) -> Dict:
    """
    Force a decision to finalize negotiation.
    
    WHAT: Manually complete negotiation with outcome
    WHY: Allow manual override or early termination
    HOW: Call SessionManager.finalize_run with validation
    
    Args:
        room_id: Negotiation run ID
        decision_type: 'deal' or 'no_deal'
        selected_seller_id: Seller ID if deal
        final_price_per_unit: Final price if deal
        quantity: Quantity if deal
        decision_reason: Reason for decision
        
    Returns:
        Dict with outcome details
        
    Raises:
        RoomNotFoundError: If room doesn't exist
        ValidationError: If decision parameters are invalid
    """
    from ....utils.exceptions import ValidationError
    from ....core.models import NegotiationParticipant
    
    logger.info(f"Forcing decision for room {room_id}: {decision_type}")
    
    # Validate decision_type
    if decision_type not in ("deal", "no_deal"):
        raise ValidationError(
            message="decision_type must be 'deal' or 'no_deal'",
            code="VALIDATION_ERROR",
            details={"field": "decision_type", "value": decision_type}
        )
    
    with get_db() as db:
        # Check if run exists
        run = db.query(NegotiationRun).filter(NegotiationRun.id == room_id).first()
        if not run:
            raise RoomNotFoundError(
                message=f"Room {room_id} not found",
                code="ROOM_NOT_FOUND"
            )
        
        # Validate deal-specific parameters
        if decision_type == "deal":
            if not selected_seller_id:
                raise ValidationError(
                    message="selected_seller_id is required for decision_type=deal",
                    code="VALIDATION_ERROR",
                    details={"field": "selected_seller_id"}
                )
            
            if final_price_per_unit is None:
                raise ValidationError(
                    message="final_price_per_unit is required for decision_type=deal",
                    code="VALIDATION_ERROR",
                    details={"field": "final_price_per_unit"}
                )
            
            if quantity is None:
                raise ValidationError(
                    message="quantity is required for decision_type=deal",
                    code="VALIDATION_ERROR",
                    details={"field": "quantity"}
                )
            
            # Ensure seller is a participant
            participant = db.query(NegotiationParticipant).filter(
                NegotiationParticipant.negotiation_run_id == room_id,
                NegotiationParticipant.seller_id == selected_seller_id
            ).first()
            
            if not participant:
                raise ValidationError(
                    message=f"Seller {selected_seller_id} is not a participant in this negotiation",
                    code="VALIDATION_ERROR",
                    details={"field": "selected_seller_id", "value": selected_seller_id}
                )
            
            # Validate against buyer constraints
            buyer_item = db.query(BuyerItem).filter(BuyerItem.id == run.buyer_item_id).first()
            if buyer_item:
                min_price = buyer_item.min_price_per_unit
                max_price = buyer_item.max_price_per_unit
                
                if not (min_price <= final_price_per_unit <= max_price):
                    raise ValidationError(
                        message=f"final_price_per_unit ${final_price_per_unit:.2f} is outside buyer constraints (${min_price:.2f} - ${max_price:.2f})",
                        code="VALIDATION_ERROR",
                        details={
                            "field": "final_price_per_unit",
                            "value": final_price_per_unit,
                            "min": min_price,
                            "max": max_price
                        }
                    )
                
                if quantity < 1 or quantity > buyer_item.quantity_needed:
                    raise ValidationError(
                        message=f"quantity {quantity} is outside valid range (1 - {buyer_item.quantity_needed})",
                        code="VALIDATION_ERROR",
                        details={
                            "field": "quantity",
                            "value": quantity,
                            "min": 1,
                            "max": buyer_item.quantity_needed
                        }
                    )
    
    try:
        outcome = session_manager.finalize_run(
            run_id=room_id,
            decision_type=decision_type,
            selected_seller_id=selected_seller_id,
            final_price_per_unit=final_price_per_unit,
            quantity=quantity,
            decision_reason=decision_reason or "Manual decision via force_decision endpoint",
            emit_event=True  # Record system message for forced decisions
        )
        
        return {
            "outcome_id": outcome.id,
            "decision_type": outcome.decision_type,
            "selected_seller_id": outcome.selected_seller_id,
            "final_price": outcome.final_price_per_unit,
            "quantity": outcome.quantity,
            "total_cost": outcome.total_cost,
            "decision_reason": outcome.decision_reason
        }
    except ValueError as e:
        raise RoomNotFoundError(
            message=str(e),
            code="ROOM_NOT_FOUND"
        )


@router.get("/negotiation/{room_id}/state", response_model=NegotiationStateResponse)
async def get_negotiation_state(
    room_id: str,
    agent_id: Optional[str] = None,
    agent_type: Optional[str] = None
) -> NegotiationStateResponse:
    """
    Get current negotiation state.
    
    WHAT: Retrieve conversation history, offers, and status
    WHY: Display negotiation progress to user
    HOW: Query DB and cached room state, optionally filter by agent visibility
    
    Args:
        room_id: Negotiation run ID
        agent_id: Optional agent ID for visibility filtering
        agent_type: Optional agent type ('buyer' or 'seller')
        
    Returns:
        NegotiationStateResponse with state details
        
    Raises:
        RoomNotFoundError: If room doesn't exist
    """
    logger.info(f"Getting state for room {room_id}")
    
    with get_db() as db:
        run = db.query(NegotiationRun).filter(NegotiationRun.id == room_id).first()
        if not run:
            raise RoomNotFoundError(
                message=f"Room {room_id} not found",
                code="ROOM_NOT_FOUND"
            )
        
        # Get buyer item
        buyer_item = db.query(BuyerItem).filter(BuyerItem.id == run.buyer_item_id).first()
        
        # Get conversation history
        messages = db.query(Message).filter(
            Message.negotiation_run_id == room_id
        ).order_by(Message.turn_number).all()
        
        conversation_history = [
            {
                "message_id": msg.id,
                "turn_number": msg.turn_number,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                "sender_type": msg.sender_type,
                "sender_id": msg.sender_id,
                "sender_name": msg.sender_name,
                "content": msg.message_text,
                "mentioned_agents": json.loads(msg.mentioned_agents) if msg.mentioned_agents else []
            }
            for msg in messages
        ]
        
        # Apply visibility filter if agent_id provided
        if agent_id and agent_type:
            # TODO: Apply visibility_filter.filter_conversation
            # For now, return all messages
            pass
        
        # Get current offers
        offers = db.query(Offer).join(Message).filter(
            Message.negotiation_run_id == room_id
        ).all()
        
        current_offers = {}
        for offer in offers:
            current_offers[offer.seller_id] = OfferSchema(
                price=offer.price_per_unit,
                quantity=offer.quantity
            )
        
        return NegotiationStateResponse(
            room_id=room_id,
            item_name=buyer_item.item_name if buyer_item else "Unknown",
            status=run.status,
            current_round=run.current_round,
            max_rounds=run.max_rounds,
            conversation_history=conversation_history,
            current_offers=current_offers,
            buyer_constraints=BuyerConstraints(
                min_price_per_unit=buyer_item.min_price_per_unit if buyer_item else 0.0,
                max_price_per_unit=buyer_item.max_price_per_unit if buyer_item else 0.0
            )
        )

