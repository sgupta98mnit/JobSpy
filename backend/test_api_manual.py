#!/usr/bin/env python3
"""
Manual test script for the search API endpoint.
"""

import requests
import json
import sys

def test_health_endpoint():
    """Test the health endpoint."""
    try:
        response = requests.get("http://127.0.0.1:8000/api/v1/health/")
        print(f"Health endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.json()}")
            return True
    except requests.exceptions.ConnectionError:
        print("Server is not running. Please start the server first.")
        return False
    except Exception as e:
        print(f"Error testing health endpoint: {e}")
        return False

def test_search_validation():
    """Test the search validation endpoint."""
    try:
        # Test valid parameters
        response = requests.get(
            "http://127.0.0.1:8000/api/v1/search/validate",
            params={
                "search_term": "software engineer",
                "location": "San Francisco, CA",
                "site_names": "indeed,linkedin",
                "results_wanted": 10
            }
        )
        print(f"Validation endpoint status: {response.status_code}")
        print(f"Validation response: {response.json()}")
        
        # Test invalid parameters
        response = requests.get(
            "http://127.0.0.1:8000/api/v1/search/validate",
            params={
                "search_term": "software engineer",
                "job_type": "invalid_type"
            }
        )
        print(f"Invalid validation status: {response.status_code}")
        print(f"Invalid validation response: {response.json()}")
        
    except Exception as e:
        print(f"Error testing validation endpoint: {e}")

def test_search_endpoint():
    """Test the search endpoint with a simple request."""
    try:
        search_data = {
            "search_term": "python developer",
            "location": "Remote",
            "site_names": ["indeed"],
            "results_wanted": 5,
            "is_remote": True
        }
        
        response = requests.post(
            "http://127.0.0.1:8000/api/v1/search/",
            json=search_data,
            timeout=30
        )
        
        print(f"Search endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total results: {data.get('total_results', 0)}")
            print(f"Search ID: {data.get('search_metadata', {}).get('search_id', 'N/A')}")
            print(f"Duration: {data.get('search_metadata', {}).get('search_duration', 0):.2f}s")
            print(f"Errors: {len(data.get('errors', []))}")
            print(f"Warnings: {len(data.get('warnings', []))}")
            
            if data.get('jobs'):
                print(f"First job title: {data['jobs'][0].get('title', 'N/A')}")
                print(f"First job company: {data['jobs'][0].get('company_name', 'N/A')}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error testing search endpoint: {e}")

if __name__ == "__main__":
    print("Testing Job Search API endpoints...")
    print("=" * 50)
    
    # Test health first
    if not test_health_endpoint():
        print("Please start the server with: python -m uvicorn app.main:app --reload")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Testing validation endpoint...")
    test_search_validation()
    
    print("\n" + "=" * 50)
    print("Testing search endpoint...")
    test_search_endpoint()
    
    print("\n" + "=" * 50)
    print("API testing complete!")