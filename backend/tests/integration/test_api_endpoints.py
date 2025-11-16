"""
Integration tests for Phase 4 API endpoints.

WHAT: Comprehensive tests for simulation, negotiation, streaming, and logs endpoints
WHY: Ensure API contract compliance and error handling
HOW: FastAPI TestClient with mocked providers and database
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from app.main import app
from app.core.database import get_db
from app.core.models import (
    Session as SessionModel, Buyer, BuyerItem, Seller, SellerInventory,
    NegotiationRun, Message, Offer, NegotiationOutcome
)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_initialize_request():
    """Sample initialize session request."""
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
                "name": "Seller A",
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
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 500
        }
    }


class TestSimulationEndpoints:
    """Test simulation endpoints."""
    
    def test_initialize_session_success(self, client, sample_initialize_request):
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
        
        # Check room structure
        room = data["negotiation_rooms"][0]
        assert "room_id" in room
        assert room["item_name"] == "Widget"
        assert room["status"] == "pending"
    
    def test_initialize_session_validation_errors(self, client):
        """Test session initialization with invalid data."""
        # Missing buyer
        response = client.post(
            "/api/v1/simulation/initialize",
            json={"sellers": [], "llm_config": {}}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_initialize_session_too_many_sellers(self, client, sample_initialize_request):
        """Test initialization with too many sellers."""
        # Add 11 sellers
        sample_initialize_request["sellers"] = [
            sample_initialize_request["sellers"][0] for _ in range(11)
        ]
        
        response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        
        # Should be caught by Pydantic validation
        assert response.status_code == 400
    
    def test_get_session_success(self, client, sample_initialize_request):
        """Test getting session details."""
        # First create a session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        session_id = init_response.json()["session_id"]
        
        # Get session
        response = client.get(f"/api/v1/simulation/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "status" in data
        assert "buyer_name" in data
    
    def test_get_session_not_found(self, client):
        """Test getting non-existent session."""
        response = client.get("/api/v1/simulation/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "SESSION_NOT_FOUND"
    
    def test_delete_session_success(self, client, sample_initialize_request):
        """Test deleting a session."""
        # First create a session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        session_id = init_response.json()["session_id"]
        
        # Delete session
        response = client.delete(f"/api/v1/simulation/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert data["session_id"] == session_id
    
    def test_delete_session_not_found(self, client):
        """Test deleting non-existent session."""
        response = client.delete("/api/v1/simulation/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "SESSION_NOT_FOUND"
    
    def test_get_session_summary(self, client, sample_initialize_request):
        """Test getting session summary."""
        # Create a session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        session_id = init_response.json()["session_id"]
        
        # Get summary
        response = client.get(f"/api/v1/simulation/{session_id}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check summary structure
        assert "session_id" in data
        assert "buyer_name" in data
        assert "total_items_requested" in data
        assert "completed_purchases" in data
        assert "failed_purchases" in data
        assert "purchases" in data
        assert "failed_items" in data
        assert "total_cost_summary" in data
        assert "negotiation_metrics" in data


class TestNegotiationEndpoints:
    """Test negotiation control endpoints."""
    
    def test_start_negotiation_success(self, client, sample_initialize_request):
        """Test starting a negotiation."""
        # Create a session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        # Start negotiation
        response = client.post(f"/api/v1/negotiation/{room_id}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert "stream_url" in data
        assert data["stream_url"] == f"/api/v1/negotiation/{room_id}/stream"
    
    def test_start_negotiation_not_found(self, client):
        """Test starting non-existent negotiation."""
        response = client.post("/api/v1/negotiation/nonexistent-id/start")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "ROOM_NOT_FOUND"
    
    def test_start_negotiation_already_active(self, client, sample_initialize_request):
        """Test starting already active negotiation."""
        # Create and start a negotiation
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
    
    def test_send_message(self, client, sample_initialize_request):
        """Test sending a manual message."""
        # Create and start negotiation
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        # Send message
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
    
    def test_get_negotiation_state(self, client, sample_initialize_request):
        """Test getting negotiation state."""
        # Create session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        # Get state
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
    
    def test_force_decision(self, client, sample_initialize_request):
        """Test forcing a decision."""
        # Create and start negotiation
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        # Force decision
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


class TestStreamingEndpoint:
    """Test SSE streaming endpoint."""
    
    def test_stream_not_found(self, client):
        """Test streaming non-existent room."""
        response = client.get("/api/v1/negotiation/nonexistent-id/stream")
        
        # SSE endpoint should return 404
        assert response.status_code == 404
    
    @patch('app.api.v1.endpoints.streaming.get_provider')
    @patch('app.api.v1.endpoints.streaming.NegotiationGraph')
    def test_stream_connected_event(self, mock_graph, mock_provider, client, sample_initialize_request):
        """Test SSE stream sends connected event."""
        # Create and start negotiation
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        client.post(f"/api/v1/negotiation/{room_id}/start")
        
        # Mock the graph to return immediate completion
        async def mock_run(room_state):
            yield {
                "type": "negotiation_complete",
                "data": {"room_id": room_id},
                "timestamp": datetime.now()
            }
        
        mock_graph_instance = MagicMock()
        mock_graph_instance.run = mock_run
        mock_graph.return_value = mock_graph_instance
        
        # Get stream
        with client.stream("GET", f"/api/v1/negotiation/{room_id}/stream") as response:
            assert response.status_code == 200
            # Check that it's text/event-stream
            assert "text/event-stream" in response.headers.get("content-type", "")


class TestLogsEndpoint:
    """Test logs retrieval endpoint."""
    
    def test_get_log_not_found(self, client):
        """Test retrieving non-existent log."""
        response = client.get("/api/v1/logs/fake-session/fake-room")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] in ["LOG_NOT_FOUND", "ROOM_NOT_FOUND"]


class TestValidationErrors:
    """Test request validation errors."""
    
    def test_invalid_price_range(self, client):
        """Test invalid price range in shopping item."""
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
                "name": "Seller A",
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
                "model": "test-model",
                "temperature": 0.7,
                "max_tokens": 500
            }
        }
        
        response = client.post("/api/v1/simulation/initialize", json=request)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_invalid_inventory_prices(self, client):
        """Test invalid inventory price constraints."""
        request = {
            "buyer": {
                "name": "Test",
                "shopping_list": [{
                    "item_id": "item1",
                    "item_name": "Widget",
                    "quantity_needed": 10,
                    "min_price_per_unit": 5.0,
                    "max_price_per_unit": 15.0
                }]
            },
            "sellers": [{
                "name": "Seller A",
                "inventory": [{
                    "item_id": "item1",
                    "item_name": "Widget",
                    "cost_price": 10.0,
                    "selling_price": 8.0,  # Selling < Cost
                    "least_price": 6.0,
                    "quantity_available": 20
                }],
                "profile": {
                    "priority": "customer_retention",
                    "speaking_style": "very_sweet"
                }
            }],
            "llm_config": {
                "model": "test-model",
                "temperature": 0.7,
                "max_tokens": 500
            }
        }
        
        response = client.post("/api/v1/simulation/initialize", json=request)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"

