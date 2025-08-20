#!/usr/bin/env python3
"""
Start the FastAPI server for testing.
"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    print("Starting Job Search API server...")
    print("API Documentation: http://127.0.0.1:8000/docs")
    print("Health Check: http://127.0.0.1:8000/api/v1/health/")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )