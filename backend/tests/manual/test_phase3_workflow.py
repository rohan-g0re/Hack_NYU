"""
Manual Phase 3 workflow verification script.

WHAT: End-to-end verification of Phase 3 components
WHY: Validate complete workflow from session creation to finalization
HOW: Create session → start runs → record messages/offers → finalize → verify DB and logs
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import init_db, Base, engine, get_db
from app.core.session_manager import SessionManager
from app.core.models import (
    Session, Buyer, BuyerItem, Seller, SellerInventory,
    NegotiationRun, NegotiationParticipant, Message, Offer, NegotiationOutcome
)
from app.services.summary_service import compute_session_summary
from app.models.api_schemas import (
    InitializeSessionRequest, BuyerConfig, ShoppingItem,
    SellerConfig, InventoryItem, SellerProfile, LLMConfig
)
from app.core.config import settings


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_step(step_num, description):
    """Print a step header."""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 80)


def verify_db_counts(db, session_id, expected_counts):
    """Verify database record counts."""
    print("\nVerifying database counts...")
    
    session_count = db.query(Session).filter(Session.id == session_id).count()
    buyer_count = db.query(Buyer).filter(Buyer.session_id == session_id).count()
    buyer_item_count = db.query(BuyerItem).join(Buyer).filter(Buyer.session_id == session_id).count()
    seller_count = db.query(Seller).filter(Seller.session_id == session_id).count()
    run_count = db.query(NegotiationRun).filter(NegotiationRun.session_id == session_id).count()
    
    print(f"  Sessions: {session_count} (expected: {expected_counts.get('sessions', 0)})")
    print(f"  Buyers: {buyer_count} (expected: {expected_counts.get('buyers', 0)})")
    print(f"  Buyer Items: {buyer_item_count} (expected: {expected_counts.get('buyer_items', 0)})")
    print(f"  Sellers: {seller_count} (expected: {expected_counts.get('sellers', 0)})")
    print(f"  Negotiation Runs: {run_count} (expected: {expected_counts.get('runs', 0)})")
    
    assert session_count == expected_counts.get('sessions', 0), f"Session count mismatch"
    assert buyer_count == expected_counts.get('buyers', 0), f"Buyer count mismatch"
    assert buyer_item_count == expected_counts.get('buyer_items', 0), f"Buyer item count mismatch"
    assert seller_count == expected_counts.get('sellers', 0), f"Seller count mismatch"
    assert run_count == expected_counts.get('runs', 0), f"Run count mismatch"
    
    print("  [OK] All counts match!")


def main():
    """Run full workflow verification."""
    print_section("Phase 3 Workflow Verification")
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Initialize database
    print_step(0, "Initializing Database")
    Base.metadata.drop_all(bind=engine)
    init_db()
    print("  [OK] Database initialized")
    
    manager = SessionManager()
    
    # Step 1: Create session with 2 buyers, 3 sellers, mixed inventory
    print_step(1, "Creating Session with 2 Buyers, 3 Sellers")
    
    request = InitializeSessionRequest(
        buyer=BuyerConfig(
            name="Alice",
            shopping_list=[
                ShoppingItem(
                    item_id="laptop",
                    item_name="Gaming Laptop",
                    quantity_needed=2,
                    min_price_per_unit=800.0,
                    max_price_per_unit=1200.0
                ),
                ShoppingItem(
                    item_id="mouse",
                    item_name="Gaming Mouse",
                    quantity_needed=3,
                    min_price_per_unit=20.0,
                    max_price_per_unit=50.0
                ),
                ShoppingItem(
                    item_id="keyboard",
                    item_name="Mechanical Keyboard",
                    quantity_needed=1,
                    min_price_per_unit=50.0,
                    max_price_per_unit=150.0
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
            ),
            SellerConfig(
                name="ElectronicsHub",
                inventory=[
                    InventoryItem(
                        item_id="laptop",
                        item_name="Gaming Laptop",
                        cost_price=750.0,
                        selling_price=1150.0,
                        least_price=950.0,
                        quantity_available=3
                    ),
                    InventoryItem(
                        item_id="keyboard",
                        item_name="Mechanical Keyboard",
                        cost_price=40.0,
                        selling_price=120.0,
                        least_price=80.0,
                        quantity_available=8
                    )
                ],
                profile=SellerProfile(
                    priority="maximize_profit",
                    speaking_style="rude"
                )
            ),
            SellerConfig(
                name="GadgetWorld",
                inventory=[
                    InventoryItem(
                        item_id="mouse",
                        item_name="Gaming Mouse",
                        cost_price=18.0,
                        selling_price=45.0,
                        least_price=30.0,
                        quantity_available=15
                    ),
                    InventoryItem(
                        item_id="keyboard",
                        item_name="Mechanical Keyboard",
                        cost_price=45.0,
                        selling_price=130.0,
                        least_price=90.0,
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
    
    print(f"  [OK] Session created: {session_id}")
    print(f"  [OK] Rooms created: {len(response.negotiation_rooms)}")
    for i, room in enumerate(response.negotiation_rooms):
        print(f"    Room {i+1}: {room.room_id} - {room.item_name}")
    
    # Verify DB counts
    with get_db() as db:
        verify_db_counts(db, session_id, {
            'sessions': 1,
            'buyers': 1,
            'buyer_items': 3,
            'sellers': 3,
            'runs': 3  # Runs are created automatically for each buyer item
        })
    
    # Step 2: Start 3 negotiation runs (1 per buyer item)
    print_step(2, "Starting 3 Negotiation Runs")
    
    run_ids = []
    for i, room in enumerate(response.negotiation_rooms):
        run_info = manager.start_negotiation(room.room_id)
        run_id = run_info["run_id"]
        run_ids.append(run_id)
        print(f"  [OK] Started run {i+1}: {run_id} for {room.item_name}")
    
    # Verify DB counts (runs increase from 3 to 3 since we're starting existing runs)
    with get_db() as db:
        verify_db_counts(db, session_id, {
            'sessions': 1,
            'buyers': 1,
            'buyer_items': 3,
            'sellers': 3,
            'runs': 3  # Same 3 runs, just activated
        })
    
    # Step 3: Record messages and offers per run
    print_step(3, "Recording Messages and Offers")
    
    outcomes = {
        run_ids[0]: "deal",  # Laptop - success
        run_ids[1]: "no_deal",  # Mouse - no deal
        run_ids[2]: "deal"  # Keyboard - success
    }
    
    for run_idx, run_id in enumerate(run_ids):
        print(f"\n  Processing Run {run_idx + 1} ({run_ids[run_idx]})...")
        
        # Record 10 messages per run
        messages = []
        for turn in range(1, 11):
            sender_type = "buyer" if turn % 2 == 1 else "seller"
            seller_idx = (turn // 2) % len(response.seller_ids)
            sender_id = response.buyer_id if turn % 2 == 1 else response.seller_ids[seller_idx]
            seller_names = [s.seller_name for s in response.negotiation_rooms[run_idx].participating_sellers]
            sender_name = "Alice" if turn % 2 == 1 else seller_names[seller_idx % len(seller_names)] if seller_names else "Seller"
            content = f"Message {turn} from {sender_name}"
            
            msg = manager.record_message(
                run_id=run_id,
                turn_number=turn,
                sender_type=sender_type,
                sender_id=sender_id,
                sender_name=sender_name,
                message_text=content,
                mentioned_agents=[response.seller_ids[seller_idx]] if turn % 2 == 1 else None
            )
            messages.append(msg)
        
        print(f"    [OK] Recorded {len(messages)} messages")
        
        # Record 5 offers per run (from sellers)
        offers = []
        seller_ids = response.seller_ids
        for i in range(5):
            seller_idx = i % len(seller_ids)
            msg = messages[i * 2]  # Use every other message (seller messages)
            
            offer = manager.record_offer(
                message_id=msg.id,
                seller_id=seller_ids[seller_idx],
                price_per_unit=1000.0 - i * 10 if run_idx == 0 else 30.0 + i * 2 if run_idx == 1 else 100.0 + i * 5,
                quantity=2 if run_idx == 0 else 3 if run_idx == 1 else 1
            )
            offers.append(offer)
        
        print(f"    [OK] Recorded {len(offers)} offers")
    
    # Verify DB counts
    with get_db() as db:
        total_messages = db.query(Message).join(NegotiationRun).filter(NegotiationRun.session_id == session_id).count()
        total_offers = db.query(Offer).join(Message).join(NegotiationRun).filter(NegotiationRun.session_id == session_id).count()
        
        print(f"\n  Total Messages: {total_messages} (expected: 30)")
        print(f"  Total Offers: {total_offers} (expected: 15)")
        assert total_messages == 30, f"Message count mismatch: {total_messages}"
        assert total_offers == 15, f"Offer count mismatch: {total_offers}"
        print("  [OK] All messages and offers recorded")
    
    # Step 4: Finalize all runs with varied outcomes
    print_step(4, "Finalizing Negotiation Runs")
    
    final_outcomes = []
    for run_idx, run_id in enumerate(run_ids):
        decision_type = outcomes[run_id]
        
        if decision_type == "deal":
            seller_id = response.seller_ids[0]  # Use first seller
            outcome = manager.finalize_run(
                run_id=run_id,
                decision_type="deal",
                selected_seller_id=seller_id,
                final_price_per_unit=1000.0 - run_idx * 10 if run_idx == 0 else 100.0 + run_idx * 5,
                quantity=2 if run_idx == 0 else 1,
                decision_reason=f"Best price for {response.negotiation_rooms[run_idx].item_name}"
            )
        else:
            outcome = manager.finalize_run(
                run_id=run_id,
                decision_type="no_deal",
                decision_reason="No acceptable offers"
            )
        
        final_outcomes.append(outcome)
        print(f"  [OK] Finalized run {run_idx + 1}: {decision_type}")
    
    # Verify DB counts
    with get_db() as db:
        outcome_count = db.query(NegotiationOutcome).join(NegotiationRun).filter(NegotiationRun.session_id == session_id).count()
        print(f"\n  Total Outcomes: {outcome_count} (expected: 3)")
        assert outcome_count == 3, f"Outcome count mismatch: {outcome_count}"
        print("  [OK] All outcomes recorded")
    
    # Step 5: Verify session summary metrics
    print_step(5, "Verifying Session Summary Metrics")
    
    with get_db() as db:
        summary = compute_session_summary(db, session_id)
        
        print(f"\n  Session Summary:")
        print(f"    Total Runs: {summary['total_runs']}")
        print(f"    Successful Deals: {summary['successful_deals']}")
        print(f"    Failed Runs: {summary['failed_runs']}")
        success_rate = summary['successful_deals'] / summary['total_runs'] if summary['total_runs'] > 0 else 0.0
        print(f"    Success Rate: {success_rate:.2%}")
        print(f"    Total Cost: ${summary['total_cost']:.2f}")
        print(f"    Items Purchased: {summary['items_purchased']}")
        print(f"    Average Rounds: {summary['average_rounds']:.2f}")
        print(f"    Average Duration: {summary['average_duration_seconds']:.2f}s")
        
        assert summary['total_runs'] == 3, "Total runs mismatch"
        assert summary['successful_deals'] == 2, "Successful deals mismatch"
        assert summary['failed_runs'] == 0, "Failed runs mismatch (failed_runs counts runs with status 'no_sellers_available' or 'aborted', not completed runs with no_deal outcomes)"
        assert abs(success_rate - 2/3) < 0.01, "Success rate mismatch"
        print("  [OK] Summary metrics verified")
    
    # Step 6: Verify JSON logs generated
    print_step(6, "Verifying JSON Logs Generated")
    
    log_dir = Path(settings.LOGS_DIR) / session_id
    print(f"\n  Log directory: {log_dir}")
    
    for run_idx, run_id in enumerate(run_ids):
        log_file = log_dir / run_id / f"{run_id}.json"
        assert log_file.exists(), f"Log file not found: {log_file}"
        
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        print(f"\n  Run {run_idx + 1} log:")
        print(f"    File: {log_file}")
        print(f"    Messages: {len(log_data['conversation_history'])}")
        print(f"    Offers: {len(log_data['offers_over_time'])}")
        print(f"    Decision: {log_data['decision']['decision_type']}")
        
        assert len(log_data['conversation_history']) == 10, "Message count mismatch in log"
        assert len(log_data['offers_over_time']) == 5, "Offer count mismatch in log"
        assert log_data['decision']['decision_type'] == outcomes[run_id], "Decision mismatch in log"
        print(f"    [OK] Log verified")
    
    print("\n  [OK] All JSON logs verified")
    
    # Step 7: Delete session and verify CASCADE
    print_step(7, "Deleting Session and Verifying CASCADE")
    
    delete_result = manager.delete_session(session_id)
    print(f"  [OK] Session deleted")
    print(f"  [OK] Logs saved: {len(delete_result.get('logs_saved', []))} files")
    
    # Verify CASCADE delete
    with get_db() as db:
        session_count = db.query(Session).filter(Session.id == session_id).count()
        buyer_count = db.query(Buyer).filter(Buyer.session_id == session_id).count()
        run_count = db.query(NegotiationRun).filter(NegotiationRun.session_id == session_id).count()
        message_count = db.query(Message).join(NegotiationRun).filter(NegotiationRun.session_id == session_id).count()
        
        print(f"\n  After deletion:")
        print(f"    Sessions: {session_count} (expected: 0)")
        print(f"    Buyers: {buyer_count} (expected: 0)")
        print(f"    Runs: {run_count} (expected: 0)")
        print(f"    Messages: {message_count} (expected: 0)")
        
        assert session_count == 0, "Session not deleted"
        assert buyer_count == 0, "Buyers not CASCADE deleted"
        assert run_count == 0, "Runs not CASCADE deleted"
        assert message_count == 0, "Messages not CASCADE deleted"
        print("  [OK] CASCADE delete verified")
    
    # Final summary
    print_section("Workflow Verification Complete")
    print(f"Completed at: {datetime.now().isoformat()}")
    print("\n[OK] All steps completed successfully!")
    print("[OK] Database persistence verified")
    print("[OK] JSON logging verified")
    print("[OK] CASCADE deletion verified")
    print("\nPhase 3 workflow verification: PASSED")


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

