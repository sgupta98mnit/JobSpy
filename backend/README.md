# JobSpy Web API Backend

FastAPI backend for the JobSpy web application that provides a REST API interface for job searching across multiple job boards.

## Setup

### Prerequisites

- Python 3.10 or higher
- pip or poetry for package management

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install the JobSpy library (from parent directory):
```bash
pip install -e ../
```

5. Copy environment configuration:
```bash
cp .env.example .env
```

### Running the Application

#### Development Server

```bash
python run.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Documentation

Once the server is running, you can access:

- **Interactive API docs (Swagger UI)**: http://localhost:8000/api/v1/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

### Health Check

Test that the server is running:
```bash
curl http://localhost:8000/api/v1/health/
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Application configuration
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py    # API router configuration
│           └── endpoints/
│               ├── __init__.py
│               └── health.py # Health check endpoint
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── run.py                  # Development server runner
└── README.md              # This file
```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and modify as needed:

- `DEBUG`: Enable debug mode (default: true)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `ALLOWED_HOSTS`: CORS allowed origins (comma-separated)

## Development

### Code Style

The project uses Black for code formatting:
```bash
black app/
```

### Testing

Run tests with pytest:
```bash
pytest
```