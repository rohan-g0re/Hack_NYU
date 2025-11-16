"""
Logs retrieval endpoint for Phase 4.

WHAT: Serve persisted JSON logs for completed negotiations
WHY: Enable audit trail and replay of negotiations
HOW: Read JSON files from logs directory
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import json

from ....core.config import settings
from ....utils.exceptions import SessionNotFoundError, RoomNotFoundError
from ....utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/logs/{session_id}/{room_id}")
async def get_negotiation_log(session_id: str, room_id: str):
    """
    Retrieve JSON log for a completed negotiation.
    
    WHAT: Serve persisted JSON log file
    WHY: Allow frontend to display negotiation history
    HOW: Read file from logs directory
    
    Args:
        session_id: Session ID
        room_id: Negotiation run ID (room_id)
        
    Returns:
        JSON log file content
        
    Raises:
        RoomNotFoundError: If log file doesn't exist
    """
    logger.info(f"Retrieving log for session {session_id}, room {room_id}")
    
    # Construct log file path
    log_path = Path(settings.LOGS_DIR) / session_id / room_id / f"{room_id}.json"
    
    if not log_path.exists():
        # Try alternate path (without extra room_id subdir)
        log_path = Path(settings.LOGS_DIR) / session_id / f"{room_id}.json"
        
        if not log_path.exists():
            raise RoomNotFoundError(
                message=f"Log file not found for session {session_id}, room {room_id}",
                code="LOG_NOT_FOUND"
            )
    
    logger.info(f"Serving log file: {log_path}")
    
    try:
        # Read and return JSON
        with open(log_path, 'r') as f:
            log_data = json.load(f)
        
        return JSONResponse(content=log_data)
    except Exception as e:
        logger.error(f"Error reading log file {log_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading log file: {str(e)}"
        )

