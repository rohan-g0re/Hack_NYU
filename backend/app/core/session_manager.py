"""
Session manager for Phase 3.

WHAT: Central lifecycle control for sessions and negotiations
WHY: Orchestrate session creation, negotiation runs, message/offer recording
HOW: Database operations + in-memory cache with TTL
"""

import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    Session as SessionModel, Buyer, BuyerItem, Seller, SellerInventory,
    NegotiationRun, NegotiationParticipant, Message, Offer, NegotiationOutcome
)
from .config import settings
from ..models.api_schemas import (
    InitializeSessionRequest, InitializeSessionResponse, NegotiationRoomInfo
)
from ..models.negotiation import NegotiationRoomState
from ..models.agent import BuyerConstraints, Seller as SellerModel, InventoryItem, SellerProfile
from ..services.seller_selection import select_sellers_for_item
from ..utils.logger import get_logger

logger = get_logger(__name__)

# In-memory cache for active rooms (room_id -> (room_state, created_at))
active_rooms: Dict[str, tuple] = {}


class SessionManager:
    """Session manager for orchestrating negotiations."""
    
    def __init__(self):
        """Initialize session manager."""
        self.cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background task to clean up expired rooms."""
        async def cleanup_expired_rooms():
            while True:
                try:
                    await asyncio.sleep(settings.SESSION_CLEANUP_HOURS * 3600)  # Convert hours to seconds
                    self._cleanup_expired_rooms()
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        # Note: In a real async context, this would be started properly
        # For now, we'll clean up synchronously when needed
        pass
    
    def _cleanup_expired_rooms(self):
        """Remove expired rooms from cache."""
        now = datetime.now()
        expired = []
        for room_id, (room_state, created_at) in active_rooms.items():
            age = now - created_at
            if age > timedelta(hours=settings.SESSION_CLEANUP_HOURS):
                expired.append(room_id)
        
        for room_id in expired:
            del active_rooms[room_id]
            logger.info(f"Cleaned up expired room: {room_id}")
    
    def create_session(
        self,
        request: InitializeSessionRequest
    ) -> InitializeSessionResponse:
        """
        Create a new session with buyer, sellers, and negotiation rooms.
        
        WHAT: Persist session configuration and create negotiation rooms
        WHY: Initialize marketplace episode
        HOW: Insert into DB, run seller selection, create rooms
        
        Args:
            request: InitializeSessionRequest with buyer, sellers, LLM config
        
        Returns:
            InitializeSessionResponse with session_id and rooms
        """
        with get_db() as db:
            # Create session
            session_id = str(uuid.uuid4())
            # Use provider from request if specified, otherwise use global settings
            llm_provider = request.llm_config.provider or settings.LLM_PROVIDER
            session = SessionModel(
                id=session_id,
                status='draft',
                llm_model=request.llm_config.model,
                llm_temperature=request.llm_config.temperature,
                llm_max_tokens=request.llm_config.max_tokens,
                llm_provider=llm_provider
            )
            db.add(session)
            db.flush()
            
            # Create buyer
            buyer_id = str(uuid.uuid4())
            buyer = Buyer(
                id=buyer_id,
                session_id=session_id,
                name=request.buyer.name
            )
            db.add(buyer)
            db.flush()
            
            # Create buyer items
            buyer_items = []
            for item in request.buyer.shopping_list:
                buyer_item = BuyerItem(
                    id=str(uuid.uuid4()),
                    buyer_id=buyer_id,
                    item_id=item.item_id,
                    item_name=item.item_name,
                    quantity_needed=item.quantity_needed,
                    min_price_per_unit=item.min_price_per_unit,
                    max_price_per_unit=item.max_price_per_unit
                )
                db.add(buyer_item)
                buyer_items.append(buyer_item)
            
            db.flush()
            
            # Create sellers
            seller_ids = []
            sellers_orm = []
            for seller_config in request.sellers:
                seller_id = str(uuid.uuid4())
                seller = Seller(
                    id=seller_id,
                    session_id=session_id,
                    name=seller_config.name,
                    priority=seller_config.profile.priority,
                    speaking_style=seller_config.profile.speaking_style
                )
                db.add(seller)
                db.flush()
                
                # Create seller inventory
                inventory_list = []
                for inv_item in seller_config.inventory:
                    seller_inv = SellerInventory(
                        id=str(uuid.uuid4()),
                        seller_id=seller_id,
                        item_id=inv_item.item_id,
                        item_name=inv_item.item_name,
                        cost_price=inv_item.cost_price,
                        selling_price=inv_item.selling_price,
                        least_price=inv_item.least_price,
                        quantity_available=inv_item.quantity_available
                    )
                    db.add(seller_inv)
                    inventory_list.append(seller_inv)
                
                seller_ids.append(seller_id)
                sellers_orm.append((seller, inventory_list))
            
            db.commit()
            
            # Create negotiation rooms using seller selection
            negotiation_rooms = []
            skipped_items = []
            
            for buyer_item in buyer_items:
                # Get all sellers and their inventories for this session
                all_sellers = [s for s, _ in sellers_orm]
                all_inventories = [inv for _, inv in sellers_orm]
                
                # Select participating sellers
                participating_sellers, skipped_reasons = select_sellers_for_item(
                    buyer_item,
                    all_sellers,
                    all_inventories
                )
                
                if not participating_sellers:
                    skipped_items.append(buyer_item.item_name)
                    # Create run with no_sellers_available status
                    run = NegotiationRun(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        buyer_item_id=buyer_item.id,
                        status='no_sellers_available'
                    )
                    db.add(run)
                    continue
                
                # Create negotiation run
                room_id = str(uuid.uuid4())
                run = NegotiationRun(
                    id=room_id,
                    session_id=session_id,
                    buyer_item_id=buyer_item.id,
                    status='pending'
                )
                db.add(run)
                db.flush()
                
                # Create participants
                for seller in participating_sellers:
                    participant = NegotiationParticipant(
                        id=str(uuid.uuid4()),
                        negotiation_run_id=room_id,
                        seller_id=seller.id
                    )
                    db.add(participant)
                
                db.flush()
                
                # Build room info
                from ..models.api_schemas import SellerParticipant
                
                participants = [
                    SellerParticipant(
                        seller_id=s.id,
                        seller_name=s.name,
                        initial_price=None,
                        current_offer=None
                    )
                    for s in participating_sellers
                ]
                
                from ..models.api_schemas import BuyerConstraints as BuyerConstraintsSchema
                
                room_info = NegotiationRoomInfo(
                    room_id=room_id,
                    item_id=buyer_item.item_id,
                    item_name=buyer_item.item_name,
                    quantity_needed=buyer_item.quantity_needed,
                    buyer_constraints=BuyerConstraintsSchema(
                        min_price_per_unit=buyer_item.min_price_per_unit,
                        max_price_per_unit=buyer_item.max_price_per_unit
                    ),
                    participating_sellers=participants,
                    status='pending',
                    reason=None
                )
                negotiation_rooms.append(room_info)
            
            db.commit()
            
            logger.info(f"Created session {session_id} with {len(negotiation_rooms)} rooms")
            
            return InitializeSessionResponse(
                session_id=session_id,
                created_at=session.created_at,
                buyer_id=buyer_id,
                seller_ids=seller_ids,
                negotiation_rooms=negotiation_rooms,
                total_rooms=len(negotiation_rooms),
                skipped_items=skipped_items
            )
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session details.
        
        Args:
            session_id: Session ID
        
        Returns:
            Dict with session details or None if not found
        """
        with get_db() as db:
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                return None
            
            buyer = db.query(Buyer).filter(Buyer.session_id == session_id).first()
            runs = db.query(NegotiationRun).filter(NegotiationRun.session_id == session_id).all()
            
            return {
                "session_id": session_id,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "buyer_name": buyer.name if buyer else None,
                "total_runs": len(runs),
                "llm_model": session.llm_model
            }
    
    def delete_session(self, session_id: str) -> Dict:
        """
        Delete a session and all related data.
        
        Args:
            session_id: Session ID
        
        Returns:
            Dict with deletion status
        """
        with get_db() as db:
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                return {"deleted": False, "error": "Session not found"}
            
            # Get all run IDs for this session to clear cache
            run_ids = [run.id for run in db.query(NegotiationRun).filter(NegotiationRun.session_id == session_id).all()]
            
            # Cascade delete will handle related records
            db.delete(session)
            db.commit()
            
            # Clear cache entries for all runs in this session
            for run_id in run_ids:
                if run_id in active_rooms:
                    del active_rooms[run_id]
            
            logger.info(f"Deleted session {session_id}")
            return {"deleted": True, "session_id": session_id}
    
    def start_negotiation(self, room_id: str) -> Dict:
        """
        Start a negotiation run.
        
        WHAT: Activate a negotiation run and create NegotiationRoomState
        WHY: Begin negotiation process
        HOW: Update run status, create in-memory room state
        
        Args:
            room_id: Negotiation run ID (room_id)
        
        Returns:
            Dict with run details
        """
        with get_db() as db:
            run = db.query(NegotiationRun).filter(NegotiationRun.id == room_id).first()
            if not run:
                return {"error": "Run not found"}
            
            if run.status != 'pending':
                # Allow restarting completed/aborted negotiations
                if run.status in ['completed', 'aborted']:
                    logger.info(f"Restarting negotiation for room {room_id}")
                    run.current_round = 0  # Reset round counter
                    run.status = 'pending'
                else:
                    return {"error": f"Run already {run.status}"}
            
            # Update status
            run.status = 'active'
            run.started_at = datetime.now()
            run.current_round = 0  # Always reset to 0 when starting
            db.commit()
            
            # Create NegotiationRoomState for in-memory cache
            # This would be populated from DB models
            # For now, we'll create a placeholder
            room_state = self._create_room_state_from_run(db, run)
            if room_state:
                active_rooms[room_id] = (room_state, datetime.now())
                logger.info(f"Room {room_id} added to active_rooms (sellers: {len(room_state.sellers)})")
            else:
                logger.error(f"Failed to create room state for {room_id} - room_state is None!")
                return {"error": "Failed to initialize room state"}
            
            return {
                "run_id": room_id,
                "status": "active",
                "started_at": run.started_at.isoformat()
            }
    
    def _create_room_state_from_run(self, db: Session, run: NegotiationRun) -> Optional[NegotiationRoomState]:
        """Create NegotiationRoomState from DB run."""
        logger.info(f"Creating room state from run {run.id}")
        
        # Get session to retrieve LLM provider
        session = db.query(SessionModel).filter(SessionModel.id == run.session_id).first()
        if not session:
            logger.error(f"Session {run.session_id} not found for run {run.id}")
            return None
        
        buyer_item = db.query(BuyerItem).filter(BuyerItem.id == run.buyer_item_id).first()
        if not buyer_item:
            logger.error(f"Buyer item {run.buyer_item_id} not found for run {run.id}")
            return None
        
        buyer = db.query(Buyer).filter(Buyer.id == buyer_item.buyer_id).first()
        if not buyer:
            logger.error(f"Buyer {buyer_item.buyer_id} not found")
            return None
        
        # Get participants
        participants = db.query(NegotiationParticipant).filter(
            NegotiationParticipant.negotiation_run_id == run.id
        ).all()
        
        logger.info(f"Found {len(participants)} participants for run {run.id}")
        
        seller_ids = [p.seller_id for p in participants]
        sellers_orm = db.query(Seller).filter(Seller.id.in_(seller_ids)).all()
        
        logger.info(f"Loaded {len(sellers_orm)} sellers from DB")
        
        # Convert to Seller models
        sellers = []
        for seller_orm in sellers_orm:
            inventory_orm = db.query(SellerInventory).filter(
                SellerInventory.seller_id == seller_orm.id
            ).all()
            
            inventory = [
                InventoryItem(
                    item_id=inv.item_id,
                    item_name=inv.item_name,
                    cost_price=inv.cost_price,
                    selling_price=inv.selling_price,
                    least_price=inv.least_price,
                    quantity_available=inv.quantity_available
                )
                for inv in inventory_orm
            ]
            
            sellers.append(SellerModel(
                seller_id=seller_orm.id,
                name=seller_orm.name,
                profile=SellerProfile(
                    priority=seller_orm.priority,
                    speaking_style=seller_orm.speaking_style
                ),
                inventory=inventory
            ))
        
        buyer_constraints = BuyerConstraints(
            item_id=buyer_item.item_id,
            item_name=buyer_item.item_name,
            quantity_needed=buyer_item.quantity_needed,
            min_price_per_unit=buyer_item.min_price_per_unit,
            max_price_per_unit=buyer_item.max_price_per_unit
        )
        
        room_state = NegotiationRoomState(
            room_id=run.id,
            buyer_id=buyer.id,
            buyer_name=buyer.name,
            buyer_constraints=buyer_constraints,
            sellers=sellers,
            conversation_history=[],
            current_round=run.current_round,  # Use DB value (should be 0 after reset)
            max_rounds=run.max_rounds,
            status='active',
            llm_provider=session.llm_provider,  # Use provider from session
            llm_model=session.llm_model  # Use model from session
        )
        
        logger.info(f"Successfully created room state for {run.id}: {len(sellers)} sellers, round {run.current_round}/{run.max_rounds}")
        return room_state
    
    def record_message(
        self,
        run_id: str,
        turn_number: int,
        sender_type: str,
        sender_id: str,
        sender_name: str,
        message_text: str,
        mentioned_agents: Optional[List[str]] = None
    ) -> Message:
        """
        Record a message in the database.
        
        Args:
            run_id: Negotiation run ID
            turn_number: Turn number
            sender_type: 'buyer' or 'seller'
            sender_id: Sender ID
            sender_name: Sender name
            message_text: Message content
            mentioned_agents: List of mentioned agent IDs
        
        Returns:
            Message ORM object
        """
        with get_db() as db:
            message = Message(
                id=str(uuid.uuid4()),
                negotiation_run_id=run_id,
                turn_number=turn_number,
                sender_type=sender_type,
                sender_id=sender_id,
                sender_name=sender_name,
                message_text=message_text,
                mentioned_agents=json.dumps(mentioned_agents) if mentioned_agents else None
            )
            db.add(message)
            db.commit()
            return message
    
    def record_offer(
        self,
        message_id: str,
        seller_id: str,
        price_per_unit: float,
        quantity: int,
        conditions: Optional[str] = None
    ) -> Offer:
        """
        Record an offer linked to a message.
        
        Args:
            message_id: Message ID
            seller_id: Seller ID
            price_per_unit: Price per unit
            quantity: Quantity
            conditions: Optional conditions
        
        Returns:
            Offer ORM object
        """
        with get_db() as db:
            offer = Offer(
                id=str(uuid.uuid4()),
                message_id=message_id,
                seller_id=seller_id,
                price_per_unit=price_per_unit,
                quantity=quantity,
                conditions=conditions
            )
            db.add(offer)
            db.commit()
            return offer
    
    def finalize_run(
        self,
        run_id: str,
        decision_type: str,
        selected_seller_id: Optional[str] = None,
        final_price_per_unit: Optional[float] = None,
        quantity: Optional[int] = None,
        decision_reason: Optional[str] = None,
        emit_event: bool = False
    ) -> NegotiationOutcome:
        """
        Finalize a negotiation run with outcome.
        
        Args:
            run_id: Negotiation run ID
            decision_type: 'deal' or 'no_deal'
            selected_seller_id: Selected seller ID (if deal)
            final_price_per_unit: Final price (if deal)
            quantity: Quantity (if deal)
            decision_reason: Decision reason
            emit_event: If True, emit decision event to active room state (for forced decisions)
        
        Returns:
            NegotiationOutcome ORM object
        """
        with get_db() as db:
            run = db.query(NegotiationRun).filter(NegotiationRun.id == run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found")
            
            # Get seller name if dealing
            seller_name = None
            if decision_type == "deal" and selected_seller_id:
                seller = db.query(Seller).filter(Seller.id == selected_seller_id).first()
                if seller:
                    seller_name = seller.name
            
            # Update run status
            run.status = 'completed'
            run.ended_at = datetime.now()
            
            # Compute total cost
            total_cost = None
            if final_price_per_unit and quantity:
                total_cost = final_price_per_unit * quantity
            
            # Create outcome
            outcome = NegotiationOutcome(
                id=str(uuid.uuid4()),
                negotiation_run_id=run_id,
                decision_type=decision_type,
                selected_seller_id=selected_seller_id,
                final_price_per_unit=final_price_per_unit,
                quantity=quantity,
                total_cost=total_cost,
                decision_reason=decision_reason
            )
            db.add(outcome)
            
            # If room is active and emit_event is True, record decision message
            if emit_event and run_id in active_rooms:
                room_state, _ = active_rooms[run_id]
                
                # Record system message about forced decision
                if decision_type == "deal":
                    decision_message = f"🎯 Manual Decision: Accepted offer from {seller_name or selected_seller_id} at ${final_price_per_unit}/unit for {quantity} units (Total: ${total_cost}). Reason: {decision_reason or 'Manual override'}"
                else:
                    decision_message = f"❌ Manual Decision: No deal. Reason: {decision_reason or 'Manual rejection'}"
                
                # Create system message
                system_message = Message(
                    id=str(uuid.uuid4()),
                    negotiation_run_id=run_id,
                    turn_number=run.current_round + 1,
                    sender_type="buyer",
                    sender_id="system",
                    sender_name="System",
                    message_text=decision_message,
                    mentioned_agents=None
                )
                db.add(system_message)
            
            db.commit()
            
            # Write JSON log
            if settings.AUTO_SAVE_NEGOTIATIONS:
                self._write_json_log(db, run_id)
            
            # Remove from cache
            if run_id in active_rooms:
                del active_rooms[run_id]
            
            logger.info(f"Finalized run {run_id} with decision: {decision_type}")
            return outcome
    
    def _write_json_log(self, db: Session, run_id: str):
        """Write JSON log for a negotiation run."""
        run = db.query(NegotiationRun).filter(NegotiationRun.id == run_id).first()
        if not run:
            return
        
        # Get all data for log
        buyer_item = db.query(BuyerItem).filter(BuyerItem.id == run.buyer_item_id).first()
        buyer = db.query(Buyer).filter(Buyer.id == buyer_item.buyer_id).first() if buyer_item else None
        session = db.query(SessionModel).filter(SessionModel.id == run.session_id).first()
        
        messages = db.query(Message).filter(Message.negotiation_run_id == run_id).order_by(Message.turn_number).all()
        offers = db.query(Offer).join(Message).filter(Message.negotiation_run_id == run_id).all()
        outcome = db.query(NegotiationOutcome).filter(NegotiationOutcome.negotiation_run_id == run_id).first()
        
        # Build log structure
        log_data = {
            "metadata": {
                "session_id": run.session_id,
                "run_id": run_id,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "ended_at": run.ended_at.isoformat() if run.ended_at else None
            },
            "buyer": {
                "buyer_id": buyer.id if buyer else None,
                "buyer_name": buyer.name if buyer else None,
                "item_name": buyer_item.item_name if buyer_item else None,
                "quantity_needed": buyer_item.quantity_needed if buyer_item else None,
                "min_price": buyer_item.min_price_per_unit if buyer_item else None,
                "max_price": buyer_item.max_price_per_unit if buyer_item else None
            },
            "sellers": [],  # Would populate from participants
            "conversation_history": [
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
            ],
            "offers_over_time": [
                {
                    "offer_id": offer.id,
                    "message_id": offer.message_id,
                    "seller_id": offer.seller_id,
                    "price_per_unit": offer.price_per_unit,
                    "quantity": offer.quantity,
                    "timestamp": offer.timestamp.isoformat() if offer.timestamp else None
                }
                for offer in offers
            ],
            "decision": {
                "decision_type": outcome.decision_type if outcome else None,
                "selected_seller_id": outcome.selected_seller_id if outcome else None,
                "final_price": outcome.final_price_per_unit if outcome else None,
                "quantity": outcome.quantity if outcome else None,
                "total_cost": outcome.total_cost if outcome else None,
                "reason": outcome.decision_reason if outcome else None
            } if outcome else None,
            "duration": (run.ended_at - run.started_at).total_seconds() if run.started_at and run.ended_at else None,
            "rounds": run.current_round
        }
        
        # Write to file
        log_dir = Path(settings.LOGS_DIR) / session.id / run_id
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{run_id}.json"
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Wrote JSON log to {log_file}")
    
    @staticmethod
    def cleanup_old_logs():
        """Clean up logs older than retention period."""
        log_dir = Path(settings.LOGS_DIR)
        if not log_dir.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=settings.LOG_RETENTION_DAYS)
        deleted_count = 0
        
        for session_dir in log_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            # Check session directory modification time
            session_mtime = datetime.fromtimestamp(session_dir.stat().st_mtime)
            
            if session_mtime < cutoff_date:
                # Delete entire session directory
                import shutil
                shutil.rmtree(session_dir)
                deleted_count += 1
                logger.info(f"Deleted old log directory: {session_dir}")
            else:
                # Check individual run directories
                for run_dir in session_dir.iterdir():
                    if run_dir.is_dir():
                        run_mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
                        if run_mtime < cutoff_date:
                            import shutil
                            shutil.rmtree(run_dir)
                            deleted_count += 1
                            logger.info(f"Deleted old log directory: {run_dir}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old log directories")
    
    def get_active_room_state(self, room_id: str) -> Optional[NegotiationRoomState]:
        """
        Get active room state from cache.
        
        WHAT: Retrieve NegotiationRoomState from in-memory cache
        WHY: Fast access to active negotiation state
        HOW: Look up in active_rooms dict
        
        Args:
            room_id: Negotiation run ID
            
        Returns:
            NegotiationRoomState if found, None otherwise
        """
        if room_id in active_rooms:
            room_state, _ = active_rooms[room_id]
            return room_state
        return None
    
    def build_state_response(self, room_id: str, agent_id: Optional[str] = None, agent_type: Optional[str] = None) -> Optional[Dict]:
        """
        Build NegotiationStateResponse from database and cache.
        
        WHAT: Compose negotiation state for API response
        WHY: Centralize state assembly logic
        HOW: Query DB for messages/offers, combine with cached room state
        
        Args:
            room_id: Negotiation run ID
            agent_id: Optional agent ID filter for visibility
            agent_type: Optional agent type filter ('buyer' or 'seller')
            
        Returns:
            Dict matching NegotiationStateResponse schema or None if room not found
        """
        with get_db() as db:
            run = db.query(NegotiationRun).filter(NegotiationRun.id == room_id).first()
            if not run:
                return None
            
            buyer_item = db.query(BuyerItem).filter(BuyerItem.id == run.buyer_item_id).first()
            if not buyer_item:
                return None
            
            # Get messages
            messages_query = db.query(Message).filter(
                Message.negotiation_run_id == room_id
            ).order_by(Message.turn_number)
            
            # Apply visibility filter if agent_id/agent_type provided
            if agent_id and agent_type:
                from ..services.visibility_filter import filter_conversation
                # This would require converting DB messages to Message models
                # For now, return all messages
                pass
            
            messages = messages_query.all()
            
            # Get offers
            offers_query = db.query(Offer).join(Message).filter(
                Message.negotiation_run_id == room_id
            )
            offers = offers_query.all()
            
            # Build conversation history
            conversation_history = []
            for msg in messages:
                conv_entry = {
                    "message_id": msg.id,
                    "turn_number": msg.turn_number,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "sender_type": msg.sender_type,
                    "sender_id": msg.sender_id,
                    "sender_name": msg.sender_name,
                    "content": msg.message_text,
                    "mentioned_agents": json.loads(msg.mentioned_agents) if msg.mentioned_agents else []
                }
                conversation_history.append(conv_entry)
            
            # Build current offers dict (seller_id -> Offer)
            current_offers = {}
            for offer in offers:
                if offer.seller_id not in current_offers:
                    current_offers[offer.seller_id] = {
                        "price": offer.price_per_unit,
                        "quantity": offer.quantity
                    }
            
            # Get buyer constraints
            buyer_constraints = {
                "min_price_per_unit": buyer_item.min_price_per_unit,
                "max_price_per_unit": buyer_item.max_price_per_unit
            }
            
            return {
                "room_id": room_id,
                "item_name": buyer_item.item_name,
                "status": run.status,
                "current_round": run.current_round,
                "max_rounds": run.max_rounds,
                "conversation_history": conversation_history,
                "current_offers": current_offers,
                "buyer_constraints": buyer_constraints
            }


# Singleton instance
session_manager = SessionManager()

