"""
SSE streaming endpoint for Phase 4.

WHAT: Server-Sent Events (SSE) endpoint for real-time negotiation updates
WHY: Stream negotiation events to frontend as they happen
HOW: sse-starlette EventSourceResponse with graph event streaming
"""

import asyncio
import json
from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from datetime import datetime
from typing import AsyncIterator

from ....core.session_manager import session_manager
from ....core.database import get_db
from ....core.models import NegotiationRun
from ....core.config import settings
from ....agents.graph_builder import NegotiationGraph
from ....llm.provider_factory import get_provider
from ....utils.exceptions import RoomNotFoundException
from ....utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def negotiation_event_generator(room_id: str) -> AsyncIterator[dict]:
    """
    Generate SSE events for negotiation.
    
    WHAT: Async generator yielding SSE events from negotiation graph
    WHY: Stream real-time updates to frontend
    HOW: Run graph, yield events, handle errors, send heartbeats
    
    Args:
        room_id: Negotiation room identifier
        
    Yields:
        Dict with event data for SSE
    """
    try:
        # Send connected event
        yield {
            "event": "connected",
            "data": json.dumps({
                "room_id": room_id,
                "timestamp": datetime.utcnow().isoformat()
            })
        }
        
        # Get room state
        room_state = session_manager.get_room_state(room_id)
        if not room_state:
            logger.error(f"Room state not found for {room_id}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "code": "ROOM_NOT_FOUND",
                    "message": f"Room not found: {room_id}",
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            return
        
        # Get provider
        provider = get_provider()
        
        # Create graph
        graph = NegotiationGraph(provider)
        
        # Track last heartbeat time
        last_heartbeat = asyncio.get_event_loop().time()
        heartbeat_interval = settings.SSE_HEARTBEAT_INTERVAL if hasattr(settings, 'SSE_HEARTBEAT_INTERVAL') else 15
        
        # Run graph and stream events
        async for event in graph.run(room_state):
            # Check if we need to send heartbeat
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat >= heartbeat_interval:
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "timestamp": datetime.utcnow().isoformat(),
                        "round": room_state.current_round
                    })
                }
                last_heartbeat = current_time
            
            # Process event based on type
            event_type = event.get("type")
            event_data = event.get("data", {})
            
            # Record message in database if applicable
            if event_type in ["buyer_message", "seller_response"]:
                try:
                    message_data = {
                        "turn_number": room_state.current_round,
                        "timestamp": event.get("timestamp", datetime.utcnow()),
                        "sender_id": event_data.get("sender_id", room_state.buyer_id if event_type == "buyer_message" else event_data.get("seller_id")),
                        "sender_type": "buyer" if event_type == "buyer_message" else "seller",
                        "sender_name": event_data.get("sender_name", room_state.buyer_name if event_type == "buyer_message" else event_data.get("seller_name", "")),
                        "content": event_data.get("message", ""),
                        "mentioned_sellers": event_data.get("mentioned_sellers", []),
                        "visibility": event_data.get("visibility", []),
                        "offer": event_data.get("offer")
                    }
                    session_manager.record_message(room_id, message_data)
                except Exception as e:
                    logger.error(f"Error recording message: {e}")
            
            # Update room state in cache
            session_manager.update_room_state(room_id, room_state)
            
            # Prepare event for SSE
            sse_event = {
                "event": event_type,
                "data": json.dumps({
                    **event_data,
                    "timestamp": event.get("timestamp", datetime.utcnow()).isoformat() if isinstance(event.get("timestamp"), datetime) else event.get("timestamp", datetime.utcnow().isoformat())
                })
            }
            
            yield sse_event
            
            # If negotiation complete, finalize and break
            if event_type == "negotiation_complete":
                logger.info(f"Negotiation completed for room {room_id}")
                
                # Finalize the run
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
                
                try:
                    session_manager.finalize_run(room_id, outcome_data)
                except Exception as e:
                    logger.error(f"Error finalizing run: {e}", exc_info=True)
                    # Don't break the stream, just log the error
                    # The finalize_run method is now idempotent, so duplicate calls are safe
                
                break
        
        # Send final heartbeat
        yield {
            "event": "heartbeat",
            "data": json.dumps({
                "message": "Stream closing",
                "timestamp": datetime.utcnow().isoformat()
            })
        }
        
    except asyncio.CancelledError:
        logger.info(f"Stream cancelled for room {room_id}")
        raise
    except Exception as e:
        logger.error(f"Error in event generator for room {room_id}: {e}", exc_info=True)
        yield {
            "event": "error",
            "data": json.dumps({
                "code": "STREAM_ERROR",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        }


@router.get("/negotiation/{room_id}/stream")
async def stream_negotiation(room_id: str):
    """
    Stream negotiation events via SSE.
    
    WHAT: SSE endpoint for real-time negotiation updates
    WHY: Frontend needs live updates during negotiation
    HOW: EventSourceResponse with negotiation_event_generator
    
    Args:
        room_id: Negotiation room identifier
        
    Returns:
        EventSourceResponse streaming negotiation events
    """
    try:
        logger.info(f"Client connecting to stream for room: {room_id}")
        
        # Verify room exists
        with get_db() as db:
            run = db.query(NegotiationRun).filter_by(room_id=room_id).first()
            if not run:
                raise RoomNotFoundException(room_id)
        
        # Verify room is in cache (should be started)
        room_state = session_manager.get_room_state(room_id)
        if not room_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "NEGOTIATION_NOT_STARTED",
                        "message": "Negotiation has not been started yet. Call /start first."
                    }
                }
            )
        
        # Return SSE stream
        return EventSourceResponse(
            negotiation_event_generator(room_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except RoomNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ROOM_NOT_FOUND", "message": f"Room not found: {room_id}"}}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up stream for room {room_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to setup stream"}}
        )

