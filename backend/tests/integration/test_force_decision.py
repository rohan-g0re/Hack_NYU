"""
Integration tests for force decision endpoint with validation.

WHAT: Test force decision endpoint with various validation scenarios
WHY: Ensure validation logic works correctly for forced decisions
HOW: Test valid and invalid decision parameters
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_initialize_request():
    """Sample initialization request."""
    return {
        "buyer": {
            "name": "Test Buyer",
            "shopping_list": [
                {
                    "item_id": "widget_a",
                    "item_name": "Widget A",
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
                        "item_id": "widget_a",
                        "item_name": "Widget A",
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
            },
            {
                "name": "Seller B",
                "inventory": [
                    {
                        "item_id": "widget_a",
                        "item_name": "Widget A",
                        "cost_price": 3.5,
                        "selling_price": 11.0,
                        "least_price": 5.5,
                        "quantity_available": 15
                    }
                ],
                "profile": {
                    "priority": "maximize_profit",
                    "speaking_style": "rude"
                }
            }
        ],
        "llm_config": {
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 500
        }
    }


class TestForceDecisionValidation:
    """Test force decision endpoint validation."""
    
    def test_force_decision_deal_success(self, client, sample_initialize_request):
        """Test forcing a valid deal decision."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        assert init_response.status_code == 200
        
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        # Force decision with valid parameters
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "final_price_per_unit": 10.0,
                "quantity": 10,
                "decision_reason": "Best offer"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["decision_type"] == "deal"
        assert data["selected_seller_id"] == seller_id
        assert data["final_price"] == 10.0
        assert data["quantity"] == 10
        assert data["total_cost"] == 100.0
        assert "decision_reason" in data
    
    def test_force_decision_no_deal_success(self, client, sample_initialize_request):
        """Test forcing a valid no deal decision."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        assert init_response.status_code == 200
        
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        # Force no deal
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "no_deal",
                "decision_reason": "No acceptable offers"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["decision_type"] == "no_deal"
        assert data["selected_seller_id"] is None
    
    def test_force_decision_invalid_decision_type(self, client, sample_initialize_request):
        """Test force decision with invalid decision_type."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        # Invalid decision_type
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "maybe",  # Invalid
                "decision_reason": "Unsure"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "decision_type" in data["message"].lower()
    
    def test_force_decision_deal_missing_seller(self, client, sample_initialize_request):
        """Test deal without selected_seller_id."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        # Deal without seller
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "final_price_per_unit": 10.0,
                "quantity": 10
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "selected_seller_id" in data["message"].lower()
    
    def test_force_decision_deal_missing_price(self, client, sample_initialize_request):
        """Test deal without final_price_per_unit."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        # Deal without price
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "quantity": 10
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "final_price_per_unit" in data["message"].lower()
    
    def test_force_decision_deal_missing_quantity(self, client, sample_initialize_request):
        """Test deal without quantity."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        # Deal without quantity
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "final_price_per_unit": 10.0
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "quantity" in data["message"].lower()
    
    def test_force_decision_invalid_seller(self, client, sample_initialize_request):
        """Test deal with non-participant seller."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        
        # Invalid seller ID (not a participant)
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": "fake-seller-id",
                "final_price_per_unit": 10.0,
                "quantity": 10
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "participant" in data["message"].lower()
    
    def test_force_decision_price_below_min(self, client, sample_initialize_request):
        """Test deal with price below buyer's minimum."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        # Price below min (min is 5.0)
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "final_price_per_unit": 3.0,  # Below min
                "quantity": 10
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "constraints" in data["message"].lower() or "outside" in data["message"].lower()
    
    def test_force_decision_price_above_max(self, client, sample_initialize_request):
        """Test deal with price above buyer's maximum."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        # Price above max (max is 15.0)
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "final_price_per_unit": 20.0,  # Above max
                "quantity": 10
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "constraints" in data["message"].lower() or "outside" in data["message"].lower()
    
    def test_force_decision_quantity_too_high(self, client, sample_initialize_request):
        """Test deal with quantity exceeding buyer's needs."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        # Quantity too high (needed is 10)
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "final_price_per_unit": 10.0,
                "quantity": 20  # More than needed
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "quantity" in data["message"].lower()
    
    def test_force_decision_quantity_zero(self, client, sample_initialize_request):
        """Test deal with zero quantity."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        # Zero quantity
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "final_price_per_unit": 10.0,
                "quantity": 0  # Invalid
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_force_decision_nonexistent_room(self, client):
        """Test force decision on non-existent room."""
        response = client.post(
            "/api/v1/negotiation/fake-room-id/decide",
            params={
                "decision_type": "no_deal",
                "decision_reason": "Testing"
            }
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "ROOM_NOT_FOUND"
    
    def test_force_decision_with_reason(self, client, sample_initialize_request):
        """Test force decision includes reason in response."""
        # Initialize session
        init_response = client.post(
            "/api/v1/simulation/initialize",
            json=sample_initialize_request
        )
        room_id = init_response.json()["negotiation_rooms"][0]["room_id"]
        seller_id = init_response.json()["seller_ids"][0]
        
        custom_reason = "This is a custom decision reason"
        
        # Force decision with reason
        response = client.post(
            f"/api/v1/negotiation/{room_id}/decide",
            params={
                "decision_type": "deal",
                "selected_seller_id": seller_id,
                "final_price_per_unit": 10.0,
                "quantity": 10,
                "decision_reason": custom_reason
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["decision_reason"] == custom_reason

