"""
Cache and TTL tests for Phase 3.

WHAT: Test in-memory cache behavior for active rooms
WHY: Ensure cache stores, expires, and invalidates correctly
HOW: Test cache storage, TTL expiry, invalidation on delete
"""

import pytest
import uuid
import time
from datetime import datetime, timedelta
from app.core.database import get_db, init_db, Base, engine
from app.core.session_manager import SessionManager, active_rooms
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
def clear_cache():
    """Clear cache before and after each test."""
    active_rooms.clear()
    yield
    active_rooms.clear()


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


class TestCacheStorage:
    """Test cache storage behavior."""
    
    def test_cache_stores_room_on_start(self, db_session, sample_request):
        """Test that cache stores room state when negotiation starts."""
        manager = SessionManager()
        
        # Create session
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        # Start negotiation
        run_info = manager.start_negotiation(room_id)
        run_id = run_info["run_id"]
        
        # Verify room is in cache
        assert run_id in active_rooms, "Room should be in cache after start"
        
        room_state, created_at = active_rooms[run_id]
        assert room_state is not None, "Room state should be stored"
        assert isinstance(created_at, datetime), "Created timestamp should be datetime"
    
    def test_cache_stores_multiple_rooms(self, db_session, sample_request):
        """Test that cache can store multiple rooms."""
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
        
        # Start multiple negotiations
        run1_id = manager.start_negotiation(response.negotiation_rooms[0].room_id)["run_id"]
        run2_id = manager.start_negotiation(response.negotiation_rooms[1].room_id)["run_id"]
        
        # Verify both rooms are in cache
        assert run1_id in active_rooms, "Room 1 should be in cache"
        assert run2_id in active_rooms, "Room 2 should be in cache"
        assert len(active_rooms) == 2, "Cache should contain 2 rooms"


class TestCacheInvalidation:
    """Test cache invalidation behavior."""
    
    def test_cache_removed_on_finalize(self, db_session, sample_request):
        """Test that cache entry is removed when run is finalized."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Verify room is in cache
        assert run_id in active_rooms, "Room should be in cache"
        
        # Finalize run
        manager.finalize_run(run_id, decision_type="no_deal")
        
        # Verify room is removed from cache
        assert run_id not in active_rooms, "Room should be removed from cache after finalize"
    
    def test_cache_removed_on_session_delete(self, db_session, sample_request):
        """Test that cache entries are removed when session is deleted."""
        manager = SessionManager()
        
        # Create session with multiple rooms
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
        
        # Start negotiations
        run1_id = manager.start_negotiation(response.negotiation_rooms[0].room_id)["run_id"]
        run2_id = manager.start_negotiation(response.negotiation_rooms[1].room_id)["run_id"]
        
        # Verify rooms are in cache
        assert run1_id in active_rooms
        assert run2_id in active_rooms
        
        # Delete session
        manager.delete_session(session_id)
        
        # Verify rooms are removed from cache
        assert run1_id not in active_rooms, "Room 1 should be removed from cache"
        assert run2_id not in active_rooms, "Room 2 should be removed from cache"


class TestCacheTTL:
    """Test cache TTL and expiration."""
    
    def test_cache_cleanup_expired_rooms(self, db_session, sample_request):
        """Test that expired rooms are cleaned up."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Manually set old timestamp to simulate expiration
        old_time = datetime.now() - timedelta(hours=settings.SESSION_CLEANUP_HOURS + 1)
        active_rooms[run_id] = (active_rooms[run_id][0], old_time)
        
        # Run cleanup
        manager._cleanup_expired_rooms()
        
        # Verify expired room is removed
        assert run_id not in active_rooms, "Expired room should be removed"
    
    def test_cache_retains_recent_rooms(self, db_session, sample_request):
        """Test that recent rooms are retained."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Room should have recent timestamp (default)
        assert run_id in active_rooms, "Room should be in cache"
        
        # Run cleanup
        manager._cleanup_expired_rooms()
        
        # Verify recent room is retained
        assert run_id in active_rooms, "Recent room should be retained"
    
    def test_cache_cleanup_multiple_expired(self, db_session, sample_request):
        """Test cleanup of multiple expired rooms."""
        manager = SessionManager()
        
        # Create multiple sessions
        response1 = manager.create_session(sample_request)
        run1_id = manager.start_negotiation(response1.negotiation_rooms[0].room_id)["run_id"]
        
        response2 = manager.create_session(sample_request)
        run2_id = manager.start_negotiation(response2.negotiation_rooms[0].room_id)["run_id"]
        
        response3 = manager.create_session(sample_request)
        run3_id = manager.start_negotiation(response3.negotiation_rooms[0].room_id)["run_id"]
        
        # Make first two expired
        old_time = datetime.now() - timedelta(hours=settings.SESSION_CLEANUP_HOURS + 1)
        active_rooms[run1_id] = (active_rooms[run1_id][0], old_time)
        active_rooms[run2_id] = (active_rooms[run2_id][0], old_time)
        
        # Run cleanup
        manager._cleanup_expired_rooms()
        
        # Verify expired rooms are removed
        assert run1_id not in active_rooms, "Expired room 1 should be removed"
        assert run2_id not in active_rooms, "Expired room 2 should be removed"
        
        # Verify recent room is retained
        assert run3_id in active_rooms, "Recent room should be retained"
    
    def test_cache_cleanup_exact_boundary(self, db_session, sample_request):
        """Test cleanup at exact TTL boundary."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Set timestamp exactly at TTL boundary
        boundary_time = datetime.now() - timedelta(hours=settings.SESSION_CLEANUP_HOURS)
        active_rooms[run_id] = (active_rooms[run_id][0], boundary_time)
        
        # Run cleanup
        manager._cleanup_expired_rooms()
        
        # Room should be removed (age >= TTL)
        assert run_id not in active_rooms, "Room at boundary should be removed"


class TestCacheHitMiss:
    """Test cache hit/miss scenarios."""
    
    def test_cache_hit_after_start(self, db_session, sample_request):
        """Test cache hit after negotiation starts."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Cache hit
        assert run_id in active_rooms, "Cache hit: room should be accessible"
        room_state, _ = active_rooms[run_id]
        assert room_state.room_id == run_id, "Cache hit: correct room state"
    
    def test_cache_miss_after_finalize(self, db_session, sample_request):
        """Test cache miss after negotiation is finalized."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Finalize
        manager.finalize_run(run_id, decision_type="no_deal")
        
        # Cache miss
        assert run_id not in active_rooms, "Cache miss: room should not be in cache"
    
    def test_cache_miss_after_delete(self, db_session, sample_request):
        """Test cache miss after session deletion."""
        manager = SessionManager()
        
        response = manager.create_session(sample_request)
        session_id = response.session_id
        room_id = response.negotiation_rooms[0].room_id
        
        run_id = manager.start_negotiation(room_id)["run_id"]
        
        # Delete session
        manager.delete_session(session_id)
        
        # Cache miss
        assert run_id not in active_rooms, "Cache miss: room should not be in cache"

