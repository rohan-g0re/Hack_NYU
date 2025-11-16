"""
Integration tests for status endpoints.

WHAT: Test /api/v1/llm/status and /api/v1/health endpoints
WHY: Ensure HTTP layer correctly integrates with provider and DB
HOW: Use TestClient with mocked LM Studio HTTP responses
"""

import pytest
import respx
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.llm.provider_factory import reset_provider


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.mark.phase1
@pytest.mark.integration
class TestLLMStatusEndpoint:
    """Test /api/v1/llm/status endpoint."""
    
    @respx.mock
    def test_llm_status_available(self, client, mock_settings):
        """Test LLM status when provider is available."""
        # Mock LM Studio models endpoint
        respx.get("http://localhost:1234/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "model-1"}, {"id": "model-2"}]}
            )
        )
        
        # Mock database ping
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {
                "available": True,
                "url": "sqlite:///./test.db",
                "error": None
            }
            
            response = client.get("/api/v1/llm/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "llm" in data
        assert data["llm"]["available"] is True
        assert data["llm"]["models"] == ["model-1", "model-2"]
        assert data["llm"]["error"] is None
        
        assert "database" in data
        assert data["database"]["available"] is True
    
    @respx.mock
    def test_llm_status_unavailable(self, client, mock_settings):
        """Test LLM status when provider is down."""
        # Mock LM Studio connection refused
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        
        # Mock database ping
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {
                "available": True,
                "url": "sqlite:///./test.db",
                "error": None
            }
            
            response = client.get("/api/v1/llm/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["llm"]["available"] is False
        assert data["llm"]["error"] is not None
        assert "refused" in data["llm"]["error"].lower()
    
    @respx.mock
    def test_llm_status_db_down(self, client, mock_settings):
        """Test LLM status when database is unavailable."""
        # Mock LM Studio as available
        respx.get("http://localhost:1234/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "model-1"}]}
            )
        )
        
        # Mock database ping failure
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {
                "available": False,
                "url": "sqlite:///./test.db",
                "error": "Connection failed"
            }
            
            response = client.get("/api/v1/llm/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["llm"]["available"] is True
        assert data["database"]["available"] is False
        assert data["database"]["error"] == "Connection failed"


@pytest.mark.phase1
@pytest.mark.integration
class TestHealthEndpoint:
    """Test /api/v1/health endpoint."""
    
    @respx.mock
    def test_health_all_systems_up(self, client, mock_settings):
        """Test health check when all systems are healthy."""
        # Mock LM Studio as available
        respx.get("http://localhost:1234/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "model-1"}]}
            )
        )
        
        # Mock database ping
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {
                "available": True,
                "url": "sqlite:///./test.db",
                "error": None
            }
            
            response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["app_name"] == "Test App"
        assert data["components"]["llm"]["available"] is True
        assert data["components"]["llm"]["provider"] == "lm_studio"
        assert data["components"]["database"]["available"] is True
    
    @respx.mock
    def test_health_degraded_llm_down(self, client, mock_settings):
        """Test health check when LLM is down."""
        # Mock LM Studio connection refused
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        
        # Mock database ping
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {
                "available": True,
                "url": "sqlite:///./test.db",
                "error": None
            }
            
            response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["components"]["llm"]["available"] is False
        assert data["components"]["database"]["available"] is True
    
    @respx.mock
    def test_health_degraded_db_down(self, client, mock_settings):
        """Test health check when database is down."""
        # Mock LM Studio as available
        respx.get("http://localhost:1234/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "model-1"}]}
            )
        )
        
        # Mock database ping failure
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {
                "available": False,
                "url": "sqlite:///./test.db",
                "error": "Connection failed"
            }
            
            response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["components"]["llm"]["available"] is True
        assert data["components"]["database"]["available"] is False
    
    @respx.mock
    def test_health_degraded_all_down(self, client, mock_settings):
        """Test health check when all systems are down."""
        # Mock LM Studio connection refused
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        
        # Mock database ping failure
        with patch("app.api.v1.endpoints.status.ping_database", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = {
                "available": False,
                "url": "sqlite:///./test.db",
                "error": "Connection failed"
            }
            
            response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["components"]["llm"]["available"] is False
        assert data["components"]["database"]["available"] is False


@pytest.mark.phase1
@pytest.mark.integration
class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root(self, client, mock_settings):
        """Test root endpoint returns app info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "app" in data
        assert "version" in data
        assert data["status"] == "running"

