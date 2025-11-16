"""
Schema and constraint tests for Phase 3.

WHAT: Test database constraints, unique constraints, foreign keys, cascades
WHY: Ensure data integrity at database level
HOW: Insert invalid data and verify IntegrityError is raised
"""

import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid

from app.core.database import get_db, init_db, Base, engine
from app.core.models import (
    Session, Buyer, BuyerItem, Seller, SellerInventory,
    NegotiationRun, NegotiationParticipant, Message, Offer, NegotiationOutcome
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    # Drop and recreate tables
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    with get_db() as db:
        yield db
        db.rollback()


class TestCheckConstraints:
    """Test CHECK constraints."""
    
    def test_buyer_item_quantity_positive(self, db_session):
        """Test that quantity_needed must be > 0."""
        session = Session(
            id=str(uuid.uuid4()),
            llm_model="test-model",
            status="draft"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Buyer"
        )
        db_session.add(buyer)
        db_session.flush()
        
        # Try to insert with quantity = 0 (should fail)
        buyer_item = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="item1",
            item_name="Test Item",
            quantity_needed=0,  # Invalid
            min_price_per_unit=10.0,
            max_price_per_unit=20.0
        )
        db_session.add(buyer_item)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_buyer_item_max_price_greater_than_min(self, db_session):
        """Test that max_price_per_unit > min_price_per_unit."""
        session = Session(
            id=str(uuid.uuid4()),
            llm_model="test-model",
            status="draft"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Buyer"
        )
        db_session.add(buyer)
        db_session.flush()
        
        # Try to insert with max <= min (should fail)
        buyer_item = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="item1",
            item_name="Test Item",
            quantity_needed=1,
            min_price_per_unit=20.0,
            max_price_per_unit=10.0  # Invalid: max <= min
        )
        db_session.add(buyer_item)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_seller_inventory_price_constraints(self, db_session):
        """Test seller inventory price constraints."""
        session = Session(
            id=str(uuid.uuid4()),
            llm_model="test-model",
            status="draft"
        )
        db_session.add(session)
        db_session.flush()
        
        seller = Seller(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Seller",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller)
        db_session.flush()
        
        # Try invalid: selling_price <= cost_price
        inv1 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller.id,
            item_id="item1",
            item_name="Test Item",
            cost_price=10.0,
            selling_price=10.0,  # Invalid: should be > cost_price
            least_price=9.0,
            quantity_available=5
        )
        db_session.add(inv1)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
        
        # Try invalid: least_price <= cost_price
        inv2 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller.id,
            item_id="item1",
            item_name="Test Item",
            cost_price=10.0,
            selling_price=20.0,
            least_price=10.0,  # Invalid: should be > cost_price
            quantity_available=5
        )
        db_session.add(inv2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
        
        # Try invalid: least_price >= selling_price
        inv3 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller.id,
            item_id="item1",
            item_name="Test Item",
            cost_price=10.0,
            selling_price=20.0,
            least_price=25.0,  # Invalid: should be < selling_price
            quantity_available=5
        )
        db_session.add(inv3)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestUniqueConstraints:
    """Test UNIQUE constraints."""
    
    def test_seller_inventory_unique_seller_item(self, db_session):
        """Test that (seller_id, item_id) is unique."""
        session = Session(
            id=str(uuid.uuid4()),
            llm_model="test-model",
            status="draft"
        )
        db_session.add(session)
        db_session.flush()
        
        seller = Seller(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Seller",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller)
        db_session.flush()
        
        # Insert first inventory item
        inv1 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller.id,
            item_id="item1",
            item_name="Test Item",
            cost_price=10.0,
            selling_price=20.0,
            least_price=15.0,
            quantity_available=5
        )
        db_session.add(inv1)
        db_session.commit()
        
        # Try to insert duplicate (seller_id, item_id)
        inv2 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller.id,
            item_id="item1",  # Same item_id
            item_name="Test Item 2",
            cost_price=12.0,
            selling_price=22.0,
            least_price=17.0,
            quantity_available=3
        )
        db_session.add(inv2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_negotiation_participant_unique(self, db_session):
        """Test that (negotiation_run_id, seller_id) is unique."""
        session = Session(
            id=str(uuid.uuid4()),
            llm_model="test-model",
            status="draft"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Buyer"
        )
        db_session.add(buyer)
        db_session.flush()
        
        buyer_item = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="item1",
            item_name="Test Item",
            quantity_needed=1,
            min_price_per_unit=10.0,
            max_price_per_unit=20.0
        )
        db_session.add(buyer_item)
        db_session.flush()
        
        run = NegotiationRun(
            id=str(uuid.uuid4()),
            session_id=session.id,
            buyer_item_id=buyer_item.id,
            status="pending"
        )
        db_session.add(run)
        db_session.flush()
        
        seller = Seller(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Seller",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller)
        db_session.flush()
        
        # Insert first participant
        part1 = NegotiationParticipant(
            id=str(uuid.uuid4()),
            negotiation_run_id=run.id,
            seller_id=seller.id
        )
        db_session.add(part1)
        db_session.commit()
        
        # Try to insert duplicate
        part2 = NegotiationParticipant(
            id=str(uuid.uuid4()),
            negotiation_run_id=run.id,
            seller_id=seller.id  # Same seller
        )
        db_session.add(part2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestForeignKeyCascades:
    """Test foreign key cascades."""
    
    def test_session_delete_cascades_to_buyer(self, db_session):
        """Test that deleting session cascades to buyer."""
        session = Session(
            id=str(uuid.uuid4()),
            llm_model="test-model",
            status="draft"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Buyer"
        )
        db_session.add(buyer)
        db_session.commit()
        
        buyer_id = buyer.id
        
        # Delete session
        db_session.delete(session)
        db_session.commit()
        
        # Verify buyer is deleted
        buyer_check = db_session.query(Buyer).filter(Buyer.id == buyer_id).first()
        assert buyer_check is None
    
    def test_buyer_delete_cascades_to_buyer_items(self, db_session):
        """Test that deleting buyer cascades to buyer items."""
        session = Session(
            id=str(uuid.uuid4()),
            llm_model="test-model",
            status="draft"
        )
        db_session.add(session)
        db_session.flush()
        
        buyer = Buyer(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Buyer"
        )
        db_session.add(buyer)
        db_session.flush()
        
        buyer_item = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="item1",
            item_name="Test Item",
            quantity_needed=1,
            min_price_per_unit=10.0,
            max_price_per_unit=20.0
        )
        db_session.add(buyer_item)
        db_session.commit()
        
        item_id = buyer_item.id
        
        # Delete buyer
        db_session.delete(buyer)
        db_session.commit()
        
        # Verify buyer item is deleted
        item_check = db_session.query(BuyerItem).filter(BuyerItem.id == item_id).first()
        assert item_check is None
    
    def test_seller_delete_cascades_to_inventory(self, db_session):
        """Test that deleting seller cascades to inventory."""
        session = Session(
            id=str(uuid.uuid4()),
            llm_model="test-model",
            status="draft"
        )
        db_session.add(session)
        db_session.flush()
        
        seller = Seller(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name="Test Seller",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller)
        db_session.flush()
        
        inv = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller.id,
            item_id="item1",
            item_name="Test Item",
            cost_price=10.0,
            selling_price=20.0,
            least_price=15.0,
            quantity_available=5
        )
        db_session.add(inv)
        db_session.commit()
        
        inv_id = inv.id
        
        # Delete seller
        db_session.delete(seller)
        db_session.commit()
        
        # Verify inventory is deleted
        inv_check = db_session.query(SellerInventory).filter(SellerInventory.id == inv_id).first()
        assert inv_check is None


class TestIndexes:
    """Test that indexes exist."""
    
    def test_indexes_exist(self, db_session):
        """Verify that key indexes exist."""
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        
        # Check Session indexes
        session_indexes = [idx['name'] for idx in inspector.get_indexes('sessions')]
        assert 'idx_sessions_status' in session_indexes
        
        # Check Buyer indexes
        buyer_indexes = [idx['name'] for idx in inspector.get_indexes('buyers')]
        assert 'idx_buyers_session' in buyer_indexes
        
        # Check NegotiationRun indexes
        run_indexes = [idx['name'] for idx in inspector.get_indexes('negotiation_runs')]
        assert 'idx_negotiation_runs_session' in run_indexes
        assert 'idx_negotiation_runs_status' in run_indexes
        
        # Check Message indexes
        message_indexes = [idx['name'] for idx in inspector.get_indexes('messages')]
        assert 'idx_messages_negotiation' in message_indexes
        assert 'idx_messages_turn' in message_indexes

