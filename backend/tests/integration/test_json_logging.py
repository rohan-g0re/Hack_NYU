"""
JSON logging integration tests for Phase 3.

WHAT: Test log generation and schema validation
WHY: Ensure negotiation logs are properly saved and structured
HOW: Create runs, record messages/offers, finalize, verify log files and schema
"""

import pytest
import json
import uuid
from pathlib import Path
from datetime import datetime
from app.core.database import get_db, init_db, Base, engine
from app.core.session_manager import SessionManager
from app.core.models import Session, Buyer, BuyerItem, Seller, NegotiationRun, Message, Offer, NegotiationOutcome
from app.core.config import settings
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


@pytest.fixture(autouse=True)
def cleanup_logs():
    """Clean up logs before and after each test."""
    log_dir = Path(settings.LOGS_DIR)
    if log_dir.exists():
        import shutil
        shutil.rmtree(log_dir)
    yield
    if log_dir.exists():
        import shutil
        shutil.rmtree(log_dir)


class TestJSONLogging:
    """Test JSON log generation and schema."""
    
    def test_log_generated_on_finalize(self, db_session, sample_request):
        """Test that JSON log is generated when run is finalized."""
        manager = SessionManager()
        
        # Create session
        response = manager.create_session(sample_request)
        session_id = response.session_id
        room_id = response.negotiation_rooms[0].room_id
        seller_id = response.seller_ids[0]  # Get actual seller ID
        
        # Start negotiation
        run_info = manager.start_negotiation(room_id)
        run_id = run_info["run_id"]
        
        # Record messages
        msg1 = manager.record_message(
            run_id=run_id,
            turn_number=1,
            sender_type="buyer",
            sender_id=response.buyer_id,
            sender_name="Test Buyer",
            message_text="Hello, I'm looking for a laptop."
        )
        
        msg2 = manager.record_message(
            run_id=run_id,
            turn_number=2,
            sender_type="seller",
            sender_id=seller_id,
            sender_name="TechStore",
            message_text="I have a great laptop for you!"
        )
        
        # Record offer
        offer = manager.record_offer(
            message_id=msg2.id,
            seller_id=seller_id,
            price_per_unit=1000.0,
            quantity=2
        )
        
        # Finalize run
        outcome = manager.finalize_run(
            run_id=run_id,
            decision_type="deal",
            selected_seller_id=seller_id,
            final_price_per_unit=1000.0,
            quantity=2,
            decision_reason="Good price"
        )
        
        # Verify log file exists
        log_file = Path(settings.LOGS_DIR) / session_id / run_id / f"{run_id}.json"
        assert log_file.exists(), f"Log file not found at {log_file}"
    
    def test_log_schema_structure(self, db_session, sample_request):
        """Test that log file has correct schema structure."""
        manager = SessionManager()
        
        # Create session and run
        response = manager.create_session(sample_request)
        session_id = response.session_id
        room_id = response.negotiation_rooms[0].room_id
        seller_id = response.seller_ids[0]
        
        run_info = manager.start_negotiation(room_id)
        run_id = run_info["run_id"]
        
        # Record messages and offers
        msg1 = manager.record_message(
            run_id=run_id,
            turn_number=1,
            sender_type="buyer",
            sender_id=response.buyer_id,
            sender_name="Test Buyer",
            message_text="Hello",
            mentioned_agents=[seller_id]
        )
        
        msg2 = manager.record_message(
            run_id=run_id,
            turn_number=2,
            sender_type="seller",
            sender_id=seller_id,
            sender_name="TechStore",
            message_text="Hi there"
        )
        
        offer = manager.record_offer(
            message_id=msg2.id,
            seller_id=seller_id,
            price_per_unit=1000.0,
            quantity=2
        )
        
        # Finalize
        manager.finalize_run(
            run_id=run_id,
            decision_type="deal",
            selected_seller_id=seller_id,
            final_price_per_unit=1000.0,
            quantity=2
        )
        
        # Load and verify log
        log_file = Path(settings.LOGS_DIR) / session_id / run_id / f"{run_id}.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        # Verify required top-level keys
        assert "metadata" in log_data
        assert "buyer" in log_data
        assert "sellers" in log_data
        assert "conversation_history" in log_data
        assert "offers_over_time" in log_data
        assert "decision" in log_data
        assert "duration" in log_data
        assert "rounds" in log_data
        
        # Verify metadata structure
        assert "session_id" in log_data["metadata"]
        assert "run_id" in log_data["metadata"]
        assert log_data["metadata"]["session_id"] == session_id
        assert log_data["metadata"]["run_id"] == run_id
        
        # Verify buyer structure
        assert "buyer_id" in log_data["buyer"]
        assert "buyer_name" in log_data["buyer"]
        assert "item_name" in log_data["buyer"]
        assert log_data["buyer"]["buyer_name"] == "Test Buyer"
        
        # Verify conversation history
        assert len(log_data["conversation_history"]) == 2
        assert log_data["conversation_history"][0]["sender_type"] == "buyer"
        assert log_data["conversation_history"][1]["sender_type"] == "seller"
        assert seller_id in log_data["conversation_history"][0]["mentioned_agents"]
        
        # Verify offers
        assert len(log_data["offers_over_time"]) == 1
        assert log_data["offers_over_time"][0]["price_per_unit"] == 1000.0
        assert log_data["offers_over_time"][0]["quantity"] == 2
        
        # Verify decision
        assert log_data["decision"]["decision_type"] == "deal"
        assert log_data["decision"]["selected_seller_id"] == seller_id
        assert log_data["decision"]["final_price"] == 1000.0
    
    def test_log_persists_after_session_deletion(self, db_session, sample_request):
        """Test that logs persist even after session is deleted."""
        manager = SessionManager()
        
        # Create session and run
        response = manager.create_session(sample_request)
        session_id = response.session_id
        room_id = response.negotiation_rooms[0].room_id
        
        run_info = manager.start_negotiation(room_id)
        run_id = run_info["run_id"]
        
        # Record message
        manager.record_message(
            run_id=run_id,
            turn_number=1,
            sender_type="buyer",
            sender_id=response.buyer_id,
            sender_name="Test Buyer",
            message_text="Hello"
        )
        
        # Finalize
        manager.finalize_run(
            run_id=run_id,
            decision_type="no_deal"
        )
        
        # Verify log exists
        log_file = Path(settings.LOGS_DIR) / session_id / run_id / f"{run_id}.json"
        assert log_file.exists()
        
        # Delete session
        manager.delete_session(session_id)
        
        # Verify log still exists
        assert log_file.exists(), "Log should persist after session deletion"
    
    def test_multiple_runs_generate_separate_logs(self, db_session, sample_request):
        """Test that multiple runs generate separate log files."""
        manager = SessionManager()
        
        # Create session with multiple items
        request = InitializeSessionRequest(
            buyer=BuyerConfig(
                name="Test Buyer",
                shopping_list=[
                    ShoppingItem(
                        item_id="laptop",
                        item_name="Gaming Laptop",
                        quantity_needed=1,
                        min_price_per_unit=800.0,
                        max_price_per_unit=1200.0
                    ),
                    ShoppingItem(
                        item_id="mouse",
                        item_name="Gaming Mouse",
                        quantity_needed=2,
                        min_price_per_unit=20.0,
                        max_price_per_unit=50.0
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
                        ),
                        InventoryItem(
                            item_id="mouse",
                            item_name="Gaming Mouse",
                            cost_price=15.0,
                            selling_price=40.0,
                            least_price=25.0,
                            quantity_available=10
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
        
        response = manager.create_session(request)
        session_id = response.session_id
        
        # Start and finalize first run
        seller_id = response.seller_ids[0]
        run1_id = manager.start_negotiation(response.negotiation_rooms[0].room_id)["run_id"]
        manager.record_message(
            run_id=run1_id,
            turn_number=1,
            sender_type="buyer",
            sender_id=response.buyer_id,
            sender_name="Test Buyer",
            message_text="Hello"
        )
        manager.finalize_run(run1_id, decision_type="deal", selected_seller_id=seller_id, final_price_per_unit=1000.0, quantity=1)
        
        # Start and finalize second run
        run2_id = manager.start_negotiation(response.negotiation_rooms[1].room_id)["run_id"]
        manager.record_message(
            run_id=run2_id,
            turn_number=1,
            sender_type="buyer",
            sender_id=response.buyer_id,
            sender_name="Test Buyer",
            message_text="Hello"
        )
        manager.finalize_run(run2_id, decision_type="no_deal")
        
        # Verify both logs exist
        log1 = Path(settings.LOGS_DIR) / session_id / run1_id / f"{run1_id}.json"
        log2 = Path(settings.LOGS_DIR) / session_id / run2_id / f"{run2_id}.json"
        
        assert log1.exists(), f"Log 1 not found at {log1}"
        assert log2.exists(), f"Log 2 not found at {log2}"
        
        # Verify they are different files
        assert log1 != log2
    
    def test_log_includes_all_messages(self, db_session, sample_request):
        """Test that log includes all recorded messages."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Record multiple messages
        seller_id = response.seller_ids[0]
        messages = []
        for i in range(5):
            msg = manager.record_message(
                run_id=run_id,
                turn_number=i + 1,
                sender_type="buyer" if i % 2 == 0 else "seller",
                sender_id=response.buyer_id if i % 2 == 0 else seller_id,
                sender_name="Test Buyer" if i % 2 == 0 else "TechStore",
                message_text=f"Message {i + 1}"
            )
            messages.append(msg)
        
        manager.finalize_run(run_id, decision_type="no_deal")
        
        # Verify log contains all messages
        log_file = Path(settings.LOGS_DIR) / response.session_id / run_id / f"{run_id}.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        assert len(log_data["conversation_history"]) == 5
        for i, msg in enumerate(log_data["conversation_history"]):
            assert msg["turn_number"] == i + 1
            assert msg["content"] == f"Message {i + 1}"
    
    def test_log_includes_all_offers(self, db_session, sample_request):
        """Test that log includes all recorded offers."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Record messages with offers
        seller_id = response.seller_ids[0]
        offers = []
        for i in range(3):
            msg = manager.record_message(
                run_id=run_id,
                turn_number=i + 1,
                sender_type="seller",
                sender_id=seller_id,
                sender_name="TechStore",
                message_text=f"Offer {i + 1}"
            )
            offer = manager.record_offer(
                message_id=msg.id,
                seller_id=seller_id,
                price_per_unit=1000.0 + i * 10,
                quantity=2
            )
            offers.append(offer)
        
        manager.finalize_run(run_id, decision_type="deal", selected_seller_id=seller_id, final_price_per_unit=1020.0, quantity=2)
        
        # Verify log contains all offers
        log_file = Path(settings.LOGS_DIR) / response.session_id / run_id / f"{run_id}.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        assert len(log_data["offers_over_time"]) == 3
        for i, offer in enumerate(log_data["offers_over_time"]):
            assert offer["price_per_unit"] == 1000.0 + i * 10
            assert offer["quantity"] == 2
    
    def test_log_no_deal_decision(self, db_session, sample_request):
        """Test log structure for no_deal decision."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        manager.record_message(
            run_id=run_id,
            turn_number=1,
            sender_type="buyer",
            sender_id=response.buyer_id,
            sender_name="Test Buyer",
            message_text="Hello"
        )
        
        manager.finalize_run(
            run_id=run_id,
            decision_type="no_deal",
            decision_reason="No acceptable offers"
        )
        
        # Verify log
        log_file = Path(settings.LOGS_DIR) / response.session_id / run_id / f"{run_id}.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        assert log_data["decision"]["decision_type"] == "no_deal"
        assert log_data["decision"]["selected_seller_id"] is None
        assert log_data["decision"]["final_price"] is None
        assert log_data["decision"]["reason"] == "No acceptable offers"
    
    def test_log_duration_calculation(self, db_session, sample_request):
        """Test that log includes correct duration calculation."""
        import time
        
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Wait a bit
        time.sleep(0.1)
        
        manager.finalize_run(run_id, decision_type="no_deal")
        
        # Verify log
        log_file = Path(settings.LOGS_DIR) / response.session_id / run_id / f"{run_id}.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        assert log_data["duration"] is not None
        assert log_data["duration"] >= 0.1  # Should be at least 0.1 seconds

