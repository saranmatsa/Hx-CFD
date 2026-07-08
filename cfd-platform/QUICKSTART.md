# Quick Start Guide

This guide will help you get the CFD Platform running on your local machine using Docker Compose.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker + Docker Compose (Linux)
- Git
- At least 8GB RAM available for Docker

## One-Command Setup

### Windows
```powershell
.\setup.ps1
```

### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
```

## Manual Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd cfd-platform
```

### 2. Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env if needed (default values work for local development)
# The defaults are set for localhost development
```

### 3. Start Services
```bash
# Start all services
docker-compose up -d

# Or start services individually
docker-compose up -d postgres redis
docker-compose up -d backend worker
docker-compose up -d frontend
```

### 4. Run Database Migrations
```bash
docker-compose exec backend alembic upgrade head
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Flower (Celery Monitor)**: http://localhost:5555

## Development Workflow

### Hot Reload
Both backend and frontend support hot reload during development:
- Backend: Changes to Python files automatically restart the server
- Frontend: Changes to React files automatically refresh the browser

### View Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f worker
```

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (cleans database)
docker-compose down -v
```

### Run Tests
```bash
# Backend tests
docker-compose exec backend pytest backend/tests/ -v

# Frontend tests
docker-compose exec frontend npm test
```

### Run Linting
```bash
# Backend linting
docker-compose exec backend ruff check backend/
docker-compose exec backend black --check backend/

# Frontend linting
docker-compose exec frontend npm run lint
```

## Troubleshooting

### Port Already in Use
If ports are already in use, change them in `.env`:
```env
BACKEND_PORT=8001
FRONTEND_PORT=3001
```

### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Backend Not Starting
```bash
# Check backend logs
docker-compose logs backend

# Rebuild backend image
docker-compose build backend
docker-compose up -d backend
```

### Frontend Not Loading
```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend image
docker-compose build frontend
docker-compose up -d frontend
```

## Project Structure

```
cfd-platform/
├── backend/           # FastAPI backend
│   ├── api/          # API endpoints
│   ├── core/         # Core functionality
│   ├── services/     # Business logic
│   └── tests/        # Backend tests
├── frontend/         # React frontend
│   ├── src/          # Source code
│   └── tests/        # Frontend tests
├── infrastructure/   # Docker configs
├── docker-compose.yml # Docker Compose configuration
└── .env             # Environment variables
```

## Next Steps

1. Read the [Architecture Documentation](ARCHITECTURE.md) to understand the system design
2. Check the [API Documentation](http://localhost:8000/docs) to explore available endpoints
3. Review the [Local Development Guide](docs/DEPLOYMENT.md) for detailed development instructions

## Getting Help

- Check logs: `docker-compose logs -f`
- Review documentation in the `docs/` directory
- Open an issue on GitHub for bugs or questions
