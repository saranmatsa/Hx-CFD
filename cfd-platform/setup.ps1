# CFD Platform Local Development Setup Script for Windows

Write-Host "🚀 Setting up CFD Platform for local development..." -ForegroundColor Green

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is installed
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

# Create .env file if it doesn't exist
if (-not (Test-Path .env)) {
    Write-Host "📝 Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✅ .env file created. Please review and update it if needed." -ForegroundColor Green
} else {
    Write-Host "✅ .env file already exists." -ForegroundColor Green
}

# Create necessary directories
Write-Host "📁 Creating necessary directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "C:\temp\cfd\uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "C:\temp\cfd\simulations" | Out-Null
New-Item -ItemType Directory -Force -Path "infrastructure\postgres\init" | Out-Null

# Build Docker images
Write-Host "🔨 Building Docker images..." -ForegroundColor Yellow
docker-compose build

# Start services
Write-Host "🚀 Starting services..." -ForegroundColor Yellow
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
Write-Host "⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Start backend and worker
Write-Host "🚀 Starting backend and worker..." -ForegroundColor Yellow
docker-compose up -d backend worker

# Wait for backend to be ready
Write-Host "⏳ Waiting for backend to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Run database migrations
Write-Host "🗄️  Running database migrations..." -ForegroundColor Yellow
try {
    docker-compose exec backend alembic upgrade head
} catch {
    Write-Host "⚠️  Migration failed - this might be expected on first run" -ForegroundColor Yellow
}

# Start frontend
Write-Host "🚀 Starting frontend..." -ForegroundColor Yellow
docker-compose up -d frontend

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Access the application at:" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:3000"
Write-Host "   Backend API: http://localhost:8000"
Write-Host "   API Docs: http://localhost:8000/docs"
Write-Host "   Flower (Celery Monitor): http://localhost:5555"
Write-Host ""
Write-Host "📝 Useful commands:" -ForegroundColor Cyan
Write-Host "   View logs: docker-compose logs -f"
Write-Host "   Stop services: docker-compose down"
Write-Host "   Restart services: docker-compose restart"
Write-Host ""
