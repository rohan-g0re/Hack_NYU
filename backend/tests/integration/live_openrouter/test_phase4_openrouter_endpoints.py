"""
Live OpenRouter Phase 4 endpoint tests.

WHAT: Test Phase 4 API endpoints with real OpenRouter provider
WHY: Validate API contract with live inference provider
HOW: Use TestClient with OpenRouter configured, skip if not available
"""

import pytest
import os
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
            "temperature": 0.1,  # Low temp for deterministic tests
            "max_tokens": 128  # Short responses for faster tests
        }
    }


@pytest.mark.phase4
@pytest.mark.integration
@pytest.mark.requires_openrouter
@pytest.mark.slow
class TestOpenRouterSimulationEndpoints:
    """Test simulation endpoints with OpenRouter."""
    
    def test_initialize_session_success(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test successful session initialization."""
        response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "created_at" in data
        assert "buyer_id" in data
        assert "seller_ids" in data
        assert "negotiation_rooms" in data
        assert "total_rooms" in data
        assert data["total_rooms"] == 1
        assert len(data["negotiation_rooms"]) == 1
        
        room = data["negotiation_rooms"][0]
        assert "room_id" in room
        assert room["item_name"] == "Widget"
        assert room["status"] == "pending"
    
    def test_initialize_session_validation_error(self, client, skip_if_no_openrouter):
        """Test session initialization with invalid price range."""
        request = {
            "buyer": {
                "name": "Test",
                "shopping_list": [
                    {
                        "item_id": "item1",
                        "item_name": "Widget",
                        "quantity_needed": 10,
                        "min_price_per_unit": 15.0,  # Min > Max
                        "max_price_per_unit": 10.0
                    }
                ]
            },
            "sellers": [{
                "name": "SellerA",
                "inventory": [{
                    "item_id": "item1",
                    "item_name": "Widget",
                    "cost_price": 4.0,
                    "selling_price": 12.0,
                    "least_price": 6.0,
                    "quantity_available": 20
                }],
                "profile": {
                    "priority": "customer_retention",
                    "speaking_style": "very_sweet"
                }
            }],
            "llm_config": {
                "model": os.getenv("OPENROUTER_TEST_MODEL", "google/gemini-2.5-flash-lite"),
                "temperature": 0.1,
                "max_tokens": 128
            }
        }
        
        response = client.post("/api/v1/simulation/initialize", json=request)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_get_session_success(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test getting session details."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        session_id = init_response.json()["session_id"]
        
        response = client.get(f"/api/v1/simulation/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "status" in data
        assert "buyer_name" in data
    
    def test_get_session_not_found(self, client, skip_if_no_openrouter):
        """Test getting non-existent session."""
        response = client.get("/api/v1/simulation/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "SESSION_NOT_FOUND"
    
    def test_delete_session_success(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test deleting a session."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        session_id = init_response.json()["session_id"]
        
        response = client.delete(f"/api/v1/simulation/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert data["session_id"] == session_id
    
    def test_delete_session_not_found(self, client, skip_if_no_openrouter):
        """Test deleting non-existent session (idempotent)."""
        response = client.delete("/api/v1/simulation/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "SESSION_NOT_FOUND"
    
    def test_get_session_summary(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test getting session summary (shape only, may be empty)."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        session_id = init_response.json()["session_id"]
        
        response = client.get(f"/api/v1/simulation/{session_id}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check summary structure (content may be empty)
        assert "session_id" in data
        assert "buyer_name" in data
        assert "total_items_requested" in data
        assert "completed_purchases" in data
        assert "failed_purchases" in data
        assert "purchases" in data
        assert "failed_items" in data
        assert "total_cost_summary" in data
        assert "negotiation_metrics" in data


@pytest.mark.phase4
@pytest.mark.integration
@pytest.mark.requires_openrouter
@pytest.mark.slow
class TestOpenRouterNegotiationEndpoints:
    """Test negotiation control endpoints with OpenRouter."""
    
    def test_start_negotiation_success(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test starting a negotiation."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        response = client.post(f"/api/v1/negotiation/{room_id}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert "stream_url" in data
        assert data["stream_url"] == f"/api/v1/negotiation/{room_id}/stream"
    
    def test_start_negotiation_not_found(self, client, skip_if_no_openrouter):
        """Test starting non-existent negotiation."""
        response = client.post("/api/v1/negotiation/nonexistent-id/start")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "ROOM_NOT_FOUND"
    
    def test_start_negotiation_already_active(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test starting already active negotiation (idempotency conflict)."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        # Start once
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        # Try to start again
        response = client.post(f"/api/v1/negotiation/{room_id}/start")
        
        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "NEGOTIATION_ALREADY_ACTIVE"
    
    def test_send_message(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test sending a manual buyer message."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        response = client.post(
            f"/api/v1/negotiation/{room_id}/message",
            json={"message": "Hello @SellerA"}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "message_id" in data
        assert "timestamp" in data
        assert "mentioned_sellers" in data
        assert data["processing"] is True
    
    def test_get_negotiation_state(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test getting negotiation state."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        response = client.get(f"/api/v1/negotiation/{room_id}/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["room_id"] == room_id
        assert "item_name" in data
        assert "status" in data
        assert "current_round" in data
        assert "max_rounds" in data
        assert "conversation_history" in data
        assert "current_offers" in data
        assert "buyer_constraints" in data
    
    def test_force_decision(self, client, skip_if_no_openrouter, sample_initialize_request):
        """Test forcing a decision."""
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        session_data = init_response.json()
        room_id = session_data["negotiation_rooms"][0]["room_id"]
        seller_id = session_data["seller_ids"][0]
        
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "final_price_per_unit": 10.0,
                "quantity": 10,
                "decision_reason": "Manual override"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["decision_type"] == "deal"
        assert data["selected_seller_id"] == seller_id


@pytest.mark.phase4
@pytest.mark.integration
@pytest.mark.requires_openrouter
@pytest.mark.slow
class TestOpenRouterLogsEndpoint:
    """Test logs retrieval endpoint with OpenRouter."""
    
    def test_get_log_not_found(self, client, skip_if_no_openrouter):
        """Test retrieving non-existent log."""
        response = client.get("/api/v1/logs/fake-session/fake-room")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] in ["LOG_NOT_FOUND", "ROOM_NOT_FOUND"]

