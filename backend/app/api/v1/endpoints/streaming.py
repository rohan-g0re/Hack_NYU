"""
SSE streaming endpoint for Phase 4.

WHAT: Server-Sent Events stream for real-time negotiation updates
WHY: Enable frontend to receive live negotiation events
HOW: EventSourceResponse wrapping NegotiationGraph event stream
"""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from typing import AsyncIterator
import asyncio
import json
from datetime import datetime

from ....core.session_manager import active_rooms
from ....core.config import settings
from ....core.database import get_db
from ....core.models import NegotiationRun
from ....agents.graph_builder import NegotiationGraph
from ....llm.provider_factory import get_provider
from ....utils.exceptions import RoomNotFoundError
from ....utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def negotiation_event_generator(room_id: str) -> AsyncIterator[dict]:
    """
    Generate SSE events for negotiation.
    
    WHAT: Stream negotiation events with heartbeats
    WHY: Real-time updates to frontend
    HOW: Yield events from NegotiationGraph with periodic heartbeats
    
    Args:
        room_id: Negotiation run ID
        
    Yields:
        SSE event dicts
    """
    logger.info(f"Starting SSE stream for room {room_id}")
    
    # Check if room exists and is active
    if room_id not in active_rooms:
        logger.error(f"Room {room_id} not found in active_rooms")
        yield {
            "event": "error",
            "data": json.dumps({
                "type": "error",
                "error": "ROOM_NOT_FOUND",
                "message": f"Room {room_id} not found or not active",
                "timestamp": datetime.now().isoformat()
            })
        }
        return
    
    # Send connected event immediately
    yield {
        "event": "connected",
        "data": json.dumps({
            "type": "connected",
            "room_id": room_id,
            "timestamp": datetime.now().isoformat()
        })
    }
    
    try:
        # Get room state
        room_state, _ = active_rooms[room_id]
        
        # Get LLM provider from room state (session-specific)
        provider = get_provider(room_state.llm_provider)
        
        # Create negotiation graph
        graph = NegotiationGraph(provider)
        
        # Create heartbeat task
        heartbeat_task = None
        stop_heartbeat = asyncio.Event()
        
        async def send_heartbeats():
            """Send periodic heartbeat events."""
            while not stop_heartbeat.is_set():
                try:
                    await asyncio.sleep(settings.SSE_HEARTBEAT_INTERVAL)
                    if not stop_heartbeat.is_set():
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({
                                "type": "heartbeat",
                                "timestamp": datetime.now().isoformat()
                            })
                        }
                except asyncio.CancelledError:
                    break
        
        # Stream negotiation events
        async for event in graph.run(room_state):
            # Serialize event data
            event_data = event.get("data", {})
            
            # Add type field to data payload for frontend categorization
            event_data["type"] = event["type"]
            
            # Ensure timestamp exists for all events
            if "timestamp" not in event_data:
                event_data["timestamp"] = datetime.now().isoformat()
            elif isinstance(event_data["timestamp"], datetime):
                # Convert datetime objects to ISO strings
                event_data["timestamp"] = event_data["timestamp"].isoformat()
            
            yield {
                "event": event["type"],
                "data": json.dumps(event_data)
            }
            
            # Check if negotiation is complete
            if event["type"] == "negotiation_complete":
                logger.info(f"Negotiation {room_id} completed")
                break
        
        # Send final completion event if not already sent
        yield {
            "event": "negotiation_complete",
            "data": json.dumps({
                "type": "negotiation_complete",
                "room_id": room_id,
                "timestamp": datetime.now().isoformat()
            })
        }

        # Persist completion to DB (status, rounds, ended_at)
        try:
            with get_db() as db:
                run = db.query(NegotiationRun).filter(NegotiationRun.id == room_id).first()
                if run:
                    run.status = "completed"
                    run.current_round = getattr(room_state, "current_round", run.current_round)
                    run.ended_at = datetime.now()
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to persist completion for room {room_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error in SSE stream for room {room_id}: {e}")
        yield {
            "event": "error",
            "data": json.dumps({
                "type": "error",
                "error": "STREAM_ERROR",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })
        }
    finally:
        logger.info(f"SSE stream ended for room {room_id}")
        # Cleanup in-memory state to allow clean restarts
        try:
            if room_id in active_rooms:
                del active_rooms[room_id]
                logger.info(f"Removed room {room_id} from active_rooms")
        except Exception as e:
            logger.error(f"Failed to cleanup active room {room_id}: {e}")


@router.get("/negotiation/{room_id}/stream")
async def stream_negotiation(room_id: str):
    """
    Stream negotiation events via SSE.
    
    WHAT: Server-Sent Events endpoint for real-time updates
    WHY: Frontend needs live negotiation progress
    HOW: EventSourceResponse with event generator
    
    Args:
        room_id: Negotiation run ID
        
    Returns:
        EventSourceResponse with negotiation events
        
    Raises:
        RoomNotFoundError: If room not found or not active
    """
    logger.info(f"SSE stream requested for room {room_id}")
    
    # Verify room exists
    if room_id not in active_rooms:
        raise RoomNotFoundError(
            message=f"Room {room_id} not found or not active",
            code="ROOM_NOT_FOUND"
        )
    
    return EventSourceResponse(
        negotiation_event_generator(room_id),
        media_type="text/event-stream"
    )

