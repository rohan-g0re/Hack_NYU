#!/usr/bin/env python3
"""
Quick verification script for Phase 1 setup.

WHAT: Check that all components can be imported and basic config works
WHY: Catch setup issues early before running the full app
HOW: Import key modules, check config, verify structure
"""

import sys
from pathlib import Path


def verify_imports():
    """Verify all Phase 1 modules can be imported."""
    print("[*] Verifying imports...")
    
    try:
        from app.llm import (
            ChatMessage,
            TokenChunk,
            LLMResult,
            ProviderStatus,
            get_provider,
        )
        from app.core.config import settings
        from app.core.database import ping_database
        from app.api.v1.router import api_router
        from app.main import app
        print("  [OK] All imports successful")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        return False


def verify_config():
    """Verify configuration can be loaded."""
    print("\n[*] Verifying configuration...")
    
    try:
        from app.core.config import settings
        
        print(f"  App Name: {settings.APP_NAME}")
        print(f"  Version: {settings.APP_VERSION}")
        print(f"  LLM Provider: {settings.LLM_PROVIDER}")
        print(f"  LM Studio URL: {settings.LM_STUDIO_BASE_URL}")
        print(f"  Database: {settings.DATABASE_URL}")
        print("  [OK] Configuration loaded")
        return True
    except Exception as e:
        print(f"  [FAIL] Config failed: {e}")
        return False


def verify_structure():
    """Verify expected files exist."""
    print("\n[*] Verifying file structure...")
    
    expected_files = [
        "app/llm/types.py",
        "app/llm/provider.py",
        "app/llm/provider_factory.py",
        "app/llm/lm_studio.py",
        "app/llm/openrouter.py",
        "app/llm/streaming_handler.py",
        "app/core/config.py",
        "app/core/database.py",
        "app/api/v1/endpoints/status.py",
        "app/main.py",
        "tests/unit/test_llm_provider.py",
        "tests/integration/test_status_endpoints.py",
        "pyproject.toml",
    ]
    
    missing = []
    for file_path in expected_files:
        if not Path(file_path).exists():
            missing.append(file_path)
            print(f"  [MISS] Missing: {file_path}")
        else:
            print(f"  [OK] Found: {file_path}")
    
    if missing:
        print(f"\n  [FAIL] {len(missing)} files missing")
        return False
    else:
        print(f"\n  [OK] All {len(expected_files)} files present")
        return True


def verify_provider_factory():
    """Verify provider factory works."""
    print("\n[*] Verifying provider factory...")
    
    try:
        from app.llm.provider_factory import get_provider, reset_provider
        from app.llm.lm_studio import LMStudioProvider
        
        reset_provider()
        provider = get_provider()
        
        if isinstance(provider, LMStudioProvider):
            print("  [OK] Provider factory returns LMStudioProvider")
            return True
        else:
            print(f"  [FAIL] Unexpected provider type: {type(provider)}")
            return False
    except Exception as e:
        print(f"  [FAIL] Provider factory failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Phase 1 Setup Verification")
    print("=" * 60)
    
    checks = [
        verify_structure,
        verify_imports,
        verify_config,
        verify_provider_factory,
    ]
    
    results = [check() for check in checks]
    
    print("\n" + "=" * 60)
    if all(results):
        print("[SUCCESS] All verification checks passed!")
        print("\nNext steps:")
        print("  1. Start LM Studio on port 1234")
        print("  2. Run: poetry run python -m app.main")
        print("  3. Visit: http://localhost:8000/api/v1/health")
        print("  4. Run tests: poetry run pytest -v")
        return 0
    else:
        print("[FAILED] Some verification checks failed")
        print("\nTroubleshooting:")
        print("  1. Ensure you're in the backend directory")
        print("  2. Run: poetry install")
        print("  3. Check that all files were created")
        return 1


if __name__ == "__main__":
    sys.exit(main())

