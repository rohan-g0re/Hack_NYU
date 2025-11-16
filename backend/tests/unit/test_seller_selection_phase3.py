"""
Seller selection tests for Phase 3.

WHAT: Test seller selection logic with diverse inventories and constraints
WHY: Ensure correct participant formation and reason codes
HOW: Test various scenarios with different price/quantity combinations
"""

import pytest
import uuid
from app.core.database import get_db, init_db, Base, engine
from app.core.models import Session, Buyer, BuyerItem, Seller, SellerInventory
from app.services.seller_selection import select_sellers_for_item


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
    """Create a sample session."""
    session = Session(
        id=str(uuid.uuid4()),
        llm_model="test-model",
        status="draft"
    )
    db_session.add(session)
    db_session.flush()
    return session


@pytest.fixture
def sample_buyer_item(db_session, sample_session):
    """Create a sample buyer item."""
    buyer = Buyer(
        id=str(uuid.uuid4()),
        session_id=sample_session.id,
        name="Test Buyer"
    )
    db_session.add(buyer)
    db_session.flush()
    
    buyer_item = BuyerItem(
        id=str(uuid.uuid4()),
        buyer_id=buyer.id,
        item_id="laptop",
        item_name="Gaming Laptop",
        quantity_needed=2,
        min_price_per_unit=800.0,
        max_price_per_unit=1200.0
    )
    db_session.add(buyer_item)
    db_session.commit()
    return buyer_item


class TestSellerSelection:
    """Test seller selection logic."""
    
    def test_select_sellers_with_matching_inventory(self, db_session, sample_session, sample_buyer_item):
        """Test selecting sellers who have matching inventory."""
        # Create sellers with matching inventory
        seller1 = Seller(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            name="TechStore",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller1)
        db_session.flush()
        
        inv1 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller1.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            cost_price=700.0,
            selling_price=1100.0,
            least_price=900.0,
            quantity_available=5
        )
        db_session.add(inv1)
        
        seller2 = Seller(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            name="BargainPCs",
            priority="maximize_profit",
            speaking_style="rude"
        )
        db_session.add(seller2)
        db_session.flush()
        
        inv2 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller2.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            cost_price=750.0,
            selling_price=1150.0,
            least_price=950.0,
            quantity_available=3
        )
        db_session.add(inv2)
        db_session.commit()
        
        # Select sellers
        sellers = [seller1, seller2]
        inventories = [[inv1], [inv2]]
        
        participating, skipped = select_sellers_for_item(
            sample_buyer_item,
            sellers,
            inventories
        )
        
        assert len(participating) == 2
        assert len(skipped) == 0
        assert seller1 in participating
        assert seller2 in participating
    
    def test_skip_seller_no_inventory(self, db_session, sample_session, sample_buyer_item):
        """Test skipping seller with no matching inventory."""
        seller1 = Seller(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            name="TechStore",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller1)
        db_session.flush()
        
        # Seller has different item
        inv1 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller1.id,
            item_id="mouse",
            item_name="Gaming Mouse",
            cost_price=20.0,
            selling_price=40.0,
            least_price=30.0,
            quantity_available=10
        )
        db_session.add(inv1)
        db_session.commit()
        
        sellers = [seller1]
        inventories = [[inv1]]
        
        participating, skipped = select_sellers_for_item(
            sample_buyer_item,
            sellers,
            inventories
        )
        
        assert len(participating) == 0
        assert len(skipped) == 1
        assert skipped[0]["reason_code"] == "no_inventory"
        assert skipped[0]["seller_id"] == seller1.id
    
    def test_skip_seller_insufficient_quantity(self, db_session, sample_session, sample_buyer_item):
        """Test skipping seller with insufficient quantity."""
        seller1 = Seller(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            name="TechStore",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller1)
        db_session.flush()
        
        # Seller has item but insufficient quantity (needs 2, has 1)
        inv1 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller1.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            cost_price=700.0,
            selling_price=1100.0,
            least_price=900.0,
            quantity_available=1  # Less than needed (2)
        )
        db_session.add(inv1)
        db_session.commit()
        
        sellers = [seller1]
        inventories = [[inv1]]
        
        participating, skipped = select_sellers_for_item(
            sample_buyer_item,
            sellers,
            inventories
        )
        
        assert len(participating) == 0
        assert len(skipped) == 1
        assert skipped[0]["reason_code"] == "insufficient_quantity"
    
    def test_skip_seller_price_mismatch(self, db_session, sample_session, sample_buyer_item):
        """Test skipping seller with price mismatch."""
        seller1 = Seller(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            name="TechStore",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller1)
        db_session.flush()
        
        # Seller's least_price (1300) > buyer's max_price (1200)
        inv1 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller1.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            cost_price=1000.0,
            selling_price=1500.0,
            least_price=1300.0,  # Too high for buyer
            quantity_available=5
        )
        db_session.add(inv1)
        db_session.commit()
        
        sellers = [seller1]
        inventories = [[inv1]]
        
        participating, skipped = select_sellers_for_item(
            sample_buyer_item,
            sellers,
            inventories
        )
        
        assert len(participating) == 0
        assert len(skipped) == 1
        assert skipped[0]["reason_code"] == "price_mismatch"
    
    def test_mixed_scenarios(self, db_session, sample_session, sample_buyer_item):
        """Test mixed scenarios with multiple sellers."""
        # Seller 1: Valid participant
        seller1 = Seller(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            name="TechStore",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller1)
        db_session.flush()
        
        inv1 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller1.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            cost_price=700.0,
            selling_price=1100.0,
            least_price=900.0,
            quantity_available=5
        )
        db_session.add(inv1)
        
        # Seller 2: No inventory
        seller2 = Seller(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            name="MouseStore",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller2)
        db_session.flush()
        
        inv2 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller2.id,
            item_id="mouse",
            item_name="Gaming Mouse",
            cost_price=20.0,
            selling_price=40.0,
            least_price=30.0,
            quantity_available=10
        )
        db_session.add(inv2)
        
        # Seller 3: Insufficient quantity
        seller3 = Seller(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            name="LowStock",
            priority="customer_retention",
            speaking_style="very_sweet"
        )
        db_session.add(seller3)
        db_session.flush()
        
        inv3 = SellerInventory(
            id=str(uuid.uuid4()),
            seller_id=seller3.id,
            item_id="laptop",
            item_name="Gaming Laptop",
            cost_price=750.0,
            selling_price=1150.0,
            least_price=950.0,
            quantity_available=1  # Insufficient
        )
        db_session.add(inv3)
        db_session.commit()
        
        sellers = [seller1, seller2, seller3]
        inventories = [[inv1], [inv2], [inv3]]
        
        participating, skipped = select_sellers_for_item(
            sample_buyer_item,
            sellers,
            inventories
        )
        
        assert len(participating) == 1
        assert seller1 in participating
        assert len(skipped) == 2
        assert skipped[0]["reason_code"] in ["no_inventory", "insufficient_quantity"]
        assert skipped[1]["reason_code"] in ["no_inventory", "insufficient_quantity"]

