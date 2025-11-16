"""
Unit tests for database schema validation.

WHAT: Test ORM models, constraints, and relationships
WHY: Ensure database integrity and proper constraint enforcement
HOW: Create test instances with valid/invalid data, test cascades
"""

import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from uuid import uuid4

from app.core.database import Base, engine, SessionLocal, init_db
from app.core.models import (
    Session, Buyer, BuyerItem, Seller, SellerInventory,
    NegotiationRun, NegotiationParticipant, Message, Offer, NegotiationOutcome,
    SessionStatus, NegotiationStatus
)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database for each test.
    
    WHAT: Setup and teardown test database
    WHY: Ensure test isolation
    HOW: Drop/create all tables before/after each test
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.mark.phase3
class TestSessionModel:
    """Test Session model and constraints."""
    
    def test_create_session_success(self, db_session):
        """Test creating a valid session."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice",
            status=SessionStatus.PENDING
        )
        db_session.add(session)
        db_session.commit()
        
        assert session.session_id is not None
        assert session.buyer_name == "Alice"
        assert session.status == SessionStatus.PENDING
        assert session.created_at is not None
    
    def test_session_cascade_delete_buyers(self, db_session):
        """Test that deleting session cascades to buyers."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice",
            status=SessionStatus.PENDING
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            session_id=session.session_id,
            buyer_id="buyer_1",
            name="Alice"
        )
        db_session.add(buyer)
        db_session.commit()
        
        buyer_id = buyer.id
        
        # Delete session
        db_session.delete(session)
        db_session.commit()
        
        # Verify buyer was cascade deleted
        result = db_session.query(Buyer).filter_by(id=buyer_id).first()
        assert result is None


@pytest.mark.phase3
class TestBuyerItemModel:
    """Test BuyerItem model and constraints."""
    
    def test_create_buyer_item_success(self, db_session):
        """Test creating a valid buyer item."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            session_id=session.session_id,
            buyer_id="buyer_1",
            name="Alice"
        )
        db_session.add(buyer)
        db_session.flush()
        
        item = BuyerItem(
            buyer_db_id=buyer.id,
            item_id="laptop_001",
            item_name="Laptop",
            quantity_needed=2,
            min_price_per_unit=800.0,
            max_price_per_unit=1200.0
        )
        db_session.add(item)
        db_session.commit()
        
        assert item.id is not None
        assert item.item_name == "Laptop"
        assert item.quantity_needed == 2
    
    def test_buyer_item_quantity_must_be_positive(self, db_session):
        """Test quantity_needed CHECK constraint."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            session_id=session.session_id,
            buyer_id="buyer_1",
            name="Alice"
        )
        db_session.add(buyer)
        db_session.flush()
        
        item = BuyerItem(
            buyer_db_id=buyer.id,
            item_id="laptop_001",
            item_name="Laptop",
            quantity_needed=0,  # Invalid: must be >= 1
            min_price_per_unit=800.0,
            max_price_per_unit=1200.0
        )
        db_session.add(item)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_buyer_item_min_price_must_be_non_negative(self, db_session):
        """Test min_price_per_unit CHECK constraint."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            session_id=session.session_id,
            buyer_id="buyer_1",
            name="Alice"
        )
        db_session.add(buyer)
        db_session.flush()
        
        item = BuyerItem(
            buyer_db_id=buyer.id,
            item_id="laptop_001",
            item_name="Laptop",
            quantity_needed=1,
            min_price_per_unit=-10.0,  # Invalid: must be >= 0
            max_price_per_unit=1200.0
        )
        db_session.add(item)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_buyer_item_max_must_be_greater_than_min(self, db_session):
        """Test max_price_per_unit > min_price_per_unit CHECK constraint."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            session_id=session.session_id,
            buyer_id="buyer_1",
            name="Alice"
        )
        db_session.add(buyer)
        db_session.flush()
        
        item = BuyerItem(
            buyer_db_id=buyer.id,
            item_id="laptop_001",
            item_name="Laptop",
            quantity_needed=1,
            min_price_per_unit=1200.0,
            max_price_per_unit=800.0  # Invalid: max <= min
        )
        db_session.add(item)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.phase3
class TestSellerInventoryModel:
    """Test SellerInventory model and constraints."""
    
    def test_create_inventory_success(self, db_session):
        """Test creating valid seller inventory."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        seller = Seller(
            session_id=session.session_id,
            seller_id="seller_1",
            name="Bob's Store",
            priority="maximize_profit",
            speaking_style="rude"
        )
        db_session.add(seller)
        db_session.flush()
        
        inventory = SellerInventory(
            seller_db_id=seller.id,
            item_id="laptop_001",
            item_name="Laptop",
            cost_price=700.0,
            selling_price=1100.0,
            least_price=850.0,
            quantity_available=5
        )
        db_session.add(inventory)
        db_session.commit()
        
        assert inventory.id is not None
        assert inventory.item_name == "Laptop"
        assert inventory.least_price == 850.0
    
    def test_inventory_unique_seller_item_constraint(self, db_session):
        """Test UNIQUE constraint on (seller_db_id, item_id)."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        seller = Seller(
            session_id=session.session_id,
            seller_id="seller_1",
            name="Bob's Store",
            priority="maximize_profit",
            speaking_style="rude"
        )
        db_session.add(seller)
        db_session.flush()
        
        inventory1 = SellerInventory(
            seller_db_id=seller.id,
            item_id="laptop_001",
            item_name="Laptop",
            cost_price=700.0,
            selling_price=1100.0,
            least_price=850.0,
            quantity_available=5
        )
        db_session.add(inventory1)
        db_session.commit()
        
        # Try to add duplicate (same seller, same item)
        inventory2 = SellerInventory(
            seller_db_id=seller.id,
            item_id="laptop_001",  # Duplicate item_id for same seller
            item_name="Laptop Pro",
            cost_price=800.0,
            selling_price=1200.0,
            least_price=900.0,
            quantity_available=3
        )
        db_session.add(inventory2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_inventory_price_constraints(self, db_session):
        """Test price relationship CHECK constraints."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        seller = Seller(
            session_id=session.session_id,
            seller_id="seller_1",
            name="Bob's Store",
            priority="maximize_profit",
            speaking_style="rude"
        )
        db_session.add(seller)
        db_session.flush()
        
        # Test: selling_price must be > cost_price
        inventory = SellerInventory(
            seller_db_id=seller.id,
            item_id="laptop_001",
            item_name="Laptop",
            cost_price=1000.0,
            selling_price=900.0,  # Invalid: selling < cost
            least_price=850.0,
            quantity_available=5
        )
        db_session.add(inventory)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.phase3
class TestNegotiationRunModel:
    """Test NegotiationRun model and relationships."""
    
    def test_create_negotiation_run_success(self, db_session):
        """Test creating a valid negotiation run."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        run = NegotiationRun(
            run_id=str(uuid4()),
            session_id=session.session_id,
            room_id="room_laptop_001",
            item_id="laptop_001",
            item_name="Laptop",
            status=NegotiationStatus.PENDING,
            max_rounds=5
        )
        db_session.add(run)
        db_session.commit()
        
        assert run.id is not None
        assert run.room_id == "room_laptop_001"
        assert run.status == NegotiationStatus.PENDING
    
    def test_negotiation_run_cascade_delete_messages(self, db_session):
        """Test that deleting run cascades to messages."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        run = NegotiationRun(
            run_id=str(uuid4()),
            session_id=session.session_id,
            room_id="room_laptop_001",
            item_id="laptop_001",
            item_name="Laptop"
        )
        db_session.add(run)
        db_session.flush()
        
        message = Message(
            message_id=str(uuid4()),
            negotiation_run_id=run.id,
            turn_number=1,
            sender_id="buyer_1",
            sender_type="buyer",
            sender_name="Alice",
            content="Hello!"
        )
        db_session.add(message)
        db_session.commit()
        
        message_id = message.message_id
        
        # Delete run
        db_session.delete(run)
        db_session.commit()
        
        # Verify message was cascade deleted
        result = db_session.query(Message).filter_by(message_id=message_id).first()
        assert result is None


@pytest.mark.phase3
class TestOfferModel:
    """Test Offer model and constraints."""
    
    def test_create_offer_success(self, db_session):
        """Test creating a valid offer."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        run = NegotiationRun(
            run_id=str(uuid4()),
            session_id=session.session_id,
            room_id="room_laptop_001",
            item_id="laptop_001",
            item_name="Laptop"
        )
        db_session.add(run)
        db_session.flush()
        
        message = Message(
            message_id=str(uuid4()),
            negotiation_run_id=run.id,
            turn_number=2,
            sender_id="seller_1",
            sender_type="seller",
            sender_name="Bob",
            content="I offer $1000"
        )
        db_session.add(message)
        db_session.flush()
        
        offer = Offer(
            message_id=message.message_id,
            negotiation_run_id=run.id,
            seller_id="seller_1",
            price=1000.0,
            quantity=2
        )
        db_session.add(offer)
        db_session.commit()
        
        assert offer.id is not None
        assert offer.price == 1000.0
        assert offer.quantity == 2
    
    def test_offer_price_non_negative_constraint(self, db_session):
        """Test price CHECK constraint."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        run = NegotiationRun(
            run_id=str(uuid4()),
            session_id=session.session_id,
            room_id="room_laptop_001",
            item_id="laptop_001",
            item_name="Laptop"
        )
        db_session.add(run)
        db_session.flush()
        
        message = Message(
            message_id=str(uuid4()),
            negotiation_run_id=run.id,
            turn_number=2,
            sender_id="seller_1",
            sender_type="seller",
            sender_name="Bob",
            content="Offer"
        )
        db_session.add(message)
        db_session.flush()
        
        offer = Offer(
            message_id=message.message_id,
            negotiation_run_id=run.id,
            seller_id="seller_1",
            price=-100.0,  # Invalid: negative price
            quantity=2
        )
        db_session.add(offer)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_offer_quantity_positive_constraint(self, db_session):
        """Test quantity CHECK constraint."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        run = NegotiationRun(
            run_id=str(uuid4()),
            session_id=session.session_id,
            room_id="room_laptop_001",
            item_id="laptop_001",
            item_name="Laptop"
        )
        db_session.add(run)
        db_session.flush()
        
        message = Message(
            message_id=str(uuid4()),
            negotiation_run_id=run.id,
            turn_number=2,
            sender_id="seller_1",
            sender_type="seller",
            sender_name="Bob",
            content="Offer"
        )
        db_session.add(message)
        db_session.flush()
        
        offer = Offer(
            message_id=message.message_id,
            negotiation_run_id=run.id,
            seller_id="seller_1",
            price=1000.0,
            quantity=0  # Invalid: must be >= 1
        )
        db_session.add(offer)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.phase3
class TestNegotiationOutcomeModel:
    """Test NegotiationOutcome model."""
    
    def test_create_outcome_success(self, db_session):
        """Test creating a valid negotiation outcome."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        run = NegotiationRun(
            run_id=str(uuid4()),
            session_id=session.session_id,
            room_id="room_laptop_001",
            item_id="laptop_001",
            item_name="Laptop",
            status=NegotiationStatus.COMPLETED
        )
        db_session.add(run)
        db_session.flush()
        
        outcome = NegotiationOutcome(
            negotiation_run_id=run.id,
            status="completed",
            selected_seller_id="seller_1",
            selected_seller_name="Bob",
            final_price_per_unit=1000.0,
            final_quantity=2,
            final_total_cost=2000.0,
            total_rounds=3,
            total_messages=10,
            total_offers=3,
            duration_seconds=45.5,
            decision_reason="Best price"
        )
        db_session.add(outcome)
        db_session.commit()
        
        assert outcome.id is not None
        assert outcome.final_total_cost == 2000.0
        assert outcome.decision_reason == "Best price"
    
    def test_outcome_unique_per_negotiation_run(self, db_session):
        """Test UNIQUE constraint on negotiation_run_id."""
        session = Session(
            session_id=str(uuid4()),
            buyer_id="buyer_1",
            buyer_name="Alice"
        )
        db_session.add(session)
        db_session.flush()
        
        run = NegotiationRun(
            run_id=str(uuid4()),
            session_id=session.session_id,
            room_id="room_laptop_001",
            item_id="laptop_001",
            item_name="Laptop"
        )
        db_session.add(run)
        db_session.flush()
        
        outcome1 = NegotiationOutcome(
            negotiation_run_id=run.id,
            status="completed",
            total_rounds=3,
            total_messages=10,
            total_offers=3,
            duration_seconds=45.5
        )
        db_session.add(outcome1)
        db_session.commit()
        
        # Try to add second outcome for same run
        outcome2 = NegotiationOutcome(
            negotiation_run_id=run.id,  # Duplicate run_id
            status="completed",
            total_rounds=3,
            total_messages=10,
            total_offers=3,
            duration_seconds=45.5
        )
        db_session.add(outcome2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

