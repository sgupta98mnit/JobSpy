@echo off
echo Starting JobSpy Web API Backend...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the development server
echo Starting FastAPI development server...
echo API will be available at: http://localhost:8000
echo Interactive docs at: http://localhost:8000/api/v1/docs
echo.

python run.py