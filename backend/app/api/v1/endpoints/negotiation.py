"""
Negotiation endpoints for Phase 4.

WHAT: Negotiation control and state management endpoints
WHY: Start negotiations, get state, send messages, force decisions
HOW: FastAPI router with graph orchestration and session_manager
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import Optional
from datetime import datetime

from ....models.api_schemas import (
    StartNegotiationResponse,
    NegotiationStateResponse,
    SendMessageRequest,
    ForceDecisionRequest,
    DecisionResponse,
    Message,
    Offer,
    OfferWithSeller,
    BuyerConstraints,
    SelectedSellerInfo
)
from ....core.session_manager import session_manager
from ....core.database import get_db
from ....core.models import NegotiationRun, NegotiationStatus
from ....core.config import settings
from ....agents.graph_builder import NegotiationGraph
from ....llm.provider_factory import get_provider
from ....services.visibility_filter import filter_conversation
from ....services.decision_engine import analyze_offers, select_best_offer
from ....utils.exceptions import (
    RoomNotFoundException,
    NegotiationAlreadyActiveException,
    NegotiationNotActiveException
)
from ....utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def run_negotiation_graph(room_id: str):
    """
    Background task to run negotiation graph.
    
    WHAT: Execute negotiation graph to completion
    WHY: Run graph asynchronously while streaming events
    HOW: Get room state, create graph, run to completion, finalize
    """
    try:
        logger.info(f"Starting negotiation graph for room: {room_id}")
        
        # Get room state
        room_state = session_manager.get_room_state(room_id)
        if not room_state:
            logger.error(f"Room state not found for {room_id}")
            return
        
        # Get provider
        provider = get_provider()
        
        # Create and run graph
        graph = NegotiationGraph(provider)
        
        # Run graph (this will emit events that are streamed via SSE)
        async for event in graph.run(room_state):
            # Events are captured by the streaming endpoint
            # Here we just need to update the room state
            pass
        
        # Finalize the negotiation
        outcome_data = {
            "status": room_state.status,
            "selected_seller_id": room_state.selected_seller_id,
            "selected_seller_name": next(
                (s.name for s in room_state.sellers if s.seller_id == room_state.selected_seller_id),
                None
            ) if room_state.selected_seller_id else None,
            "final_price_per_unit": room_state.final_offer.get("price") if room_state.final_offer else None,
            "final_quantity": room_state.final_offer.get("quantity") if room_state.final_offer else None,
            "final_total_cost": (
                room_state.final_offer["price"] * room_state.final_offer["quantity"]
                if room_state.final_offer else None
            ),
            "total_rounds": room_state.current_round,
            "total_messages": len(room_state.conversation_history),
            "total_offers": sum(len(offers) for offers in room_state.offers_by_seller.values()),
            "duration_seconds": 0.0,  # Calculated from DB timestamps
            "decision_reason": room_state.decision_reason
        }
        
        session_manager.finalize_run(room_id, outcome_data)
        logger.info(f"Negotiation completed for room: {room_id}")
        
    except Exception as e:
        logger.error(f"Error in negotiation graph for room {room_id}: {e}", exc_info=True)
        # Update room state to error status
        room_state = session_manager.get_room_state(room_id)
        if room_state:
            room_state.status = "aborted"
            session_manager.update_room_state(room_id, room_state)


@router.post("/negotiation/{room_id}/start", response_model=StartNegotiationResponse)
async def start_negotiation(room_id: str, background_tasks: BackgroundTasks):
    """
    Start a negotiation.
    
    WHAT: Initialize negotiation and begin graph execution
    WHY: Entry point for negotiation flow
    HOW: Load room state, spawn background task, return stream URL
    """
    try:
        logger.info(f"Starting negotiation for room: {room_id}")
        
        # Check if room exists and get current status
        with get_db() as db:
            run = db.query(NegotiationRun).filter_by(room_id=room_id).first()
            if not run:
                raise RoomNotFoundException(room_id)
            
            # Check if already active
            if run.status == NegotiationStatus.ACTIVE:
                existing_state = session_manager.get_room_state(room_id)
                if existing_state:
                    raise NegotiationAlreadyActiveException(room_id)
        
        # Start negotiation (loads into memory)
        room_state = session_manager.start_negotiation(room_id)
        
        # Spawn background task for graph execution
        background_tasks.add_task(run_negotiation_graph, room_id)
        
        # Build response
        response = StartNegotiationResponse(
            room_id=room_id,
            status="active",
            item_name=room_state.buyer_constraints.item_name,
            participating_sellers=[s.name for s in room_state.sellers],
            buyer_opening_message=f"Hello sellers! I'm looking to buy {room_state.buyer_constraints.item_name}.",
            stream_url=f"/api/v1/negotiation/{room_id}/stream"
        )
        
        logger.info(f"Negotiation started for room {room_id} with {len(room_state.sellers)} sellers")
        return response
        
    except (RoomNotFoundException, NegotiationAlreadyActiveException):
        raise
    except Exception as e:
        logger.error(f"Error starting negotiation for room {room_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to start negotiation"}}
        )


@router.get("/negotiation/{room_id}/state", response_model=NegotiationStateResponse)
async def get_negotiation_state(
    room_id: str,
    agent_id: Optional[str] = None,
    agent_type: Optional[str] = None
):
    """
    Get current negotiation state.
    
    WHAT: Retrieve negotiation state with optional visibility filter
    WHY: Frontend needs current state for display
    HOW: Get room state, apply visibility filter if specified, return
    """
    try:
        logger.info(f"Fetching state for room: {room_id} (agent: {agent_id}, type: {agent_type})")
        
        # Get room state from cache or database
        room_state = session_manager.get_room_state(room_id)
        
        if not room_state:
            # Try to load from database
            with get_db() as db:
                run = db.query(NegotiationRun).filter_by(room_id=room_id).first()
                if not run:
                    raise RoomNotFoundException(room_id)
                
                # If not in cache, it might not be started yet
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": {"code": "NEGOTIATION_NOT_STARTED", "message": "Negotiation has not been started yet"}}
                )
        
        # Apply visibility filter if requested
        conversation_history = room_state.conversation_history
        if agent_id and agent_type:
            conversation_history = filter_conversation(
                conversation_history,
                agent_id,
                agent_type
            )
        
        # Build current offers
        current_offers = {}
        for seller_id, offers in room_state.offers_by_seller.items():
            if offers:
                latest_offer = offers[-1]
                seller = next((s for s in room_state.sellers if s.seller_id == seller_id), None)
                if seller:
                    current_offers[seller_id] = OfferWithSeller(
                        price=latest_offer["price"],
                        quantity=latest_offer["quantity"],
                        timestamp=latest_offer.get("timestamp", datetime.utcnow().isoformat()),
                        seller_name=seller.name
                    )
        
        # Convert conversation history to Message schema
        messages = []
        for msg in conversation_history:
            message = Message(
                message_id=msg.get("message_id", ""),
                turn=msg.get("turn_number", msg.get("turn", 0)),
                timestamp=msg.get("timestamp", datetime.utcnow()).isoformat() if isinstance(msg.get("timestamp"), datetime) else msg.get("timestamp", datetime.utcnow().isoformat()),
                sender_type=msg.get("sender_type", "system"),
                sender_id=msg.get("sender_id"),
                sender_name=msg.get("sender_name", ""),
                message=msg.get("content", msg.get("message", "")),
                mentioned_agents=msg.get("mentioned_sellers", msg.get("mentioned_agents")),
                updated_offer=Offer(
                    price=msg["offer"]["price"],
                    quantity=msg["offer"]["quantity"],
                    timestamp=msg["offer"].get("timestamp", msg.get("timestamp", datetime.utcnow()).isoformat())
                ) if msg.get("offer") else None
            )
            messages.append(message)
        
        response = NegotiationStateResponse(
            room_id=room_id,
            item_name=room_state.buyer_constraints.item_name,
            status=room_state.status,
            current_round=room_state.current_round,
            max_rounds=room_state.max_rounds,
            conversation_history=messages,
            current_offers=current_offers,
            buyer_constraints=BuyerConstraints(
                min_price_per_unit=room_state.buyer_constraints.min_price_per_unit,
                max_price_per_unit=room_state.buyer_constraints.max_price_per_unit
            )
        )
        
        return response
        
    except RoomNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ROOM_NOT_FOUND", "message": f"Room not found: {room_id}"}}
        )
    except Exception as e:
        logger.error(f"Error fetching state for room {room_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to retrieve negotiation state"}}
        )


@router.post("/negotiation/{room_id}/message")
async def send_buyer_message(room_id: str, request: SendMessageRequest):
    """
    Send a manual buyer message.
    
    WHAT: Allow manual buyer message injection (future feature)
    WHY: Manual control for testing/debugging
    HOW: Add message to room state, trigger seller responses
    """
    # This is a placeholder for future implementation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"error": {"code": "NOT_IMPLEMENTED", "message": "Manual messages not yet implemented"}}
    )


@router.post("/negotiation/{room_id}/decide", response_model=DecisionResponse)
async def force_decision(room_id: str, request: ForceDecisionRequest = ForceDecisionRequest()):
    """
    Force a decision.
    
    WHAT: Manually trigger decision logic
    WHY: Allow early termination or override
    HOW: Analyze current offers, select best, finalize negotiation
    """
    try:
        logger.info(f"Forcing decision for room: {room_id}")
        
        # Get room state
        room_state = session_manager.get_room_state(room_id)
        if not room_state:
            raise RoomNotFoundException(room_id)
        
        if room_state.status not in ["active", "completed"]:
            raise NegotiationNotActiveException(room_id, room_state.status)
        
        # If force_select_seller is specified, use that
        if request.force_select_seller:
            selected_seller = next(
                (s for s in room_state.sellers if s.seller_id == request.force_select_seller),
                None
            )
            if not selected_seller:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": {"code": "INVALID_SELLER", "message": f"Seller not found: {request.force_select_seller}"}}
                )
            
            # Get latest offer from this seller
            offers = room_state.offers_by_seller.get(request.force_select_seller, [])
            if not offers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": {"code": "NO_OFFER", "message": f"No offer from seller: {request.force_select_seller}"}}
                )
            
            final_offer = offers[-1]
            room_state.selected_seller_id = request.force_select_seller
            room_state.final_offer = final_offer
            room_state.decision_reason = "Manually selected"
        else:
            # Analyze offers and select best
            analysis = analyze_offers(room_state)
            
            if not analysis["acceptable_offers"]:
                # No acceptable offers
                room_state.status = "aborted"
                room_state.decision_reason = "No acceptable offers"
            else:
                # Select best offer
                best_offer = select_best_offer(
                    analysis["acceptable_offers"],
                    room_state.buyer_constraints,
                    room_state.seller_response_times
                )
                
                room_state.selected_seller_id = best_offer["seller_id"]
                room_state.final_offer = {
                    "price": best_offer["price"],
                    "quantity": best_offer["quantity"]
                }
                room_state.decision_reason = best_offer.get("reason", "Best offer selected")
        
        # Mark as completed
        if room_state.selected_seller_id:
            room_state.status = "completed"
        
        # Update room state
        session_manager.update_room_state(room_id, room_state)
        
        # Calculate duration
        with get_db() as db:
            run = db.query(NegotiationRun).filter_by(room_id=room_id).first()
            duration = 0.0
            if run and run.started_at:
                duration = (datetime.utcnow() - run.started_at).total_seconds()
        
        # Build response
        selected_seller_info = None
        if room_state.selected_seller_id and room_state.final_offer:
            seller = next(
                (s for s in room_state.sellers if s.seller_id == room_state.selected_seller_id),
                None
            )
            selected_seller_info = SelectedSellerInfo(
                seller_id=room_state.selected_seller_id,
                seller_name=seller.name if seller else room_state.selected_seller_id,
                final_price=room_state.final_offer["price"],
                quantity=room_state.final_offer["quantity"]
            )
        
        response = DecisionResponse(
            room_id=room_id,
            decision_made=room_state.selected_seller_id is not None,
            selected_seller=selected_seller_info,
            decision_reason=room_state.decision_reason or "No decision made",
            total_rounds=room_state.current_round,
            negotiation_duration_seconds=duration
        )
        
        # Finalize the run
        if room_state.status == "completed":
            outcome_data = {
                "status": "completed",
                "selected_seller_id": room_state.selected_seller_id,
                "selected_seller_name": selected_seller_info.seller_name if selected_seller_info else None,
                "final_price_per_unit": room_state.final_offer["price"] if room_state.final_offer else None,
                "final_quantity": room_state.final_offer["quantity"] if room_state.final_offer else None,
                "final_total_cost": (
                    room_state.final_offer["price"] * room_state.final_offer["quantity"]
                    if room_state.final_offer else None
                ),
                "total_rounds": room_state.current_round,
                "total_messages": len(room_state.conversation_history),
                "total_offers": sum(len(offers) for offers in room_state.offers_by_seller.values()),
                "duration_seconds": duration,
                "decision_reason": room_state.decision_reason
            }
            session_manager.finalize_run(room_id, outcome_data)
        
        logger.info(f"Decision forced for room {room_id}: {room_state.decision_reason}")
        return response
        
    except (RoomNotFoundException, NegotiationNotActiveException):
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error forcing decision for room {room_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to force decision"}}
        )

