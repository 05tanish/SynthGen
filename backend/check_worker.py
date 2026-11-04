#!/usr/bin/env python3
"""
Quick health check script to verify worker dependencies.
Run this on Railway to ensure the worker can start.
"""
import sys

def check_dependencies():
    """Check if all required packages are importable"""
    required = [
        'fastapi',
        'sqlalchemy',
        'langgraph',
        'langchain',
        'sdv',
        'pandas',
        'numpy',
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
            print(f"✅ {pkg}")
        except ImportError:
            print(f"❌ {pkg} - MISSING")
            missing.append(pkg)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        return False
    
    print("\n✅ All dependencies available")
    return True

def check_env_vars():
    """Check if critical environment variables are set"""
    import os
    
    required_vars = [
        'DATABASE_URL',
        'LLM_API_KEY',
        'CLOUDINARY_CLOUD_NAME',
    ]
    
    missing = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}")
        else:
            print(f"❌ {var} - NOT SET")
            missing.append(var)
    
    if missing:
        print(f"\n❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    print("\n✅ All environment variables set")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("WORKER HEALTH CHECK")
    print("=" * 60)
    
    print("\n📦 Checking dependencies...")
    deps_ok = check_dependencies()
    
    print("\n🔧 Checking environment variables...")
    env_ok = check_env_vars()
    
    print("\n" + "=" * 60)
    if deps_ok and env_ok:
        print("✅ Worker is ready to run!")
        sys.exit(0)
    else:
        print("❌ Worker has issues - see above")
        sys.exit(1)
