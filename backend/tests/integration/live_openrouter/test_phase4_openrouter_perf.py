"""
OpenRouter Phase 4 performance smoke tests.

WHAT: Light performance tests with small concurrency
WHY: Validate API latency and SSE responsiveness under load
HOW: Run 2-3 parallel sessions, measure latencies, record metrics
"""

import pytest
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
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
    """Sample initialize session request optimized for performance testing."""
    return {
        "buyer": {
            "name": "Perf Buyer",
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
            "max_tokens": 64  # Very short for faster tests
        }
    }


def create_and_start_session(client, request_data):
    """Helper to create session and start negotiation, return timing."""
    start = time.time()
    
    # Initialize
    init_start = time.time()
    init_response = client.post("/api/v1/simulation/initialize", json=request_data)
    init_latency = time.time() - init_start
    
    assert init_response.status_code == 200
    session_data = init_response.json()
    room_id = session_data["negotiation_rooms"][0]["room_id"]
    
    # Start negotiation
    start_start = time.time()
    start_response = client.post(f"/api/v1/negotiation/{room_id}/start")
    start_latency = time.time() - start_start
    
    assert start_response.status_code == 200
    
    total_latency = time.time() - start
    
    return {
        "session_id": session_data["session_id"],
        "room_id": room_id,
        "init_latency": init_latency,
        "start_latency": start_latency,
        "total_latency": total_latency
    }


@pytest.mark.phase4
@pytest.mark.integration
@pytest.mark.requires_openrouter
@pytest.mark.perf
@pytest.mark.slow
class TestOpenRouterPerformance:
    """Performance smoke tests for OpenRouter."""
    
    def test_api_latency_median(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test API endpoint latency (non-fatal metrics)."""
        latencies = []
        num_requests = 3
        
        for i in range(num_requests):
            result = create_and_start_session(client, sample_initialize_request)
            latencies.append({
                "init": result["init_latency"],
                "start": result["start_latency"],
                "total": result["total_latency"]
            })
            # Small delay between requests
            time.sleep(0.5)
        
        # Calculate medians
        init_medians = sorted([l["init"] for l in latencies])
        start_medians = sorted([l["start"] for l in latencies])
        total_medians = sorted([l["total"] for l in latencies])
        
        init_median = init_medians[len(init_medians) // 2]
        start_median = start_medians[len(start_medians) // 2]
        total_median = total_medians[len(total_medians) // 2]
        
        # Record metrics (non-fatal assertions)
        print(f"\n[PERF] Initialize latency median: {init_median:.2f}s")
        print(f"[PERF] Start latency median: {start_median:.2f}s")
        print(f"[PERF] Total latency median: {total_median:.2f}s")
        
        # Non-fatal: warn if latencies are high
        if init_median > 5.0:
            pytest.fail(f"Initialize latency median {init_median:.2f}s exceeds 5s threshold", pytrace=False)
        if start_median > 5.0:
            pytest.fail(f"Start latency median {start_median:.2f}s exceeds 5s threshold", pytrace=False)
    
    def test_concurrent_sessions(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test 2-3 concurrent session creation."""
        num_concurrent = 2
        executor = ThreadPoolExecutor(max_workers=num_concurrent)
        
        def run_session():
            return create_and_start_session(client, sample_initialize_request)
        
        start_time = time.time()
        futures = [executor.submit(run_session) for _ in range(num_concurrent)]
        results = [f.result() for f in futures]
        elapsed = time.time() - start_time
        
        executor.shutdown(wait=True)
        
        # Verify all succeeded
        assert len(results) == num_concurrent
        
        # Record metrics
        print(f"\n[PERF] Concurrent sessions ({num_concurrent}): {elapsed:.2f}s total")
        print(f"[PERF] Average per session: {elapsed / num_concurrent:.2f}s")
        
        # Non-fatal: warn if too slow
        if elapsed > 30.0:
            pytest.fail(f"Concurrent sessions took {elapsed:.2f}s (exceeds 30s threshold)", pytrace=False)
    
    def test_sse_connect_time(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test SSE connection establishment time."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        connect_times = []
        
        for _ in range(2):  # Test 2 connections
            start = time.time()
            with client.stream("GET", f"/api/v1/negotiation/{room_id}/stream") as response:
                connect_time = time.time() - start
                connect_times.append(connect_time)
                
                # Verify connection established
                assert response.status_code == 200
                
                # Read first event
                first_event_time = time.time()
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        first_event_time = time.time() - first_event_time
                        break
                    if time.time() - start > 5.0:  # 5s timeout
                        break
            
            time.sleep(0.5)
        
        median_connect = sorted(connect_times)[len(connect_times) // 2]
        
        print(f"\n[PERF] SSE connect time median: {median_connect:.2f}s")
        
        # Non-fatal assertion
        if median_connect > 2.0:
            pytest.fail(f"SSE connect time median {median_connect:.2f}s exceeds 2s threshold", pytrace=False)
    
    def test_sse_first_event_time(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test time to first SSE event."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        first_event_times = []
        
        for _ in range(2):
            start = time.time()
            with client.stream("GET", f"/api/v1/negotiation/{room_id}/stream") as response:
                assert response.status_code == 200
                
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        first_event_time = time.time() - start
                        first_event_times.append(first_event_time)
                        break
                    if time.time() - start > 10.0:  # 10s timeout
                        break
            
            time.sleep(0.5)
        
        if first_event_times:
            median = sorted(first_event_times)[len(first_event_times) // 2]
            print(f"\n[PERF] SSE first event time median: {median:.2f}s")
            
            # Non-fatal assertion
            if median > 5.0:
                pytest.fail(f"SSE first event time median {median:.2f}s exceeds 5s threshold", pytrace=False)

