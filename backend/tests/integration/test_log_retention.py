"""
Log retention and cleanup tests for Phase 3.

WHAT: Test log cleanup policy based on retention period
WHY: Ensure old logs are deleted while recent logs are retained
HOW: Create logs with old timestamps, call cleanup_old_logs(), verify deletion
"""

import pytest
import json
import uuid
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
from app.core.database import get_db, init_db, Base, engine
from app.core.session_manager import SessionManager
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


@pytest.fixture(autouse=True)
def cleanup_logs():
    """Clean up logs before and after each test."""
    log_dir = Path(settings.LOGS_DIR)
    if log_dir.exists():
        shutil.rmtree(log_dir)
    yield
    if log_dir.exists():
        shutil.rmtree(log_dir)


def create_log_file(session_id: str, run_id: str, age_days: int):
    """Create a log file with specified age."""
    log_dir = Path(settings.LOGS_DIR) / session_id / run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{run_id}.json"
    log_data = {
        "metadata": {
            "session_id": session_id,
            "run_id": run_id,
            "created_at": (datetime.now() - timedelta(days=age_days)).isoformat()
        },
        "buyer": {},
        "sellers": [],
        "conversation_history": [],
        "offers_over_time": [],
        "decision": None,
        "duration": None,
        "rounds": 0
    }
    
    with open(log_file, 'w') as f:
        json.dump(log_data, f)
    
    # Set modification time to simulate old file
    old_time = (datetime.now() - timedelta(days=age_days)).timestamp()
    log_file.touch()
    import os
    os.utime(log_file, (old_time, old_time))
    os.utime(log_dir, (old_time, old_time))
    os.utime(log_dir.parent, (old_time, old_time))
    
    return log_file


class TestLogRetention:
    """Test log retention and cleanup."""
    
    def test_cleanup_deletes_old_logs(self, db_session):
        """Test that old logs are deleted during cleanup."""
        # Create old log (older than retention period)
        old_session_id = str(uuid.uuid4())
        old_run_id = str(uuid.uuid4())
        old_log = create_log_file(old_session_id, old_run_id, age_days=settings.LOG_RETENTION_DAYS + 1)
        
        assert old_log.exists(), "Old log should exist before cleanup"
        
        # Run cleanup
        SessionManager.cleanup_old_logs()
        
        # Verify old log is deleted
        assert not old_log.exists(), "Old log should be deleted"
        assert not old_log.parent.exists(), "Old log directory should be deleted"
    
    def test_cleanup_retains_recent_logs(self, db_session):
        """Test that recent logs are retained during cleanup."""
        # Create recent log (within retention period)
        recent_session_id = str(uuid.uuid4())
        recent_run_id = str(uuid.uuid4())
        recent_log = create_log_file(recent_session_id, recent_run_id, age_days=settings.LOG_RETENTION_DAYS - 1)
        
        assert recent_log.exists(), "Recent log should exist before cleanup"
        
        # Run cleanup
        SessionManager.cleanup_old_logs()
        
        # Verify recent log is retained
        assert recent_log.exists(), "Recent log should be retained"
    
    def test_cleanup_mixed_old_and_recent(self, db_session):
        """Test cleanup with mix of old and recent logs."""
        # Create old logs
        old_session1 = str(uuid.uuid4())
        old_run1 = str(uuid.uuid4())
        old_log1 = create_log_file(old_session1, old_run1, age_days=settings.LOG_RETENTION_DAYS + 5)
        
        old_session2 = str(uuid.uuid4())
        old_run2 = str(uuid.uuid4())
        old_log2 = create_log_file(old_session2, old_run2, age_days=settings.LOG_RETENTION_DAYS + 10)
        
        # Create recent logs
        recent_session1 = str(uuid.uuid4())
        recent_run1 = str(uuid.uuid4())
        recent_log1 = create_log_file(recent_session1, recent_run1, age_days=1)
        
        recent_session2 = str(uuid.uuid4())
        recent_run2 = str(uuid.uuid4())
        recent_log2 = create_log_file(recent_session2, recent_run2, age_days=settings.LOG_RETENTION_DAYS - 1)
        
        # Run cleanup
        SessionManager.cleanup_old_logs()
        
        # Verify old logs are deleted
        assert not old_log1.exists(), "Old log 1 should be deleted"
        assert not old_log2.exists(), "Old log 2 should be deleted"
        
        # Verify recent logs are retained
        assert recent_log1.exists(), "Recent log 1 should be retained"
        assert recent_log2.exists(), "Recent log 2 should be retained"
    
    def test_cleanup_empty_logs_directory(self, db_session):
        """Test cleanup with empty logs directory."""
        log_dir = Path(settings.LOGS_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Should not raise error
        SessionManager.cleanup_old_logs()
        
        # Directory should still exist
        assert log_dir.exists()
    
    def test_cleanup_missing_session_folders(self, db_session):
        """Test cleanup handles missing session folders gracefully."""
        log_dir = Path(settings.LOGS_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a file (not a directory) in logs directory
        test_file = log_dir / "test_file.txt"
        test_file.write_text("test")
        
        # Should not raise error
        SessionManager.cleanup_old_logs()
    
    def test_cleanup_exact_retention_boundary(self, db_session):
        """Test cleanup at exact retention boundary."""
        # Create log exactly at retention boundary
        boundary_session_id = str(uuid.uuid4())
        boundary_run_id = str(uuid.uuid4())
        
        # Create log with age exactly at retention period
        log_dir = Path(settings.LOGS_DIR) / boundary_session_id / boundary_run_id
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{boundary_run_id}.json"
        log_data = {"metadata": {}, "buyer": {}, "sellers": [], "conversation_history": [], "offers_over_time": [], "decision": None, "duration": None, "rounds": 0}
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f)
        
        # Set modification time to exactly retention period ago
        boundary_time = (datetime.now() - timedelta(days=settings.LOG_RETENTION_DAYS)).timestamp()
        import os
        os.utime(log_file, (boundary_time, boundary_time))
        os.utime(log_dir, (boundary_time, boundary_time))
        os.utime(log_dir.parent, (boundary_time, boundary_time))
        
        # Run cleanup
        SessionManager.cleanup_old_logs()
        
        # Log should be deleted (age >= retention period)
        assert not log_file.exists(), "Log at boundary should be deleted"
    
    def test_cleanup_nested_run_directories(self, db_session):
        """Test cleanup of nested run directories."""
        session_id = str(uuid.uuid4())
        
        # Create multiple runs in same session
        old_run1 = str(uuid.uuid4())
        old_log1 = create_log_file(session_id, old_run1, age_days=settings.LOG_RETENTION_DAYS + 1)
        
        old_run2 = str(uuid.uuid4())
        old_log2 = create_log_file(session_id, old_run2, age_days=settings.LOG_RETENTION_DAYS + 2)
        
        recent_run = str(uuid.uuid4())
        recent_log = create_log_file(session_id, recent_run, age_days=1)
        
        # Run cleanup
        SessionManager.cleanup_old_logs()
        
        # Old runs should be deleted
        assert not old_log1.exists(), "Old run 1 should be deleted"
        assert not old_log2.exists(), "Old run 2 should be deleted"
        
        # Recent run should be retained
        assert recent_log.exists(), "Recent run should be retained"
        
        # Session directory should still exist (has recent run)
        assert (Path(settings.LOGS_DIR) / session_id).exists()
    
    def test_cleanup_deletes_entire_session_if_all_runs_old(self, db_session):
        """Test that entire session directory is deleted if all runs are old."""
        session_id = str(uuid.uuid4())
        
        # Create only old runs
        old_run1 = str(uuid.uuid4())
        old_log1 = create_log_file(session_id, old_run1, age_days=settings.LOG_RETENTION_DAYS + 1)
        
        old_run2 = str(uuid.uuid4())
        old_log2 = create_log_file(session_id, old_run2, age_days=settings.LOG_RETENTION_DAYS + 2)
        
        session_dir = Path(settings.LOGS_DIR) / session_id
        assert session_dir.exists(), "Session directory should exist before cleanup"
        
        # Run cleanup
        SessionManager.cleanup_old_logs()
        
        # Session directory should be deleted
        assert not session_dir.exists(), "Session directory should be deleted when all runs are old"
    
    def test_cleanup_with_real_session_manager(self, db_session):
        """Test cleanup with real session manager workflow."""
        manager = SessionManager()
        
        # Create a session and finalize it
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
        
        response = manager.create_session(request)
        session_id = response.session_id
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        manager.record_message(
            run_id=run_id,
            turn_number=1,
            sender_type="buyer",
            sender_id="buyer1",
            sender_name="Test Buyer",
            message_text="Hello"
        )
        manager.finalize_run(run_id, decision_type="no_deal")
        
        # Verify log exists
        log_file = Path(settings.LOGS_DIR) / session_id / run_id / f"{run_id}.json"
        assert log_file.exists()
        
        # Make log old
        old_time = (datetime.now() - timedelta(days=settings.LOG_RETENTION_DAYS + 1)).timestamp()
        import os
        os.utime(log_file, (old_time, old_time))
        os.utime(log_file.parent, (old_time, old_time))
        os.utime(log_file.parent.parent, (old_time, old_time))
        
        # Run cleanup
        SessionManager.cleanup_old_logs()
        
        # Verify log is deleted
        assert not log_file.exists(), "Log should be deleted after cleanup"

