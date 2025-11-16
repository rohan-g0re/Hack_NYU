"""
Summary service tests for Phase 3.

WHAT: Test metrics computation across seeded runs
WHY: Ensure summary accuracy for frontend
HOW: Seed multiple runs, verify totals, averages, durations, message counts
"""

import pytest
import uuid
from datetime import datetime, timedelta
from app.core.database import get_db, init_db, Base, engine
from app.core.models import (
    Session, Buyer, BuyerItem, Seller, SellerInventory,
    NegotiationRun, NegotiationParticipant, Message, Offer, NegotiationOutcome
)
from app.services.summary_service import (
    compute_session_summary, compute_run_summary,
    get_purchase_summaries, get_failed_items
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    with get_db() as db:
        yield db
        db.rollback()


@pytest.fixture
def sample_session(db_session):
    """Create a sample session with buyer and sellers."""
    session = Session(
        id=str(uuid.uuid4()),
        llm_model="test-model",
        status="active"
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
    
    seller = Seller(
        id=str(uuid.uuid4()),
        session_id=session.id,
        name="TechStore",
        priority="customer_retention",
        speaking_style="very_sweet"
    )
    db_session.add(seller)
    db_session.commit()
    
    return session, buyer, seller


class TestSummaryService:
    """Test summary service functionality."""
    
    def test_compute_session_summary_empty(self, db_session, sample_session):
        """Test summary for session with no runs."""
        session, _, _ = sample_session
        
        summary = compute_session_summary(db_session, session.id)
        
        assert summary["session_id"] == session.id
        assert summary["total_runs"] == 0
        assert summary["completed_runs"] == 0
        assert summary["successful_deals"] == 0
        assert summary["total_messages"] == 0
    
    def test_compute_session_summary_with_runs(self, db_session, sample_session):
        """Test summary with multiple runs."""
        session, buyer, seller = sample_session
        
        # Create buyer items
        item1 = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            quantity_needed=2,
            min_price_per_unit=800.0,
            max_price_per_unit=1200.0
        )
        db_session.add(item1)
        db_session.flush()
        
        item2 = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="mouse",
            item_name="Gaming Mouse",
            quantity_needed=1,
            min_price_per_unit=20.0,
            max_price_per_unit=50.0
        )
        db_session.add(item2)
        db_session.flush()
        
        # Create runs
        start_time = datetime.now()
        
        run1 = NegotiationRun(
            id=str(uuid.uuid4()),
            session_id=session.id,
            buyer_item_id=item1.id,
            status="completed",
            started_at=start_time,
            ended_at=start_time + timedelta(seconds=30),
            current_round=3,
            max_rounds=10
        )
        db_session.add(run1)
        db_session.flush()
        
        run2 = NegotiationRun(
            id=str(uuid.uuid4()),
            session_id=session.id,
            buyer_item_id=item2.id,
            status="completed",
            started_at=start_time + timedelta(seconds=10),
            ended_at=start_time + timedelta(seconds=50),
            current_round=2,
            max_rounds=10
        )
        db_session.add(run2)
        db_session.flush()
        
        # Create messages
        msg1 = Message(
            id=str(uuid.uuid4()),
            negotiation_run_id=run1.id,
            turn_number=1,
            sender_type="buyer",
            sender_id=buyer.id,
            sender_name="Test Buyer",
            message_text="Hello"
        )
        db_session.add(msg1)
        
        msg2 = Message(
            id=str(uuid.uuid4()),
            negotiation_run_id=run1.id,
            turn_number=1,
            sender_type="seller",
            sender_id=seller.id,
            sender_name="TechStore",
            message_text="Hi there"
        )
        db_session.add(msg2)
        
        msg3 = Message(
            id=str(uuid.uuid4()),
            negotiation_run_id=run2.id,
            turn_number=1,
            sender_type="buyer",
            sender_id=buyer.id,
            sender_name="Test Buyer",
            message_text="Hello"
        )
        db_session.add(msg3)
        
        # Create outcomes
        outcome1 = NegotiationOutcome(
            id=str(uuid.uuid4()),
            negotiation_run_id=run1.id,
            decision_type="deal",
            selected_seller_id=seller.id,
            final_price_per_unit=950.0,
            quantity=2,
            total_cost=1900.0
        )
        db_session.add(outcome1)
        
        outcome2 = NegotiationOutcome(
            id=str(uuid.uuid4()),
            negotiation_run_id=run2.id,
            decision_type="deal",
            selected_seller_id=seller.id,
            final_price_per_unit=30.0,
            quantity=1,
            total_cost=30.0
        )
        db_session.add(outcome2)
        db_session.commit()
        
        # Compute summary
        summary = compute_session_summary(db_session, session.id)
        
        assert summary["total_runs"] == 2
        assert summary["completed_runs"] == 2
        assert summary["successful_deals"] == 2
        assert summary["total_messages"] == 3
        assert summary["average_rounds"] == 2.5  # (3 + 2) / 2
        assert summary["total_cost"] == 1930.0  # 1900 + 30
    
    def test_compute_run_summary(self, db_session, sample_session):
        """Test run summary computation."""
        session, buyer, seller = sample_session
        
        item = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            quantity_needed=2,
            min_price_per_unit=800.0,
            max_price_per_unit=1200.0
        )
        db_session.add(item)
        db_session.flush()
        
        start_time = datetime.now()
        run = NegotiationRun(
            id=str(uuid.uuid4()),
            session_id=session.id,
            buyer_item_id=item.id,
            status="completed",
            started_at=start_time,
            ended_at=start_time + timedelta(seconds=45),
            current_round=3,
            max_rounds=10
        )
        db_session.add(run)
        db_session.flush()
        
        # Create messages and offers
        msg1 = Message(
            id=str(uuid.uuid4()),
            negotiation_run_id=run.id,
            turn_number=1,
            sender_type="buyer",
            sender_id=buyer.id,
            sender_name="Test Buyer",
            message_text="Hello"
        )
        db_session.add(msg1)
        db_session.flush()
        
        offer1 = Offer(
            id=str(uuid.uuid4()),
            message_id=msg1.id,
            seller_id=seller.id,
            price_per_unit=950.0,
            quantity=2
        )
        db_session.add(offer1)
        
        outcome = NegotiationOutcome(
            id=str(uuid.uuid4()),
            negotiation_run_id=run.id,
            decision_type="deal",
            selected_seller_id=seller.id,
            final_price_per_unit=950.0,
            quantity=2,
            total_cost=1900.0
        )
        db_session.add(outcome)
        db_session.commit()
        
        # Compute run summary
        summary = compute_run_summary(db_session, run.id)
        
        assert summary["run_id"] == run.id
        assert summary["status"] == "completed"
        assert summary["current_round"] == 3
        assert summary["message_count"] == 1
        assert summary["offer_count"] == 1
        assert summary["duration_seconds"] == 45.0
        assert summary["outcome"]["decision_type"] == "deal"
        assert summary["outcome"]["total_cost"] == 1900.0
    
    def test_get_purchase_summaries(self, db_session, sample_session):
        """Test getting purchase summaries."""
        session, buyer, seller = sample_session
        
        item = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            quantity_needed=2,
            min_price_per_unit=800.0,
            max_price_per_unit=1200.0
        )
        db_session.add(item)
        db_session.flush()
        
        start_time = datetime.now()
        run = NegotiationRun(
            id=str(uuid.uuid4()),
            session_id=session.id,
            buyer_item_id=item.id,
            status="completed",
            started_at=start_time,
            ended_at=start_time + timedelta(seconds=30),
            current_round=3
        )
        db_session.add(run)
        db_session.flush()
        
        outcome = NegotiationOutcome(
            id=str(uuid.uuid4()),
            negotiation_run_id=run.id,
            decision_type="deal",
            selected_seller_id=seller.id,
            final_price_per_unit=950.0,
            quantity=2,
            total_cost=1900.0
        )
        db_session.add(outcome)
        db_session.commit()
        
        # Get purchase summaries
        summaries = get_purchase_summaries(db_session, session.id)
        
        assert len(summaries) == 1
        assert summaries[0]["item_name"] == "Gaming Laptop"
        assert summaries[0]["quantity"] == 2
        assert summaries[0]["selected_seller"] == "TechStore"
        assert summaries[0]["final_price_per_unit"] == 950.0
        assert summaries[0]["total_cost"] == 1900.0
        assert summaries[0]["negotiation_rounds"] == 3
    
    def test_get_failed_items(self, db_session, sample_session):
        """Test getting failed items."""
        session, buyer, _ = sample_session
        
        item = BuyerItem(
            id=str(uuid.uuid4()),
            buyer_id=buyer.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            quantity_needed=2,
            min_price_per_unit=800.0,
            max_price_per_unit=1200.0
        )
        db_session.add(item)
        db_session.flush()
        
        run = NegotiationRun(
            id=str(uuid.uuid4()),
            session_id=session.id,
            buyer_item_id=item.id,
            status="no_sellers_available"
        )
        db_session.add(run)
        db_session.commit()
        
        # Get failed items
        failed = get_failed_items(db_session, session.id)
        
        assert len(failed) == 1
        assert failed[0]["item_name"] == "Gaming Laptop"
        assert failed[0]["reason"] == "no_sellers_available"

