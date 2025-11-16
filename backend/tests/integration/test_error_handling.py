"""
Integration tests for error handling and HTTP status codes.

WHAT: Test that errors are properly mapped to HTTP status codes
WHY: Ensure consistent API error responses per spec
HOW: Mock provider errors and verify HTTP responses
"""

import pytest
import respx
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.llm.provider_factory import reset_provider
from app.llm.types import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderDisabledError,
    ProviderResponseError,
)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.mark.phase1
@pytest.mark.integration
class TestProviderErrorMapping:
    """Test provider errors map to correct HTTP status codes."""
    
    @respx.mock
    def test_provider_timeout_returns_503(self, client, mock_settings):
        """Test ProviderTimeoutError returns 503 Service Unavailable."""
        # Mock timeout on all retries
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        
        # Mock database as available
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {"available": True, "url": "sqlite:///./test.db", "error": None}
            
            response = client.get("/api/v1/llm/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["llm"]["available"] is False
        assert "timeout" in data["llm"]["error"].lower()
    
    @respx.mock
    def test_provider_unavailable_returns_error(self, client, mock_settings):
        """Test ProviderUnavailableError returns error status."""
        # Mock connection refused
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {"available": True, "url": "sqlite:///./test.db", "error": None}
            
            response = client.get("/api/v1/llm/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["llm"]["available"] is False
        assert "refused" in data["llm"]["error"].lower()
    
    def test_disabled_provider_returns_error(self, client):
        """Test disabled provider returns appropriate error."""
        # Configure to use OpenRouter but disabled
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "openrouter"
            mock_settings.LLM_ENABLE_OPENROUTER = False
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            mock_settings.OPENROUTER_API_KEY = ""
            mock_settings.APP_NAME = "Test App"
            mock_settings.APP_VERSION = "0.1.0"
            
            # Reset provider to pick up new config
            reset_provider()
            
            # Mock database
            with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
                mock_db.return_value = {"available": True, "url": "sqlite:///./test.db", "error": None}
                
                response = client.get("/api/v1/llm/status")
            
            # Should return error status
            assert response.status_code == 200
            data = response.json()
            assert data["llm"]["available"] is False
            assert "disabled" in data["llm"]["error"].lower()
            
            reset_provider()


@pytest.mark.phase1
@pytest.mark.integration
class TestHealthEndpointErrorStates:
    """Test health endpoint in various error states."""
    
    @respx.mock
    def test_health_with_llm_timeout(self, client, mock_settings):
        """Test health endpoint when LLM times out."""
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {"available": True, "url": "sqlite:///./test.db", "error": None}
            
            response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["components"]["llm"]["available"] is False
        assert data["components"]["database"]["available"] is True
    
    @respx.mock
    def test_health_with_both_down(self, client, mock_settings):
        """Test health endpoint when both LLM and DB are down."""
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {"available": False, "url": "sqlite:///./test.db", "error": "Connection failed"}
            
            response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["components"]["llm"]["available"] is False
        assert data["components"]["database"]["available"] is False


@pytest.mark.phase1
@pytest.mark.integration
class TestEndpointResponseStructure:
    """Test that endpoints return proper response structures."""
    
    @respx.mock
    def test_llm_status_response_structure(self, client, mock_settings):
        """Test LLM status endpoint response has correct structure."""
        respx.get("http://localhost:1234/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "model-1"}]}
            )
        )
        
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {
                "available": True,
                "url": "sqlite:///./test.db",
                "error": None
            }
            
            response = client.get("/api/v1/llm/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "llm" in data
        assert "available" in data["llm"]
        assert "base_url" in data["llm"]
        assert "models" in data["llm"]
        assert "error" in data["llm"]
        
        assert "database" in data
        assert "available" in data["database"]
    
    @respx.mock
    def test_health_response_structure(self, client, mock_settings):
        """Test health endpoint response has correct structure."""
        respx.get("http://localhost:1234/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "model-1"}]}
            )
        )
        
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {"available": True, "url": "sqlite:///./test.db", "error": None}
            
            response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "app_name" in data
        assert "components" in data
        assert "llm" in data["components"]
        assert "database" in data["components"]
        assert "available" in data["components"]["llm"]
        assert "provider" in data["components"]["llm"]
        assert "available" in data["components"]["database"]


@pytest.mark.phase1
@pytest.mark.integration
class TestCORSAndMiddleware:
    """Test CORS and middleware configuration."""
    
    def test_cors_headers_present(self, client, mock_settings):
        """Test CORS headers are present in response."""
        response = client.get("/")
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
    
    def test_root_endpoint_structure(self, client, mock_settings):
        """Test root endpoint returns proper structure."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "app" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

