"""
Session manager integration tests for Phase 3.

WHAT: Test session lifecycle, DB persistence, message/offer recording, finalization
WHY: Ensure orchestration correctness
HOW: Create session → start run → record messages/offers → finalize; verify DB state
"""

import pytest
import uuid
from datetime import datetime, timedelta
from app.core.database import get_db, init_db, Base, engine
from app.core.session_manager import SessionManager
from app.core.models import Session, NegotiationRun, Message, Offer, NegotiationOutcome
from app.models.api_schemas import InitializeSessionRequest, BuyerConfig, ShoppingItem, SellerConfig, InventoryItem, SellerProfile, LLMConfig


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    with get_db() as db:
        yield db
        db.rollback()


@pytest.fixture
def sample_request():
    """Create a sample InitializeSessionRequest."""
    return InitializeSessionRequest(
        buyer=BuyerConfig(
            name="Test Buyer",
            shopping_list=[
                ShoppingItem(
                    item_id="laptop",
                    item_name="Gaming Laptop",
                    quantity_needed=2,
                    min_price_per_unit=800.0,
                    max_price_per_unit=1200.0
                )
            ]
        ),
        sellers=[
            SellerConfig(
                name="TechStore",
                inventory=[
                    InventoryItem(
                        item_id="laptop",
                        item_name="Gaming Laptop",
                        cost_price=700.0,
                        selling_price=1100.0,
                        least_price=900.0,
                        quantity_available=5
                    )
                ],
                profile=SellerProfile(
                    priority="customer_retention",
                    speaking_style="very_sweet"
                )
            )
        ],
        llm_config=LLMConfig(
            model="test-model",
            temperature=0.7,
            max_tokens=500
        )
    )


class TestSessionManager:
    """Test session manager functionality."""
    
    def test_create_session(self, db_session, sample_request):
        """Test creating a session."""
        manager = SessionManager()
        response = manager.create_session(sample_request)
        
        assert response.session_id is not None
        assert response.buyer_id is not None
        assert len(response.seller_ids) == 1
        assert len(response.negotiation_rooms) == 1
        assert response.total_rooms == 1
        
        # Verify DB persistence
        session = db_session.query(Session).filter(Session.id == response.session_id).first()
        assert session is not None
        assert session.llm_model == "test-model"
        assert session.status == "draft"
    
    def test_get_session(self, db_session, sample_request):
        """Test getting session details."""
        manager = SessionManager()
        create_response = manager.create_session(sample_request)
        
        session_details = manager.get_session(create_response.session_id)
        
        assert session_details is not None
        assert session_details["session_id"] == create_response.session_id
        assert session_details["status"] == "draft"
        assert session_details["buyer_name"] == "Test Buyer"
    
    def test_delete_session(self, db_session, sample_request):
        """Test deleting a session."""
        manager = SessionManager()
        create_response = manager.create_session(sample_request)
        
        result = manager.delete_session(create_response.session_id)
        
        assert result["deleted"] is True
        
        # Verify deletion
        session = db_session.query(Session).filter(Session.id == create_response.session_id).first()
        assert session is None
    
    def test_start_negotiation(self, db_session, sample_request):
        """Test starting a negotiation."""
        manager = SessionManager()
        create_response = manager.create_session(sample_request)
        
        room_id = create_response.negotiation_rooms[0].room_id
        
        result = manager.start_negotiation(room_id)
        
        assert result["status"] == "active"
        assert result["started_at"] is not None
        
        # Verify DB update
        run = db_session.query(NegotiationRun).filter(NegotiationRun.id == room_id).first()
        assert run.status == "active"
        assert run.started_at is not None
    
    def test_record_message(self, db_session, sample_request):
        """Test recording a message."""
        manager = SessionManager()
        create_response = manager.create_session(sample_request)
        room_id = create_response.negotiation_rooms[0].room_id
        manager.start_negotiation(room_id)
        
        buyer_id = create_response.buyer_id
        
        message = manager.record_message(
            run_id=room_id,
            turn_number=1,
            sender_type="buyer",
            sender_id=buyer_id,
            sender_name="Test Buyer",
            message_text="Hello, I'm interested in buying laptops.",
            mentioned_agents=["seller1"]
        )
        
        assert message.id is not None
        
        # Verify DB persistence
        db_message = db_session.query(Message).filter(Message.id == message.id).first()
        assert db_message is not None
        assert db_message.message_text == "Hello, I'm interested in buying laptops."
        assert db_message.turn_number == 1
    
    def test_record_offer(self, db_session, sample_request):
        """Test recording an offer."""
        manager = SessionManager()
        create_response = manager.create_session(sample_request)
        room_id = create_response.negotiation_rooms[0].room_id
        manager.start_negotiation(room_id)
        
        buyer_id = create_response.buyer_id
        seller_id = create_response.seller_ids[0]
        
        message = manager.record_message(
            run_id=room_id,
            turn_number=1,
            sender_type="seller",
            sender_id=seller_id,
            sender_name="TechStore",
            message_text="I can offer you laptops at $950 each."
        )
        
        offer = manager.record_offer(
            message_id=message.id,
            seller_id=seller_id,
            price_per_unit=950.0,
            quantity=2
        )
        
        assert offer.id is not None
        
        # Verify DB persistence
        db_offer = db_session.query(Offer).filter(Offer.id == offer.id).first()
        assert db_offer is not None
        assert db_offer.price_per_unit == 950.0
        assert db_offer.quantity == 2
    
    def test_finalize_run(self, db_session, sample_request):
        """Test finalizing a negotiation run."""
        manager = SessionManager()
        create_response = manager.create_session(sample_request)
        room_id = create_response.negotiation_rooms[0].room_id
        manager.start_negotiation(room_id)
        
        seller_id = create_response.seller_ids[0]
        
        outcome = manager.finalize_run(
            run_id=room_id,
            decision_type="deal",
            selected_seller_id=seller_id,
            final_price_per_unit=950.0,
            quantity=2,
            decision_reason="Best price and availability"
        )
        
        assert outcome.id is not None
        assert outcome.decision_type == "deal"
        assert outcome.selected_seller_id == seller_id
        assert outcome.final_price_per_unit == 950.0
        assert outcome.total_cost == 1900.0  # 950 * 2
        
        # Verify DB persistence
        db_outcome = db_session.query(NegotiationOutcome).filter(
            NegotiationOutcome.id == outcome.id
        ).first()
        assert db_outcome is not None
        
        # Verify run status updated
        run = db_session.query(NegotiationRun).filter(NegotiationRun.id == room_id).first()
        assert run.status == "completed"
        assert run.ended_at is not None
    
    def test_complete_negotiation_flow(self, db_session, sample_request):
        """Test complete negotiation flow."""
        manager = SessionManager()
        
        # Create session
        create_response = manager.create_session(sample_request)
        room_id = create_response.negotiation_rooms[0].room_id
        buyer_id = create_response.buyer_id
        seller_id = create_response.seller_ids[0]
        
        # Start negotiation
        manager.start_negotiation(room_id)
        
        # Record buyer message
        msg1 = manager.record_message(
            run_id=room_id,
            turn_number=1,
            sender_type="buyer",
            sender_id=buyer_id,
            sender_name="Test Buyer",
            message_text="Hello, I need 2 laptops."
        )
        
        # Record seller response with offer
        msg2 = manager.record_message(
            run_id=room_id,
            turn_number=1,
            sender_type="seller",
            sender_id=seller_id,
            sender_name="TechStore",
            message_text="I can offer $950 per laptop."
        )
        
        offer = manager.record_offer(
            message_id=msg2.id,
            seller_id=seller_id,
            price_per_unit=950.0,
            quantity=2
        )
        
        # Finalize
        outcome = manager.finalize_run(
            run_id=room_id,
            decision_type="deal",
            selected_seller_id=seller_id,
            final_price_per_unit=950.0,
            quantity=2,
            decision_reason="Good price"
        )
        
        # Verify all records persisted
        assert db_session.query(Message).filter(Message.negotiation_run_id == room_id).count() == 2
        assert db_session.query(Offer).join(Message).filter(Message.negotiation_run_id == room_id).count() == 1
        assert outcome is not None

