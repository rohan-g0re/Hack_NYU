"""
Simulation endpoints for Phase 4.

WHAT: Session initialization and management endpoints
WHY: Enable frontend to create, retrieve, delete sessions and get summaries
HOW: FastAPI endpoints wrapping SessionManager and summary services
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict

from ....core.session_manager import session_manager
from ....core.database import get_db
from ....services import summary_service
from ....models.api_schemas import (
    InitializeSessionRequest,
    InitializeSessionResponse,
    SessionSummaryResponse,
    PurchaseSummary,
    FailedItem,
    TotalCostSummary,
    NegotiationMetrics
)
from ....utils.exceptions import SessionNotFoundError, MaxSellersExceededError
from ....utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/simulation/initialize", response_model=InitializeSessionResponse, status_code=status.HTTP_200_OK)
async def initialize_session(request: InitializeSessionRequest):
    """
    Initialize a new negotiation session.
    
    WHAT: Create session with buyer, sellers, and negotiation rooms
    WHY: Start a new marketplace episode
    HOW: Call SessionManager.create_session with validated request
    
    Args:
        request: InitializeSessionRequest with buyer, sellers, LLM config
        
    Returns:
        InitializeSessionResponse with session_id and rooms
        
    Raises:
        MaxSellersExceededError: If too many sellers provided
    """
    # Validate max sellers (already done by Pydantic max_length=10)
    if len(request.sellers) > 10:
        raise MaxSellersExceededError(
            message=f"Maximum 10 sellers allowed, got {len(request.sellers)}",
            code="MAX_SELLERS_EXCEEDED"
        )
    
    logger.info(f"=== INITIALIZE SESSION REQUEST ===")
    logger.info(f"Sellers count: {len(request.sellers)}")
    logger.info(f"LLM Config: model={request.llm_config.model}, temp={request.llm_config.temperature}, max_tokens={request.llm_config.max_tokens}")
    logger.info(f"LLM Provider received: {request.llm_config.provider}")
    logger.info(f"Full llm_config: {request.llm_config.model_dump()}")
    
    try:
        response = session_manager.create_session(request)
        logger.info(f"Created session {response.session_id} with {response.total_rooms} rooms")
        return response
    except Exception as e:
        logger.error(f"Failed to initialize session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize session: {str(e)}"
        )


@router.get("/simulation/{session_id}")
async def get_session(session_id: str) -> Dict:
    """
    Get session details.
    
    WHAT: Retrieve session metadata and status
    WHY: Frontend needs session info
    HOW: Call SessionManager.get_session
    
    Args:
        session_id: Session ID
        
    Returns:
        Dict with session details
        
    Raises:
        SessionNotFoundError: If session doesn't exist
    """
    logger.info(f"Getting session {session_id}")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise SessionNotFoundError(
            message=f"Session {session_id} not found",
            code="SESSION_NOT_FOUND"
        )
    
    return session


@router.delete("/simulation/{session_id}")
async def delete_session(session_id: str) -> Dict:
    """
    Delete a session and all related data.
    
    WHAT: Remove session and cascade delete related records
    WHY: Cleanup after testing or completed negotiations
    HOW: Call SessionManager.delete_session
    
    Args:
        session_id: Session ID
        
    Returns:
        Dict with deletion status
        
    Raises:
        SessionNotFoundError: If session doesn't exist
    """
    logger.info(f"Deleting session {session_id}")
    
    result = session_manager.delete_session(session_id)
    if not result.get("deleted"):
        raise SessionNotFoundError(
            message=f"Session {session_id} not found",
            code="SESSION_NOT_FOUND"
        )
    
    return {
        "deleted": True,
        "session_id": session_id,
        "logs_saved": True  # Logs persist after deletion per spec
    }


@router.get("/simulation/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(session_id: str) -> SessionSummaryResponse:
    """
    Get comprehensive session summary.
    
    WHAT: Aggregate statistics for all negotiations in session
    WHY: Display results to user
    HOW: Query DB and compute summaries using summary_service
    
    Args:
        session_id: Session ID
        
    Returns:
        SessionSummaryResponse with metrics and summaries
        
    Raises:
        SessionNotFoundError: If session doesn't exist
    """
    logger.info(f"Computing summary for session {session_id}")
    
    with get_db() as db:
        # Check session exists
        from ....core.models import Session as SessionModel, Buyer
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise SessionNotFoundError(
                message=f"Session {session_id} not found",
                code="SESSION_NOT_FOUND"
            )
        
        buyer = db.query(Buyer).filter(Buyer.session_id == session_id).first()
        buyer_name = buyer.name if buyer else "Unknown"
        
        # Compute summary metrics
        summary_data = summary_service.compute_session_summary(db, session_id)
        
        # Get purchase summaries
        purchases = summary_service.get_purchase_summaries(db, session_id)
        
        # Get failed items
        failed = summary_service.get_failed_items(db, session_id)
        
        # Build response
        return SessionSummaryResponse(
            session_id=session_id,
            buyer_name=buyer_name,
            total_items_requested=summary_data.get("total_runs", 0),
            completed_purchases=summary_data.get("successful_deals", 0),
            failed_purchases=summary_data.get("failed_runs", 0),
            purchases=[
                PurchaseSummary(**p) for p in purchases
            ],
            failed_items=[
                FailedItem(**f) for f in failed
            ],
            total_cost_summary=TotalCostSummary(
                total_spent=summary_data.get("total_cost", 0.0),
                items_purchased=summary_data.get("items_purchased", 0),
                average_savings_per_item=summary_data.get("average_savings_per_item", 0.0)
            ),
            negotiation_metrics=NegotiationMetrics(
                average_rounds=summary_data.get("average_rounds", 0.0),
                average_duration_seconds=summary_data.get("average_duration_seconds", 0.0),
                total_messages_exchanged=summary_data.get("total_messages", 0)
            )
        )

