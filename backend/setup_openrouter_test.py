"""
Quick setup script to enable OpenRouter for testing.

WHAT: Check and guide OpenRouter setup
WHY: Ensure proper configuration before running tests
HOW: Check env vars, prompt for API key if needed
"""

import os
from pathlib import Path

def check_setup():
    """Check if OpenRouter is properly configured."""
    print("="*60)
    print("OpenRouter Setup Check")
    print("="*60)
    
    # Check for .env file
    project_root = Path(__file__).parent.parent
    backend_dir = Path(__file__).parent
    env_files = [
        project_root / ".env",
        backend_dir / ".env"
    ]
    
    env_file = None
    for ef in env_files:
        if ef.exists():
            env_file = ef
            break
    
    if not env_file:
        print("\n[WARNING] No .env file found!")
        print(f"   Create one at: {project_root / '.env'}")
        print("\nRequired settings:")
        print("  LLM_PROVIDER=openrouter")
        print("  LLM_ENABLE_OPENROUTER=true")
        print("  OPENROUTER_API_KEY=sk-or-v1-...")
        return False
    
    print(f"\n[OK] Found .env file: {env_file}")
    
    # Read .env file
    env_vars = {}
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"[ERROR] Error reading .env: {e}")
        return False
    
    # Check required vars
    provider = env_vars.get('LLM_PROVIDER', 'lm_studio')
    enabled = env_vars.get('LLM_ENABLE_OPENROUTER', 'false').lower() == 'true'
    api_key = env_vars.get('OPENROUTER_API_KEY', '')
    
    print(f"\nConfiguration:")
    print(f"  LLM_PROVIDER: {provider}")
    print(f"  LLM_ENABLE_OPENROUTER: {enabled}")
    print(f"  OPENROUTER_API_KEY: {'[SET]' if api_key else '[MISSING]'}")
    
    if provider != 'openrouter':
        print(f"\n[WARNING] LLM_PROVIDER is '{provider}', should be 'openrouter'")
        print(f"   Update {env_file} with: LLM_PROVIDER=openrouter")
        return False
    
    if not enabled:
        print(f"\n[WARNING] LLM_ENABLE_OPENROUTER is false, should be true")
        print(f"   Update {env_file} with: LLM_ENABLE_OPENROUTER=true")
        return False
    
    if not api_key:
        print(f"\n[WARNING] OPENROUTER_API_KEY is missing")
        print(f"   Get your key from: https://openrouter.ai/keys")
        print(f"   Add to {env_file}: OPENROUTER_API_KEY=sk-or-v1-...")
        return False
    
    print("\n[SUCCESS] OpenRouter is properly configured!")
    print("\nYou can now run:")
    print("  python test_openrouter_negotiation.py")
    return True

if __name__ == "__main__":
    if check_setup():
        print("\n" + "="*60)
        print("Ready to test! Run:")
        print("  python test_openrouter_negotiation.py")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("Please fix the configuration issues above")
        print("See OPENROUTER_TESTING.md for detailed setup guide")
        print("="*60)

