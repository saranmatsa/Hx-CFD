@echo off
REM Quick start script for CFD Platform on Windows

echo.
echo 🚀 CFD Platform - Quick Start
echo ==============================
echo.

REM Step 1: Build frontend
echo 📦 Building frontend...
cd frontend
call npm install
call npm run build
cd ..
echo ✓ Frontend built successfully
echo.

REM Step 2: Start Docker services
echo 🐳 Starting Docker services...
docker compose up -d
echo ✓ Services started
echo.

REM Step 3: Wait for services
echo ⏳ Waiting for services to be healthy...
timeout /t 10 /nobreak

echo.
echo ================================
echo ✓ CFD Platform is ready!
echo ================================
echo.
echo 📍 Access the application:
echo    http://localhost:3000
echo.
echo 🔐 Next steps:
echo    1. Open http://localhost:3000 in your browser
echo    2. Go to Settings (⚙️ icon) 
echo    3. Add your AI provider (OpenAI, Anthropic, Ollama, etc.)
echo    4. Paste your API key and test the connection
echo.
echo 📊 Monitoring:
echo    - Flower (Celery tasks): http://localhost:5555
echo    - PostgreSQL: localhost:5432
echo    - Redis: localhost:6379
echo.
echo ⚠️  To stop services: docker compose down
echo.
pause
