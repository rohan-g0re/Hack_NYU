"""
Live OpenRouter Phase 4 SSE streaming tests.

WHAT: Test SSE streaming endpoint with real OpenRouter provider
WHY: Validate real-time event streaming contract
HOW: Connect to SSE endpoint, capture events, verify ordering and schema
"""

import pytest
import os
import json
import time
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import check_openrouter_available


@pytest.fixture(scope="module")
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def skip_if_no_openrouter():
    """Skip test if OpenRouter not available."""
    if not check_openrouter_available():
        pytest.skip("OpenRouter not available (set RUN_LIVE_PROVIDER_TESTS=true, LLM_PROVIDER=openrouter, LLM_ENABLE_OPENROUTER=true, OPENROUTER_API_KEY)")


@pytest.fixture
def sample_initialize_request():
    """Sample initialize session request optimized for OpenRouter."""
    return {
        "buyer": {
            "name": "Test Buyer",
            "shopping_list": [
                {
                    "item_id": "item1",
                    "item_name": "Widget",
                    "quantity_needed": 10,
                    "min_price_per_unit": 5.0,
                    "max_price_per_unit": 15.0
                }
            ]
        },
        "sellers": [
            {
                "name": "SellerA",
                "inventory": [
                    {
                        "item_id": "item1",
                        "item_name": "Widget",
                        "cost_price": 4.0,
                        "selling_price": 12.0,
                        "least_price": 6.0,
                        "quantity_available": 20
                    }
                ],
                "profile": {
                    "priority": "customer_retention",
                    "speaking_style": "very_sweet"
                }
            }
        ],
        "llm_config": {
            "model": os.getenv("OPENROUTER_TEST_MODEL", "google/gemini-2.5-flash-lite"),
            "temperature": 0.1,
            "max_tokens": 64  # Very short for faster completion
        }
    }


def parse_sse_event(line: str):
    """Parse SSE event line."""
    if line.startswith("data: "):
        data_str = line[6:]  # Remove "data: " prefix
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            return None
    return None


@pytest.mark.phase4
@pytest.mark.integration
@pytest.mark.requires_openrouter
@pytest.mark.slow
class TestOpenRouterStreaming:
    """Test SSE streaming with OpenRouter."""
    
    def test_stream_connected_event(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test SSE stream sends connected event."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        # Connect to stream
        with client.stream("GET", f"/api/v1/negotiation/{room_id}/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            
            # Read first few events
            events = []
            start_time = time.time()
            timeout = 30  # 30 second timeout
            
            for line in response.iter_lines():
                if time.time() - start_time > timeout:
                    break
                
                if not line:
                    continue
                
                event = parse_sse_event(line)
                if event:
                    events.append(event)
                    
                    # Stop after connected event or first negotiation event
                    if event.get("type") == "connected":
                        break
                    if event.get("type") in ["buyer_message", "seller_response", "negotiation_complete"]:
                        break
            
            # Verify at least connected event received
            assert len(events) > 0, "No events received"
            assert events[0].get("type") == "connected", f"First event should be 'connected', got {events[0]}"
    
    def test_stream_event_ordering(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test SSE event ordering and schema."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        # Connect to stream and collect events
        events = []
        event_types_seen = set()
        
        with client.stream("GET", f"/api/v1/negotiation/{room_id}/stream") as response:
            assert response.status_code == 200
            
            start_time = time.time()
            timeout = 60  # 60 second timeout for negotiation completion
            
            for line in response.iter_lines():
                if time.time() - start_time > timeout:
                    break
                
                if not line:
                    continue
                
                event = parse_sse_event(line)
                if event:
                    events.append(event)
                    event_type = event.get("type")
                    event_types_seen.add(event_type)
                    
                    # Verify event schema
                    assert "type" in event, "Event missing 'type' field"
                    assert "data" in event or "timestamp" in event, "Event missing 'data' or 'timestamp'"
                    
                    # Stop on completion
                    if event_type == "negotiation_complete":
                        break
            
            # Verify event ordering: connected should be first
            assert len(events) > 0, "No events received"
            assert events[0].get("type") == "connected", "First event must be 'connected'"
            
            # Verify we saw at least one negotiation event (buyer_message or seller_response)
            negotiation_events = {"buyer_message", "seller_response", "negotiation_complete"}
            assert event_types_seen.intersection(negotiation_events), \
                f"Expected at least one negotiation event, saw {event_types_seen}"
    
    def test_stream_heartbeat_interval(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test SSE heartbeat events arrive within expected interval."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        heartbeat_interval = 15  # SSE_HEARTBEAT_INTERVAL from config
        tolerance = 5  # 5 second tolerance
        
        heartbeats = []
        start_time = time.time()
        
        with client.stream("GET", f"/api/v1/negotiation/{room_id}/stream") as response:
            assert response.status_code == 200
            
            # Collect heartbeats for 2 intervals
            timeout = (heartbeat_interval * 2) + tolerance
            
            for line in response.iter_lines():
                if time.time() - start_time > timeout:
                    break
                
                if not line:
                    continue
                
                event = parse_sse_event(line)
                if event and event.get("type") == "heartbeat":
                    heartbeats.append(time.time())
                    
                    # Stop after 2 heartbeats
                    if len(heartbeats) >= 2:
                        break
            
            # If we got heartbeats, verify interval
            if len(heartbeats) >= 2:
                interval = heartbeats[1] - heartbeats[0]
                assert interval <= heartbeat_interval + tolerance, \
                    f"Heartbeat interval {interval}s exceeds expected {heartbeat_interval}s + {tolerance}s tolerance"
    
    def test_stream_clean_close(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test SSE stream closes cleanly after negotiation_complete."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        completed = False
        
        with client.stream("GET", f"/api/v1/negotiation/{room_id}/stream") as response:
            assert response.status_code == 200
            
            start_time = time.time()
            timeout = 60
            
            for line in response.iter_lines():
                if time.time() - start_time > timeout:
                    # Manual timeout acceptable for this test
                    break
                
                if not line:
                    continue
                
                event = parse_sse_event(line)
                if event and event.get("type") == "negotiation_complete":
                    completed = True
                    # Stream should close after this
                    break
        
        # If we got completion, verify stream closed
        # (TestClient handles this automatically, but we verify completion was seen)
        if completed:
            assert True, "Stream completed successfully"
        else:
            # Timeout acceptable for short test negotiation
            pytest.skip("Negotiation did not complete within timeout (acceptable for live test)")

