"""
Simulation endpoints for Phase 4.

WHAT: Session lifecycle management endpoints
WHY: Initialize, retrieve, delete sessions and get summaries
HOW: FastAPI router with session_manager integration
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime

from ....models.api_schemas import (
    InitializeSessionRequest,
    InitializeSessionResponse,
    SessionDetails,
    SessionSummaryResponse,
    DeleteSessionResponse,
    NegotiationRoom,
    SellerParticipant,
    BuyerConstraints,
    SessionNegotiationRoom,
    PurchaseSummary,
    FailedItem,
    TotalCostSummary,
    NegotiationMetrics
)
from ....core.session_manager import session_manager
from ....core.database import get_db
from ....core.models import Session, NegotiationRun, Seller, NegotiationStatus, Message, Offer
from ....core.config import settings
from ....utils.exceptions import (
    SessionNotFoundException,
    MaxSellersExceededException
)
from ....utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/simulation/initialize", response_model=InitializeSessionResponse, status_code=status.HTTP_201_CREATED)
async def initialize_session(request: InitializeSessionRequest):
    """
    Initialize a new negotiation session.
    
    WHAT: Create session with buyer, sellers, and negotiation rooms
    WHY: Entry point for starting negotiations
    HOW: Validate input, create session via session_manager, return room details
    """
    try:
        logger.info(f"Initializing session with buyer: {request.buyer.name}, sellers: {len(request.sellers)}")
        
        # Validate seller count
        if len(request.sellers) > settings.MAX_SELLERS_PER_SESSION:
            raise MaxSellersExceededException(len(request.sellers), settings.MAX_SELLERS_PER_SESSION)
        
        # Generate seller IDs if not provided
        for idx, seller in enumerate(request.sellers):
            if not seller.id:
                seller.id = f"seller_{idx + 1}"
        
        # Prepare request data for session_manager
        request_data = {
            "buyer": {
                "id": request.buyer.id,
                "name": request.buyer.name,
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "quantity": item.quantity,
                        "min_price": item.min_price,
                        "max_price": item.max_price
                    }
                    for item in request.buyer.items
                ]
            },
            "sellers": [
                {
                    "id": seller.id,
                    "name": seller.name,
                    "profile": {
                        "priority": seller.profile.priority,
                        "speaking_style": seller.profile.speaking_style
                    },
                    "inventory": [
                        {
                            "item_id": inv.item_id,
                            "item_name": inv.item_name,
                            "cost_price": inv.cost_price,
                            "selling_price": inv.selling_price,
                            "least_price": inv.least_price,
                            "quantity_available": inv.quantity_available
                        }
                        for inv in seller.inventory
                    ]
                }
                for seller in request.sellers
            ]
        }
        
        # Create session
        result = session_manager.create_session(request_data)
        
        # Build response
        negotiation_rooms = []
        skipped_items = []
        
        for room in result["negotiation_rooms"]:
            if room["status"] == "no_sellers_available":
                skipped_items.append(room["item_name"])
            
            # Map to response schema
            negotiation_rooms.append(
                NegotiationRoom(
                    room_id=room["room_id"],
                    item_id=room.get("item_id", room["room_id"].split("_")[-1]),  # Extract from room_id
                    item_name=room["item_name"],
                    quantity_needed=next(
                        (item.quantity for item in request.buyer.items if item.name == room["item_name"]),
                        0
                    ),
                    buyer_constraints=BuyerConstraints(
                        min_price_per_unit=next(
                            (item.min_price for item in request.buyer.items if item.name == room["item_name"]),
                            0.0
                        ),
                        max_price_per_unit=next(
                            (item.max_price for item in request.buyer.items if item.name == room["item_name"]),
                            0.0
                        )
                    ),
                    participating_sellers=[
                        SellerParticipant(
                            seller_id=next((s.id for s in request.sellers if s.name == seller_name), ""),
                            seller_name=seller_name
                        )
                        for seller_name in room["participating_sellers"]
                    ],
                    status=room["status"],
                    reason=None
                )
            )
        
        response = InitializeSessionResponse(
            session_id=result["session_id"],
            created_at=datetime.utcnow().isoformat(),
            buyer_id=request.buyer.id,
            seller_ids=[seller.id for seller in request.sellers],
            negotiation_rooms=negotiation_rooms,
            total_rooms=len(negotiation_rooms),
            skipped_items=skipped_items
        )
        
        logger.info(f"Session {result['session_id']} created successfully with {len(negotiation_rooms)} rooms")
        return response
        
    except MaxSellersExceededException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        )
    except Exception as e:
        logger.error(f"Error initializing session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to initialize session"}}
        )


@router.get("/simulation/{session_id}", response_model=SessionDetails)
async def get_session_details(session_id: str):
    """
    Get session details.
    
    WHAT: Retrieve session information with all negotiation rooms
    WHY: Frontend needs to display session overview
    HOW: Query session_manager, transform to response schema
    """
    try:
        logger.info(f"Fetching session details for: {session_id}")
        
        # Get session from manager
        session_data = session_manager.get_session(session_id)
        
        # Get additional details from database
        with get_db() as db:
            session = db.query(Session).filter_by(session_id=session_id).first()
            if not session:
                raise SessionNotFoundException(session_id)
            
            sellers = db.query(Seller).filter_by(session_id=session_id).all()
            
            # Build response
            response = SessionDetails(
                session_id=session_data["session_id"],
                status=session_data["status"],
                created_at=session_data["created_at"],
                buyer={
                    "id": session_data["buyer_id"],
                    "name": session_data["buyer_name"]
                },
                sellers=[
                    {"id": seller.seller_id, "name": seller.name}
                    for seller in sellers
                ],
                negotiation_rooms=[
                    SessionNegotiationRoom(
                        room_id=run["room_id"],
                        item_name=run["item_name"],
                        status=run["status"],
                        current_round=run["current_round"],
                        participating_sellers_count=len([
                            s for s in sellers 
                            # This is simplified - ideally we'd check participants table
                        ])
                    )
                    for run in session_data["negotiation_runs"]
                ],
                llm_provider=settings.LLM_PROVIDER
            )
            
            return response
            
    except SessionNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SESSION_NOT_FOUND", "message": f"Session not found: {session_id}"}}
        )
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to retrieve session"}}
        )


@router.delete("/simulation/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(session_id: str):
    """
    Delete a session.
    
    WHAT: Remove session and all related data
    WHY: Cleanup after completion
    HOW: Call session_manager.delete_session, return confirmation
    """
    try:
        logger.info(f"Deleting session: {session_id}")
        
        result = session_manager.delete_session(session_id)
        
        response = DeleteSessionResponse(
            session_id=result["session_id"],
            deleted=result["deleted"],
            logs_saved=result["logs_saved"],
            logs_path=result.get("logs_path")
        )
        
        logger.info(f"Session {session_id} deleted successfully")
        return response
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "SESSION_NOT_FOUND", "message": str(e)}}
            )
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to delete session"}}
        )


@router.get("/simulation/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(session_id: str):
    """
    Get session summary with metrics.
    
    WHAT: Calculate aggregated metrics for completed session
    WHY: Provide performance overview
    HOW: Query database, calculate metrics, return summary
    """
    try:
        logger.info(f"Generating summary for session: {session_id}")
        
        with get_db() as db:
            # Get session
            session = db.query(Session).filter_by(session_id=session_id).first()
            if not session:
                raise SessionNotFoundException(session_id)
            
            # Get all negotiation runs
            runs = db.query(NegotiationRun).filter_by(session_id=session_id).all()
            
            purchases = []
            failed_items = []
            total_spent = 0.0
            total_rounds = 0
            total_duration = 0.0
            total_messages = 0
            
            for run in runs:
                # Count messages for this run
                message_count = db.query(Message).filter_by(negotiation_run_id=run.id).count()
                total_messages += message_count
                
                if run.status == NegotiationStatus.COMPLETED and run.selected_seller_id:
                    # Get final offer
                    final_offer = db.query(Offer).filter_by(
                        negotiation_run_id=run.id,
                        seller_id=run.selected_seller_id
                    ).order_by(Offer.timestamp.desc()).first()
                    
                    if final_offer:
                        total_cost = final_offer.price * final_offer.quantity
                        total_spent += total_cost
                        
                        # Calculate duration
                        duration = 0.0
                        if run.started_at and run.completed_at:
                            duration = (run.completed_at - run.started_at).total_seconds()
                        total_duration += duration
                        total_rounds += run.current_round
                        
                        # Get seller name
                        seller = db.query(Seller).filter_by(
                            session_id=session_id,
                            seller_id=run.selected_seller_id
                        ).first()
                        
                        purchases.append(
                            PurchaseSummary(
                                item_name=run.item_name,
                                quantity=final_offer.quantity,
                                selected_seller=seller.name if seller else run.selected_seller_id,
                                final_price_per_unit=final_offer.price,
                                total_cost=total_cost,
                                negotiation_rounds=run.current_round,
                                duration_seconds=duration
                            )
                        )
                else:
                    # Failed negotiation
                    reason = "No sellers available" if run.status == NegotiationStatus.NO_SELLERS_AVAILABLE else "Negotiation failed"
                    if run.decision_reason:
                        reason = run.decision_reason
                    
                    failed_items.append(
                        FailedItem(
                            item_name=run.item_name,
                            reason=reason
                        )
                    )
            
            # Calculate averages
            completed_count = len(purchases)
            avg_rounds = total_rounds / completed_count if completed_count > 0 else 0.0
            avg_duration = total_duration / completed_count if completed_count > 0 else 0.0
            
            # Calculate savings (simplified - using max possible cost vs actual)
            # This would need buyer constraints for accurate calculation
            avg_savings = 0.0  # Placeholder
            
            response = SessionSummaryResponse(
                session_id=session_id,
                buyer_name=session.buyer_name,
                total_items_requested=len(runs),
                completed_purchases=completed_count,
                failed_purchases=len(failed_items),
                purchases=purchases,
                failed_items=failed_items,
                total_cost_summary=TotalCostSummary(
                    total_spent=total_spent,
                    items_purchased=completed_count,
                    average_savings_per_item=avg_savings
                ),
                negotiation_metrics=NegotiationMetrics(
                    average_rounds=avg_rounds,
                    average_duration_seconds=avg_duration,
                    total_messages_exchanged=total_messages
                )
            )
            
            logger.info(f"Generated summary for session {session_id}: {completed_count} completed, {len(failed_items)} failed")
            return response
            
    except SessionNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SESSION_NOT_FOUND", "message": f"Session not found: {session_id}"}}
        )
    except Exception as e:
        logger.error(f"Error generating summary for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to generate summary"}}
        )

