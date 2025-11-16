"""
Database stress test for Phase 3.

WHAT: Test SQLite stability under concurrent load
WHY: Verify WAL mode performance and lock contention handling on Windows ARM
HOW: Create multiple sessions/runs concurrently, measure latency, check for errors
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import init_db, Base, engine, get_db
from app.core.session_manager import SessionManager
from app.core.models import Session, NegotiationRun, Message, Offer
from app.models.api_schemas import (
    InitializeSessionRequest, BuyerConfig, ShoppingItem,
    SellerConfig, InventoryItem, SellerProfile, LLMConfig
)


class StressTestStats:
    """Statistics collector for stress test."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.session_times = []
        self.run_times = []
        self.message_times = []
        self.errors = []
        self.session_count = 0
        self.run_count = 0
        self.message_count = 0
    
    def add_session_time(self, duration):
        """Add session creation time."""
        with self.lock:
            self.session_times.append(duration)
            self.session_count += 1
    
    def add_run_time(self, duration):
        """Add run creation time."""
        with self.lock:
            self.run_times.append(duration)
            self.run_count += 1
    
    def add_message_time(self, duration):
        """Add message insertion time."""
        with self.lock:
            self.message_times.append(duration)
            self.message_count += 1
    
    def add_error(self, error):
        """Add error."""
        with self.lock:
            self.errors.append(error)
    
    def get_stats(self):
        """Get statistics summary."""
        with self.lock:
            return {
                'sessions': {
                    'count': self.session_count,
                    'avg_time': sum(self.session_times) / len(self.session_times) if self.session_times else 0,
                    'max_time': max(self.session_times) if self.session_times else 0,
                    'min_time': min(self.session_times) if self.session_times else 0
                },
                'runs': {
                    'count': self.run_count,
                    'avg_time': sum(self.run_times) / len(self.run_times) if self.run_times else 0,
                    'max_time': max(self.run_times) if self.run_times else 0,
                    'min_time': min(self.run_times) if self.run_times else 0
                },
                'messages': {
                    'count': self.message_count,
                    'avg_time': sum(self.message_times) / len(self.message_times) if self.message_times else 0,
                    'max_time': max(self.message_times) if self.message_times else 0,
                    'min_time': min(self.message_times) if self.message_times else 0
                },
                'errors': len(self.errors),
                'error_list': self.errors[:10]  # First 10 errors
            }


def create_session_worker(worker_id, stats, num_sessions_per_worker):
    """Worker function to create sessions."""
    manager = SessionManager()
    
    request = InitializeSessionRequest(
        buyer=BuyerConfig(
            name=f"Buyer-{worker_id}",
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
                name=f"Seller-{worker_id}",
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
    
    session_ids = []
    for i in range(num_sessions_per_worker):
        try:
            start = time.time()
            response = manager.create_session(request)
            duration = time.time() - start
            stats.add_session_time(duration)
            session_ids.append(response.session_id)
        except Exception as e:
            stats.add_error(f"Worker {worker_id}, Session {i}: {str(e)}")
    
    return session_ids


def create_runs_worker(manager, session_id, room_id, stats, num_runs):
    """Worker function to create runs and insert messages."""
    run_ids = []
    
    for i in range(num_runs):
        try:
            # Create run
            start = time.time()
            run_info = manager.start_negotiation(room_id)
            duration = time.time() - start
            stats.add_run_time(duration)
            run_id = run_info["run_id"]
            run_ids.append(run_id)
            
            # Insert messages rapidly
            for turn in range(1, 11):
                msg_start = time.time()
                manager.record_message(
                    run_id=run_id,
                    turn_number=turn,
                    sender_type="buyer" if turn % 2 == 1 else "seller",
                    sender_id="buyer1" if turn % 2 == 1 else "seller1",
                    sender_name="Buyer" if turn % 2 == 1 else "Seller",
                    message_text=f"Message {turn}"
                )
                msg_duration = time.time() - msg_start
                stats.add_message_time(msg_duration)
        
        except Exception as e:
            stats.add_error(f"Run {i} in session {session_id}: {str(e)}")
    
    return run_ids


def main():
    """Run database stress test."""
    print("=" * 80)
    print("  Database Stress Test - Phase 3")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}\n")
    
    # Initialize database
    print("[Setup] Initializing database...")
    Base.metadata.drop_all(bind=engine)
    init_db()
    print("  [OK] Database initialized\n")
    
    stats = StressTestStats()
    manager = SessionManager()
    
    # Test parameters
    NUM_WORKERS = 10
    SESSIONS_PER_WORKER = 5
    TOTAL_SESSIONS = NUM_WORKERS * SESSIONS_PER_WORKER
    RUNS_PER_SESSION = 10
    TOTAL_RUNS = TOTAL_SESSIONS * RUNS_PER_SESSION
    MESSAGES_PER_RUN = 10
    TOTAL_MESSAGES = TOTAL_RUNS * MESSAGES_PER_RUN
    
    print(f"Test Parameters:")
    print(f"  Workers: {NUM_WORKERS}")
    print(f"  Sessions per worker: {SESSIONS_PER_WORKER}")
    print(f"  Total sessions: {TOTAL_SESSIONS}")
    print(f"  Runs per session: {RUNS_PER_SESSION}")
    print(f"  Total runs: {TOTAL_RUNS}")
    print(f"  Messages per run: {MESSAGES_PER_RUN}")
    print(f"  Total messages: {TOTAL_MESSAGES}")
    print()
    
    # Phase 1: Create sessions concurrently
    print("[Phase 1] Creating sessions concurrently...")
    start_time = time.time()
    
    session_ids_by_worker = []
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [
            executor.submit(create_session_worker, i, stats, SESSIONS_PER_WORKER)
            for i in range(NUM_WORKERS)
        ]
        
        for future in as_completed(futures):
            try:
                session_ids = future.result()
                session_ids_by_worker.extend(session_ids)
            except Exception as e:
                stats.add_error(f"Session creation error: {str(e)}")
    
    phase1_duration = time.time() - start_time
    print(f"  [OK] Created {len(session_ids_by_worker)} sessions in {phase1_duration:.2f}s")
    print(f"  [OK] Rate: {len(session_ids_by_worker) / phase1_duration:.2f} sessions/sec\n")
    
    # Phase 2: Create runs and insert messages concurrently
    print("[Phase 2] Creating runs and inserting messages concurrently...")
    start_time = time.time()
    
    # Get room IDs for each session
    room_ids = []
    for session_id in session_ids_by_worker:
        try:
            session_data = manager.get_session(session_id)
            if session_data.get('rooms'):
                room_ids.append((session_id, session_data['rooms'][0]['room_id']))
        except Exception as e:
            stats.add_error(f"Failed to get room for session {session_id}: {str(e)}")
    
    # Create runs and messages concurrently
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(create_runs_worker, manager, session_id, room_id, stats, RUNS_PER_SESSION)
            for session_id, room_id in room_ids
        ]
        
        for future in as_completed(futures):
            try:
                run_ids = future.result()
            except Exception as e:
                stats.add_error(f"Run creation error: {str(e)}")
    
    phase2_duration = time.time() - start_time
    print(f"  [OK] Created runs and messages in {phase2_duration:.2f}s")
    print(f"  [OK] Rate: {stats.run_count / phase2_duration:.2f} runs/sec")
    print(f"  [OK] Rate: {stats.message_count / phase2_duration:.2f} messages/sec\n")
    
    # Verify database state
    print("[Verification] Verifying database state...")
    with get_db() as db:
        db_session_count = db.query(Session).count()
        db_run_count = db.query(NegotiationRun).count()
        db_message_count = db.query(Message).count()
        
        print(f"  Database Sessions: {db_session_count} (expected: ~{TOTAL_SESSIONS})")
        print(f"  Database Runs: {db_run_count} (expected: ~{TOTAL_RUNS})")
        print(f"  Database Messages: {db_message_count} (expected: ~{TOTAL_MESSAGES})")
        
        # Allow some tolerance for errors
        assert db_session_count >= TOTAL_SESSIONS * 0.9, f"Session count too low: {db_session_count}"
        assert db_run_count >= TOTAL_RUNS * 0.9, f"Run count too low: {db_run_count}"
        assert db_message_count >= TOTAL_MESSAGES * 0.9, f"Message count too low: {db_message_count}"
        print("  [OK] Database state verified\n")
    
    # Print statistics
    print("[Statistics] Performance Metrics:")
    print("=" * 80)
    
    result_stats = stats.get_stats()
    
    print(f"\nSession Creation:")
    print(f"  Count: {result_stats['sessions']['count']}")
    print(f"  Avg Latency: {result_stats['sessions']['avg_time']*1000:.2f}ms")
    print(f"  Min Latency: {result_stats['sessions']['min_time']*1000:.2f}ms")
    print(f"  Max Latency: {result_stats['sessions']['max_time']*1000:.2f}ms")
    
    print(f"\nRun Creation:")
    print(f"  Count: {result_stats['runs']['count']}")
    print(f"  Avg Latency: {result_stats['runs']['avg_time']*1000:.2f}ms")
    print(f"  Min Latency: {result_stats['runs']['min_time']*1000:.2f}ms")
    print(f"  Max Latency: {result_stats['runs']['max_time']*1000:.2f}ms")
    
    print(f"\nMessage Insertion:")
    print(f"  Count: {result_stats['messages']['count']}")
    print(f"  Avg Latency: {result_stats['messages']['avg_time']*1000:.2f}ms")
    print(f"  Min Latency: {result_stats['messages']['min_time']*1000:.2f}ms")
    print(f"  Max Latency: {result_stats['messages']['max_time']*1000:.2f}ms")
    
    print(f"\nErrors: {result_stats['errors']}")
    if result_stats['errors'] > 0:
        print("  First 10 errors:")
        for error in result_stats['error_list']:
            print(f"    - {error}")
    
    # Check for lock contention (high max latency)
    print("\n[Analysis] Lock Contention Check:")
    max_message_latency_ms = result_stats['messages']['max_time'] * 1000
    avg_message_latency_ms = result_stats['messages']['avg_time'] * 1000
    
    if max_message_latency_ms > 1000:
        print(f"  ⚠ Warning: High max latency ({max_message_latency_ms:.2f}ms) may indicate lock contention")
    else:
        print(f"  [OK] Max latency ({max_message_latency_ms:.2f}ms) is acceptable")
    
    if avg_message_latency_ms > 100:
        print(f"  ⚠ Warning: High avg latency ({avg_message_latency_ms:.2f}ms)")
    else:
        print(f"  [OK] Avg latency ({avg_message_latency_ms:.2f}ms) is acceptable")
    
    # Final summary
    print("\n" + "=" * 80)
    print("  Stress Test Complete")
    print("=" * 80)
    print(f"Completed at: {datetime.now().isoformat()}")
    print(f"Total Duration: {phase1_duration + phase2_duration:.2f}s")
    print(f"Total Operations: {result_stats['sessions']['count'] + result_stats['runs']['count'] + result_stats['messages']['count']}")
    
    if result_stats['errors'] == 0:
        print("\n[OK] No errors detected")
        print("[OK] Database stress test: PASSED")
    else:
        print(f"\n⚠ {result_stats['errors']} errors detected")
        print("⚠ Database stress test: PASSED WITH ERRORS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

