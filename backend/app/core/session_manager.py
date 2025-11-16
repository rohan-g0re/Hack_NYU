"""
Session manager for Phase 3 orchestration.

WHAT: Central lifecycle management for sessions and negotiations
WHY: Coordinate persistence, in-memory state, and JSON logging
HOW: CRUD operations, in-memory cache with TTL, background cleanup
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session as DBSession, joinedload
from sqlalchemy.exc import IntegrityError

from .database import get_db
from .models import (
    Session, Buyer, BuyerItem, Seller, SellerInventory,
    NegotiationRun, NegotiationParticipant, Message, Offer, NegotiationOutcome,
    SessionStatus, NegotiationStatus
)
from .config import settings
from ..models.agent import (
    BuyerConstraints, SellerProfile, InventoryItem,
    Seller as SellerAgent
)
from ..models.negotiation import NegotiationRoomState
from ..services.seller_selection import select_sellers_for_item
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manage session lifecycle and negotiation orchestration.
    
    WHAT: Central hub for session CRUD, state management, and persistence
    WHY: Coordinate between database, in-memory state, and file system
    HOW: Methods for create/read/update/delete with cache and JSON logging
    """
    
    def __init__(self):
        """Initialize session manager with in-memory cache."""
        self.active_rooms: Dict[str, NegotiationRoomState] = {}
        self._cache_lock = threading.Lock()
        self._cleanup_thread = None
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """
        Start background thread for cache cleanup.
        
        WHAT: Periodic cleanup of stale cache entries
        WHY: Prevent memory leaks from abandoned negotiations
        HOW: Threading.Timer with SESSION_CLEANUP_HOURS interval
        """
        def cleanup_task():
            self.cleanup_stale_rooms()
            # Schedule next cleanup
            self._cleanup_thread = threading.Timer(
                settings.SESSION_CLEANUP_HOURS * 3600,
                cleanup_task
            )
            self._cleanup_thread.daemon = True
            self._cleanup_thread.start()
        
        self._cleanup_thread = threading.Timer(
            settings.SESSION_CLEANUP_HOURS * 3600,
            cleanup_task
        )
        self._cleanup_thread.daemon = True
        self._cleanup_thread.start()
        logger.info(f"Started cache cleanup thread (interval: {settings.SESSION_CLEANUP_HOURS}h)")
    
    def cleanup_stale_rooms(self):
        """
        Remove stale rooms from cache.
        
        WHAT: Delete rooms older than timeout threshold
        WHY: Prevent memory bloat
        HOW: Check conversation history timestamps, remove if stale
        """
        with self._cache_lock:
            timeout_minutes = settings.NEGOTIATION_TIMEOUT_MINUTES
            cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            stale_rooms = []
            for room_id, room_state in self.active_rooms.items():
                # Check if room has any messages
                if room_state.conversation_history:
                    last_msg = room_state.conversation_history[-1]
                    last_time = last_msg.get("timestamp")
                    if last_time and last_time < cutoff_time:
                        stale_rooms.append(room_id)
                else:
                    # No messages yet, check status
                    if room_state.status in ["completed", "aborted"]:
                        stale_rooms.append(room_id)
            
            for room_id in stale_rooms:
                del self.active_rooms[room_id]
                logger.info(f"Cleaned up stale room: {room_id}")
            
            if stale_rooms:
                logger.info(f"Removed {len(stale_rooms)} stale rooms from cache")
    
    def cleanup_old_logs(self):
        """
        Delete log files older than retention period.
        
        WHAT: Remove old JSON logs based on LOG_RETENTION_DAYS
        WHY: Prevent disk space bloat
        HOW: Scan logs directory, check file age, delete if too old
        """
        logs_dir = Path(settings.LOGS_DIR)
        if not logs_dir.exists():
            return
        
        retention_days = settings.LOG_RETENTION_DAYS
        cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
        
        deleted_count = 0
        for session_dir in logs_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            for log_file in session_dir.glob("*.json"):
                # Check file modification time
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff_time:
                    try:
                        log_file.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete old log {log_file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old log files (retention: {retention_days} days)")
    
    def create_session(self, request_data: dict) -> dict:
        """
        Create a new session with buyer, sellers, and negotiation runs.
        
        WHAT: Initialize complete session in database
        WHY: Entry point for starting negotiation episode
        HOW: Create Session, Buyer, Sellers, run seller selection, create NegotiationRuns
        
        Args:
            request_data: Dict with buyer, sellers, and items configuration
            
        Returns:
            Dict with session_id and list of negotiation_rooms
        """
        with get_db() as db:
            try:
                # Extract data
                buyer_config = request_data["buyer"]
                sellers_config = request_data["sellers"]
                
                # Validate seller count
                if len(sellers_config) > settings.MAX_SELLERS_PER_SESSION:
                    raise ValueError(f"Maximum {settings.MAX_SELLERS_PER_SESSION} sellers allowed")
                
                # Create Session
                session_id = str(uuid4())
                session = Session(
                    session_id=session_id,
                    buyer_id=buyer_config["id"],
                    buyer_name=buyer_config["name"],
                    status=SessionStatus.PENDING
                )
                db.add(session)
                db.flush()
                
                # Create Buyer
                buyer = Buyer(
                    session_id=session_id,
                    buyer_id=buyer_config["id"],
                    name=buyer_config["name"]
                )
                db.add(buyer)
                db.flush()
                
                # Create BuyerItems
                for item_config in buyer_config["items"]:
                    buyer_item = BuyerItem(
                        buyer_db_id=buyer.id,
                        item_id=item_config["id"],
                        item_name=item_config["name"],
                        quantity_needed=item_config["quantity"],
                        min_price_per_unit=item_config["min_price"],
                        max_price_per_unit=item_config["max_price"]
                    )
                    db.add(buyer_item)
                
                # Create Sellers and Inventory
                seller_agents = []  # For seller selection
                for seller_config in sellers_config:
                    seller = Seller(
                        session_id=session_id,
                        seller_id=seller_config["id"],
                        name=seller_config["name"],
                        priority=seller_config["profile"]["priority"],
                        speaking_style=seller_config["profile"]["speaking_style"]
                    )
                    db.add(seller)
                    db.flush()
                    
                    # Create inventory items
                    inventory_items = []
                    for inv_config in seller_config["inventory"]:
                        inventory = SellerInventory(
                            seller_db_id=seller.id,
                            item_id=inv_config["item_id"],
                            item_name=inv_config["item_name"],
                            cost_price=inv_config["cost_price"],
                            selling_price=inv_config["selling_price"],
                            least_price=inv_config["least_price"],
                            quantity_available=inv_config["quantity_available"]
                        )
                        db.add(inventory)
                        
                        # Build in-memory inventory item for seller selection
                        inv_item = InventoryItem(
                            item_id=inv_config["item_id"],
                            item_name=inv_config["item_name"],
                            cost_price=inv_config["cost_price"],
                            selling_price=inv_config["selling_price"],
                            least_price=inv_config["least_price"],
                            quantity_available=inv_config["quantity_available"]
                        )
                        inventory_items.append(inv_item)
                    
                    # Build in-memory seller agent for selection
                    seller_agent = SellerAgent(
                        seller_id=seller_config["id"],
                        name=seller_config["name"],
                        profile=SellerProfile(
                            priority=seller_config["profile"]["priority"],
                            speaking_style=seller_config["profile"]["speaking_style"]
                        ),
                        inventory=inventory_items
                    )
                    seller_agents.append(seller_agent)
                
                db.flush()
                
                # Create NegotiationRuns for each buyer item
                negotiation_rooms = []
                for item_config in buyer_config["items"]:
                    # Build buyer constraints for selection
                    constraints = BuyerConstraints(
                        item_id=item_config["id"],
                        item_name=item_config["name"],
                        quantity_needed=item_config["quantity"],
                        min_price_per_unit=item_config["min_price"],
                        max_price_per_unit=item_config["max_price"]
                    )
                    
                    # Perform seller selection
                    selection_result = select_sellers_for_item(constraints, seller_agents)
                    
                    # Determine status based on selection
                    if not selection_result.selected_sellers:
                        run_status = NegotiationStatus.NO_SELLERS_AVAILABLE
                    else:
                        run_status = NegotiationStatus.PENDING
                    
                    # Create NegotiationRun
                    room_id = f"room_{session_id[:8]}_{item_config['id']}"
                    run = NegotiationRun(
                        run_id=str(uuid4()),
                        session_id=session_id,
                        room_id=room_id,
                        item_id=item_config["id"],
                        item_name=item_config["name"],
                        status=run_status,
                        current_round=0,
                        max_rounds=settings.MAX_NEGOTIATION_ROUNDS
                    )
                    db.add(run)
                    db.flush()
                    
                    # Create NegotiationParticipants
                    for selected_seller in selection_result.selected_sellers:
                        participant = NegotiationParticipant(
                            negotiation_run_id=run.id,
                            seller_id=selected_seller.seller_id,
                            seller_name=selected_seller.name,
                            participated=True,
                            skip_reason=None
                        )
                        db.add(participant)
                    
                    # Record skipped sellers
                    for seller_id, skip_reason in selection_result.skipped_sellers.items():
                        # Find seller name
                        seller_name = next(
                            (s.name for s in seller_agents if s.seller_id == seller_id),
                            seller_id
                        )
                        participant = NegotiationParticipant(
                            negotiation_run_id=run.id,
                            seller_id=seller_id,
                            seller_name=seller_name,
                            participated=False,
                            skip_reason=skip_reason
                        )
                        db.add(participant)
                    
                    negotiation_rooms.append({
                        "room_id": room_id,
                        "item_name": item_config["name"],
                        "status": run_status.value,
                        "participating_sellers": [s.name for s in selection_result.selected_sellers]
                    })
                
                db.commit()
                
                logger.info(
                    f"Created session {session_id} with {len(negotiation_rooms)} negotiation rooms"
                )
                
                return {
                    "session_id": session_id,
                    "negotiation_rooms": negotiation_rooms
                }
            
            except IntegrityError as e:
                db.rollback()
                logger.error(f"Database integrity error creating session: {e}")
                raise
            except Exception as e:
                db.rollback()
                logger.error(f"Error creating session: {e}")
                raise
    
    def get_session(self, session_id: str) -> dict:
        """
        Retrieve session details.
        
        WHAT: Fetch session with all related data
        WHY: Provide session overview
        HOW: Query with joinedload for relationships
        
        Args:
            session_id: Session UUID
            
        Returns:
            Dict with session details
        """
        with get_db() as db:
            session = db.query(Session).filter_by(session_id=session_id).first()
            
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            # Get negotiation runs
            runs = db.query(NegotiationRun).filter_by(session_id=session_id).all()
            
            return {
                "session_id": session.session_id,
                "buyer_id": session.buyer_id,
                "buyer_name": session.buyer_name,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "negotiation_runs": [
                    {
                        "room_id": run.room_id,
                        "item_name": run.item_name,
                        "status": run.status.value,
                        "current_round": run.current_round,
                        "max_rounds": run.max_rounds
                    }
                    for run in runs
                ]
            }
    
    def delete_session(self, session_id: str) -> dict:
        """
        Delete session and all related data.
        
        WHAT: Remove session from database (CASCADE handles related records)
        WHY: Cleanup after session completion
        HOW: Query session, delete (CASCADE), return confirmation
        
        Args:
            session_id: Session UUID
            
        Returns:
            Dict with deletion confirmation
        """
        with get_db() as db:
            session = db.query(Session).filter_by(session_id=session_id).first()
            
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            # Remove from active rooms cache
            with self._cache_lock:
                rooms_to_remove = [
                    room_id for room_id in self.active_rooms.keys()
                    if room_id.startswith(f"room_{session_id[:8]}")
                ]
                for room_id in rooms_to_remove:
                    del self.active_rooms[room_id]
            
            db.delete(session)
            db.commit()
            
            logger.info(f"Deleted session {session_id}")
            
            # Check if logs exist
            logs_path = Path(settings.LOGS_DIR) / session_id
            logs_saved = logs_path.exists() and any(logs_path.glob("*.json"))
            
            return {
                "session_id": session_id,
                "deleted": True,
                "logs_saved": logs_saved,
                "logs_path": str(logs_path) if logs_saved else None
            }
    
    def start_negotiation(self, room_id: str) -> NegotiationRoomState:
        """
        Start a negotiation by loading from DB and caching in memory.
        
        WHAT: Initialize negotiation run in active state
        WHY: Begin agent interactions
        HOW: Load NegotiationRun, create NegotiationRoomState, cache it, update DB status
        
        Args:
            room_id: Negotiation room identifier
            
        Returns:
            NegotiationRoomState ready for agent graph
        """
        with get_db() as db:
            run = db.query(NegotiationRun).filter_by(room_id=room_id).first()
            
            if not run:
                raise ValueError(f"Negotiation room not found: {room_id}")
            
            if run.status == NegotiationStatus.ACTIVE:
                # Check if already in cache
                with self._cache_lock:
                    if room_id in self.active_rooms:
                        logger.info(f"Returning cached room state for {room_id}")
                        return self.active_rooms[room_id]
            
            # Load session and participants
            session = db.query(Session).filter_by(session_id=run.session_id).first()
            buyer = db.query(Buyer).filter_by(session_id=run.session_id).first()
            buyer_item = db.query(BuyerItem).join(Buyer).filter(
                Buyer.session_id == run.session_id,
                BuyerItem.item_id == run.item_id
            ).first()
            
            participants = db.query(NegotiationParticipant).filter_by(
                negotiation_run_id=run.id,
                participated=True
            ).all()
            
            # Build seller agents list
            seller_agents = []
            for participant in participants:
                seller_db = db.query(Seller).filter_by(
                    session_id=run.session_id,
                    seller_id=participant.seller_id
                ).first()
                
                if seller_db:
                    # Load inventory
                    inventory_items = []
                    for inv in seller_db.inventory:
                        inv_item = InventoryItem(
                            item_id=inv.item_id,
                            item_name=inv.item_name,
                            cost_price=inv.cost_price,
                            selling_price=inv.selling_price,
                            least_price=inv.least_price,
                            quantity_available=inv.quantity_available
                        )
                        inventory_items.append(inv_item)
                    
                    seller_agent = SellerAgent(
                        seller_id=seller_db.seller_id,
                        name=seller_db.name,
                        profile=SellerProfile(
                            priority=seller_db.priority,
                            speaking_style=seller_db.speaking_style
                        ),
                        inventory=inventory_items
                    )
                    seller_agents.append(seller_agent)
            
            # Build buyer constraints
            constraints = BuyerConstraints(
                item_id=buyer_item.item_id,
                item_name=buyer_item.item_name,
                quantity_needed=buyer_item.quantity_needed,
                min_price_per_unit=buyer_item.min_price_per_unit,
                max_price_per_unit=buyer_item.max_price_per_unit
            )
            
            # Create NegotiationRoomState
            room_state = NegotiationRoomState(
                room_id=room_id,
                buyer_id=buyer.buyer_id,
                buyer_name=buyer.name,
                buyer_constraints=constraints,
                sellers=seller_agents,
                conversation_history=[],
                current_round=run.current_round,
                max_rounds=run.max_rounds,
                status="active"
            )
            
            # Update run status in DB
            run.status = NegotiationStatus.ACTIVE
            if not run.started_at:
                run.started_at = datetime.utcnow()
            db.commit()
            
            # Cache room state
            with self._cache_lock:
                self.active_rooms[room_id] = room_state
            
            logger.info(f"Started negotiation for room {room_id}")
            
            return room_state
    
    def get_room_state(self, room_id: str) -> Optional[NegotiationRoomState]:
        """
        Retrieve room state from cache.
        
        WHAT: Get in-memory negotiation state
        WHY: Agents need current state for decisions
        HOW: Thread-safe cache lookup
        
        Args:
            room_id: Room identifier
            
        Returns:
            NegotiationRoomState or None if not found
        """
        with self._cache_lock:
            return self.active_rooms.get(room_id)
    
    def update_room_state(self, room_id: str, room_state: NegotiationRoomState):
        """
        Update cached room state.
        
        WHAT: Store updated negotiation state
        WHY: Persist changes from agent actions
        HOW: Thread-safe cache update
        
        Args:
            room_id: Room identifier
            room_state: Updated state object
        """
        with self._cache_lock:
            self.active_rooms[room_id] = room_state
        logger.debug(f"Updated room state for {room_id}")
    
    def record_message(self, room_id: str, message_data: dict) -> dict:
        """
        Record a message in the database.
        
        WHAT: Persist message from negotiation
        WHY: Track conversation history
        HOW: Insert Message record, optionally call record_offer if present
        
        Args:
            room_id: Negotiation room identifier
            message_data: Dict with message details
            
        Returns:
            Dict with persisted message details
        """
        with get_db() as db:
            # Get negotiation run
            run = db.query(NegotiationRun).filter_by(room_id=room_id).first()
            
            if not run:
                raise ValueError(f"Negotiation room not found: {room_id}")
            
            # Create message
            message_id = str(uuid4())
            message = Message(
                message_id=message_id,
                negotiation_run_id=run.id,
                turn_number=message_data.get("turn_number", run.current_round),
                timestamp=message_data.get("timestamp", datetime.utcnow()),
                sender_id=message_data["sender_id"],
                sender_type=message_data["sender_type"],
                sender_name=message_data["sender_name"],
                content=message_data["content"],
                mentioned_sellers=message_data.get("mentioned_sellers", []),
                visibility=message_data.get("visibility", [])
            )
            db.add(message)
            db.flush()
            
            # If message contains offer, record it
            offer_data = message_data.get("offer")
            if offer_data:
                offer = Offer(
                    message_id=message_id,
                    negotiation_run_id=run.id,
                    seller_id=message_data["sender_id"],
                    price=offer_data["price"],
                    quantity=offer_data["quantity"],
                    timestamp=message_data.get("timestamp", datetime.utcnow())
                )
                db.add(offer)
            
            db.commit()
            
            logger.debug(
                f"Recorded message {message_id} in room {room_id} "
                f"(turn {message.turn_number}, sender: {message.sender_name})"
            )
            
            return {
                "message_id": message_id,
                "turn_number": message.turn_number,
                "has_offer": offer_data is not None
            }
    
    def record_offer(self, message_id: str, offer_data: dict) -> dict:
        """
        Record an offer linked to a message.
        
        WHAT: Persist offer details
        WHY: Track pricing negotiations
        HOW: Insert Offer record with FK to Message
        
        Args:
            message_id: Message UUID
            offer_data: Dict with price and quantity
            
        Returns:
            Dict with persisted offer details
        """
        with get_db() as db:
            # Get message
            message = db.query(Message).filter_by(message_id=message_id).first()
            
            if not message:
                raise ValueError(f"Message not found: {message_id}")
            
            # Create offer
            offer = Offer(
                message_id=message_id,
                negotiation_run_id=message.negotiation_run_id,
                seller_id=offer_data["seller_id"],
                price=offer_data["price"],
                quantity=offer_data["quantity"],
                timestamp=datetime.utcnow()
            )
            db.add(offer)
            db.commit()
            
            logger.debug(
                f"Recorded offer for message {message_id}: "
                f"${offer.price}/unit x {offer.quantity}"
            )
            
            return {
                "offer_id": offer.id,
                "price": offer.price,
                "quantity": offer.quantity
            }
    
    def finalize_run(self, room_id: str, outcome_data: dict) -> dict:
        """
        Finalize negotiation run with outcome and save JSON log.
        
        WHAT: Complete negotiation, persist outcome, save log file
        WHY: Mark negotiation complete and create audit trail
        HOW: Update NegotiationRun, create NegotiationOutcome, save JSON log, remove from cache
        
        Args:
            room_id: Negotiation room identifier
            outcome_data: Dict with outcome details
            
        Returns:
            Dict with outcome details and log path
        """
        with get_db() as db:
            # Get negotiation run with relationships
            run = db.query(NegotiationRun).options(
                joinedload(NegotiationRun.messages),
                joinedload(NegotiationRun.offers),
                joinedload(NegotiationRun.participants)
            ).filter_by(room_id=room_id).first()
            
            if not run:
                raise ValueError(f"Negotiation room not found: {room_id}")
            
            # Update run status
            run.status = NegotiationStatus(outcome_data.get("status", "completed"))
            run.completed_at = datetime.utcnow()
            run.current_round = outcome_data.get("total_rounds", run.current_round)
            run.selected_seller_id = outcome_data.get("selected_seller_id")
            run.decision_reason = outcome_data.get("decision_reason")
            
            # Check if outcome already exists (idempotent operation)
            existing_outcome = db.query(NegotiationOutcome).filter_by(
                negotiation_run_id=run.id
            ).first()
            
            if existing_outcome:
                # Update existing outcome instead of inserting
                logger.warning(
                    f"Outcome already exists for run {run.id} (room {room_id}), "
                    f"updating instead of inserting"
                )
                existing_outcome.status = outcome_data.get("status", "completed")
                existing_outcome.selected_seller_id = outcome_data.get("selected_seller_id")
                existing_outcome.selected_seller_name = outcome_data.get("selected_seller_name")
                existing_outcome.final_price_per_unit = outcome_data.get("final_price_per_unit")
                existing_outcome.final_quantity = outcome_data.get("final_quantity")
                existing_outcome.final_total_cost = outcome_data.get("final_total_cost")
                existing_outcome.total_rounds = outcome_data.get("total_rounds", 0)
                existing_outcome.total_messages = outcome_data.get("total_messages", 0)
                existing_outcome.total_offers = outcome_data.get("total_offers", 0)
                existing_outcome.duration_seconds = outcome_data.get("duration_seconds", 0.0)
                existing_outcome.decision_reason = outcome_data.get("decision_reason")
                outcome = existing_outcome
            else:
                # Create new outcome record
                outcome = NegotiationOutcome(
                    negotiation_run_id=run.id,
                    status=outcome_data.get("status", "completed"),
                    selected_seller_id=outcome_data.get("selected_seller_id"),
                    selected_seller_name=outcome_data.get("selected_seller_name"),
                    final_price_per_unit=outcome_data.get("final_price_per_unit"),
                    final_quantity=outcome_data.get("final_quantity"),
                    final_total_cost=outcome_data.get("final_total_cost"),
                    total_rounds=outcome_data.get("total_rounds", 0),
                    total_messages=outcome_data.get("total_messages", 0),
                    total_offers=outcome_data.get("total_offers", 0),
                    duration_seconds=outcome_data.get("duration_seconds", 0.0),
                    decision_reason=outcome_data.get("decision_reason")
                )
                db.add(outcome)
            
            db.commit()
            
            # Save JSON log if enabled
            log_path = None
            if settings.AUTO_SAVE_NEGOTIATIONS:
                log_path = self._save_json_log(room_id, run, outcome_data)
            
            # Remove from cache
            with self._cache_lock:
                if room_id in self.active_rooms:
                    del self.active_rooms[room_id]
            
            logger.info(
                f"Finalized negotiation {room_id}: "
                f"status={outcome.status}, rounds={outcome.total_rounds}"
            )
            
            return {
                "room_id": room_id,
                "status": outcome.status,
                "selected_seller": outcome.selected_seller_name,
                "final_cost": outcome.final_total_cost,
                "log_path": log_path
            }
    
    def _save_json_log(self, room_id: str, run: NegotiationRun, outcome_data: dict) -> str:
        """
        Save negotiation log as JSON file.
        
        WHAT: Create JSON file with complete negotiation history
        WHY: Audit trail and analysis
        HOW: Build JSON structure per spec, write to file system
        
        Args:
            room_id: Room identifier
            run: NegotiationRun model instance (with loaded relationships)
            outcome_data: Outcome data dict
            
        Returns:
            Path to saved log file
        """
        # Build log directory path
        logs_dir = Path(settings.LOGS_DIR) / run.session_id
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = logs_dir / f"{room_id}.json"
        
        # Get session and related data
        with get_db() as db:
            session = db.query(Session).filter_by(session_id=run.session_id).first()
            buyer = db.query(Buyer).filter_by(session_id=run.session_id).first()
            buyer_item = db.query(BuyerItem).join(Buyer).filter(
                Buyer.session_id == run.session_id,
                BuyerItem.item_id == run.item_id
            ).first()
            
            # Get participating sellers
            participants = db.query(NegotiationParticipant).filter_by(
                negotiation_run_id=run.id,
                participated=True
            ).all()
            
            sellers_info = []
            for participant in participants:
                seller = db.query(Seller).filter_by(
                    session_id=run.session_id,
                    seller_id=participant.seller_id
                ).first()
                
                if seller:
                    inventory = []
                    for inv in seller.inventory:
                        if inv.item_id == run.item_id:
                            inventory.append({
                                "item_id": inv.item_id,
                                "item_name": inv.item_name,
                                "cost_price": inv.cost_price,
                                "selling_price": inv.selling_price,
                                "least_price": inv.least_price,
                                "quantity_available": inv.quantity_available
                            })
                    
                    sellers_info.append({
                        "seller_id": seller.seller_id,
                        "name": seller.name,
                        "priority": seller.priority,
                        "speaking_style": seller.speaking_style,
                        "inventory": inventory
                    })
            
            # Build conversation history
            conversation = []
            for msg in run.messages:
                msg_dict = {
                    "message_id": msg.message_id,
                    "turn_number": msg.turn_number,
                    "timestamp": msg.timestamp.isoformat(),
                    "sender_id": msg.sender_id,
                    "sender_type": msg.sender_type,
                    "sender_name": msg.sender_name,
                    "content": msg.content,
                    "mentioned_sellers": msg.mentioned_sellers or []
                }
                
                # Add offer if present
                if msg.offer:
                    msg_dict["offer"] = {
                        "price": msg.offer.price,
                        "quantity": msg.offer.quantity
                    }
                
                conversation.append(msg_dict)
            
            # Build offers over time
            offers_over_time = []
            for offer in run.offers:
                offers_over_time.append({
                    "seller_id": offer.seller_id,
                    "price": offer.price,
                    "quantity": offer.quantity,
                    "timestamp": offer.timestamp.isoformat()
                })
            
            # Build log structure
            log_data = {
                "metadata": {
                    "session_id": run.session_id,
                    "room_id": room_id,
                    "item_id": run.item_id,
                    "item_name": run.item_name,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "buyer": {
                    "buyer_id": buyer.buyer_id,
                    "name": buyer.name,
                    "constraints": {
                        "item_id": buyer_item.item_id,
                        "item_name": buyer_item.item_name,
                        "quantity_needed": buyer_item.quantity_needed,
                        "min_price_per_unit": buyer_item.min_price_per_unit,
                        "max_price_per_unit": buyer_item.max_price_per_unit
                    }
                },
                "sellers": sellers_info,
                "conversation_history": conversation,
                "offers_over_time": offers_over_time,
                "decision": {
                    "selected_seller": outcome_data.get("selected_seller_name"),
                    "final_offer": {
                        "price": outcome_data.get("final_price_per_unit"),
                        "quantity": outcome_data.get("final_quantity"),
                        "total_cost": outcome_data.get("final_total_cost")
                    } if outcome_data.get("final_price_per_unit") else None,
                    "reason": outcome_data.get("decision_reason")
                },
                "stats": {
                    "duration_seconds": outcome_data.get("duration_seconds", 0.0),
                    "total_rounds": outcome_data.get("total_rounds", 0),
                    "total_messages": outcome_data.get("total_messages", 0),
                    "total_offers": outcome_data.get("total_offers", 0)
                }
            }
        
        # Write to file
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Saved negotiation log to {log_file}")
        
        return str(log_file)


# Singleton instance
session_manager = SessionManager()

