#!/usr/bin/env python3
"""
Integration Test Script for Multi-Agent Marketplace
Tests the complete flow from backend to frontend integration with LM Studio

Usage:
    python test_integration.py
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8000"
LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
FRONTEND_URL = "http://localhost:3000"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(status, message):
    """Print colored status message."""
    if status == "success":
        print(f"{GREEN}✓ {message}{RESET}")
    elif status == "error":
        print(f"{RED}✗ {message}{RESET}")
    elif status == "warning":
        print(f"{YELLOW}⚠ {message}{RESET}")
    elif status == "info":
        print(f"{BLUE}ℹ {message}{RESET}")

def print_header(text):
    """Print section header."""
    print(f"\n{BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{RESET}\n")

def test_lm_studio():
    """Test LM Studio availability."""
    print_header("Testing LM Studio Connection")
    
    try:
        response = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            print_status("success", "LM Studio is running")
            
            if models:
                print_status("info", f"Available models: {len(models)}")
                for model in models:
                    model_id = model.get("id", "unknown")
                    print(f"  - {model_id}")
                    if "qwen" in model_id.lower() or "qwen3-1.7b" in model_id.lower():
                        print_status("success", f"Found Qwen model: {model_id}")
            else:
                print_status("warning", "No models loaded in LM Studio")
                print_status("info", "Please load qwen/qwen3-1.7b in LM Studio")
            return True
        else:
            print_status("error", f"LM Studio returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_status("error", "Cannot connect to LM Studio at http://127.0.0.1:1234")
        print_status("info", "Make sure LM Studio is running with server started")
        return False
    except Exception as e:
        print_status("error", f"LM Studio test failed: {e}")
        return False

def test_backend_health():
    """Test backend health endpoint."""
    print_header("Testing Backend API")
    
    try:
        # Test root endpoint
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status("success", f"Backend is running: {data.get('app')} v{data.get('version')}")
        else:
            print_status("error", f"Backend root returned status {response.status_code}")
            return False
        
        # Test health endpoint
        response = requests.get(f"{BACKEND_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status("success", f"Health check passed: {data.get('status')}")
            
            # Check components
            components = data.get('components', {})
            llm = components.get('llm', {})
            db = components.get('database', {})
            
            if llm.get('available'):
                print_status("success", f"LLM Provider: {llm.get('provider')} (Available)")
            else:
                print_status("error", "LLM Provider: Unavailable")
                
            if db.get('available'):
                print_status("success", "Database: Available")
            else:
                print_status("error", "Database: Unavailable")
            
            return True
        else:
            print_status("error", f"Health endpoint returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_status("error", "Cannot connect to backend at http://localhost:8000")
        print_status("info", "Start backend with: cd backend && uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_status("error", f"Backend test failed: {e}")
        return False

def test_llm_status():
    """Test LLM status endpoint."""
    print_header("Testing LLM Provider Status")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/llm/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            llm = data.get('llm', {})
            
            print_status("info", f"Base URL: {llm.get('base_url')}")
            print_status("info", f"Available: {llm.get('available')}")
            
            if llm.get('available'):
                models = llm.get('models', [])
                if models:
                    print_status("success", f"Models available: {', '.join(models)}")
                else:
                    print_status("warning", "No models listed")
                return True
            else:
                error = llm.get('error', 'Unknown error')
                print_status("error", f"LLM not available: {error}")
                return False
        else:
            print_status("error", f"LLM status returned status {response.status_code}")
            return False
    except Exception as e:
        print_status("error", f"LLM status test failed: {e}")
        return False

def test_session_initialization():
    """Test session initialization endpoint."""
    print_header("Testing Session Initialization")
    
    # Sample configuration
    config = {
        "buyer": {
            "name": "Integration Test Buyer",
            "shopping_list": [
                {
                    "item_id": "test_laptop",
                    "item_name": "Test Laptop",
                    "quantity_needed": 5,
                    "min_price_per_unit": 400.0,
                    "max_price_per_unit": 600.0
                }
            ]
        },
        "sellers": [
            {
                "name": "Test Seller A",
                "profile": {
                    "priority": "customer_retention",
                    "speaking_style": "very_sweet"
                },
                "inventory": [
                    {
                        "item_id": "test_laptop",
                        "item_name": "Test Laptop",
                        "quantity_available": 10,
                        "cost_price": 400.0,
                        "selling_price": 650.0,
                        "least_price": 500.0
                    }
                ]
            },
            {
                "name": "Test Seller B",
                "profile": {
                    "priority": "maximize_profit",
                    "speaking_style": "rude"
                },
                "inventory": [
                    {
                        "item_id": "test_laptop",
                        "item_name": "Test Laptop",
                        "quantity_available": 10,
                        "cost_price": 380.0,
                        "selling_price": 620.0,
                        "least_price": 480.0
                    }
                ]
            }
        ],
        "llm_config": {
            "model": "qwen/qwen3-1.7b",
            "temperature": 0.7,
            "max_tokens": 500
        }
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/simulation/initialize",
            json=config,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_status("success", f"Session initialized: {data.get('session_id')}")
            print_status("info", f"Rooms created: {data.get('total_rooms')}")
            
            # Print room details
            for room in data.get('negotiation_rooms', []):
                print(f"  Room: {room.get('item_name')}")
                print(f"    Status: {room.get('status')}")
                print(f"    Sellers: {len(room.get('participating_sellers', []))}")
            
            return data.get('session_id'), data.get('negotiation_rooms', [])
        else:
            print_status("error", f"Initialization failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None, None
            
    except Exception as e:
        print_status("error", f"Session initialization test failed: {e}")
        return None, None

def test_frontend():
    """Test frontend availability."""
    print_header("Testing Frontend")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print_status("success", "Frontend is accessible")
            print_status("info", f"URL: {FRONTEND_URL}")
            return True
        else:
            print_status("warning", f"Frontend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_status("warning", "Cannot connect to frontend at http://localhost:3000")
        print_status("info", "Start frontend with: cd frontend && npm run dev")
        return False
    except Exception as e:
        print_status("warning", f"Frontend test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print(f"\n{BLUE}{'='*60}")
    print("  Multi-Agent Marketplace Integration Test")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{RESET}\n")
    
    results = {
        "lm_studio": False,
        "backend": False,
        "llm_status": False,
        "session": False,
        "frontend": False
    }
    
    # Test LM Studio
    results["lm_studio"] = test_lm_studio()
    
    # Test Backend
    results["backend"] = test_backend_health()
    
    # Test LLM Status
    if results["backend"]:
        results["llm_status"] = test_llm_status()
    
    # Test Session Initialization
    if results["backend"] and results["llm_status"]:
        session_id, rooms = test_session_initialization()
        results["session"] = session_id is not None
    
    # Test Frontend
    results["frontend"] = test_frontend()
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "success" if passed_test else "error"
        print_status(status, f"{test_name.replace('_', ' ').title()}: {'PASSED' if passed_test else 'FAILED'}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print_status("success", "All integration tests passed! ✓")
        print_status("info", "You can now start using the application")
        print_status("info", f"Frontend: {FRONTEND_URL}")
        print_status("info", f"Backend API: {BACKEND_URL}")
        print_status("info", f"API Docs: {BACKEND_URL}/docs")
        return 0
    else:
        print_status("error", "Some tests failed. Please check the errors above.")
        
        # Provide specific guidance
        if not results["lm_studio"]:
            print_status("info", "Fix: Start LM Studio and load qwen/qwen3-1.7b model")
        if not results["backend"]:
            print_status("info", "Fix: Start backend with: cd backend && uvicorn app.main:app --reload")
        if not results["frontend"]:
            print_status("info", "Fix: Start frontend with: cd frontend && npm run dev")
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

