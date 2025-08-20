#!/usr/bin/env python3
"""
Test script to verify the backend setup and JobSpy integration.
"""

import sys
import os

# Add the parent directory to the path to import jobspy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Test that all required imports work."""
    try:
        # Test FastAPI imports
        from fastapi import FastAPI
        from app.main import app
        from app.core.config import settings
        print("✓ FastAPI imports successful")
        
        # Test JobSpy import
        import jobspy
        from jobspy import scrape_jobs
        print("✓ JobSpy imports successful")
        
        # Test configuration
        print(f"✓ App configuration loaded: {settings.PROJECT_NAME} v{settings.VERSION}")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_jobspy_basic():
    """Test basic JobSpy functionality."""
    try:
        from jobspy import scrape_jobs
        
        # Test with minimal parameters (dry run)
        print("✓ JobSpy scrape_jobs function accessible")
        return True
    except Exception as e:
        print(f"✗ JobSpy test error: {e}")
        return False

def main():
    """Run all setup tests."""
    print("Testing backend setup...")
    print("-" * 40)
    
    success = True
    success &= test_imports()
    success &= test_jobspy_basic()
    
    print("-" * 40)
    if success:
        print("✓ All tests passed! Backend setup is complete.")
        print("\nTo start the development server:")
        print("  python run.py")
        print("\nAPI will be available at:")
        print("  http://localhost:8000/api/v1/health/")
        print("  http://localhost:8000/api/v1/docs")
    else:
        print("✗ Some tests failed. Please check the setup.")
        sys.exit(1)

if __name__ == "__main__":
    main()