# Local Development Guide

This guide covers running the CFD Platform locally using Docker Compose.

## Quick Start

```bash
# One-command setup
./setup.sh  # Linux/Mac
.\setup.ps1 # Windows

# Or manual setup
cp .env.example .env
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Flower (Celery Monitor)**: http://localhost:5555

## Development Features

- **Hot Reload**: Both backend and frontend automatically reload on code changes
- **Volume Mounts**: Code changes are reflected immediately
- **Debug Mode**: Full error messages and debug logging enabled

See [QUICKSTART.md](../QUICKSTART.md) for detailed local development instructions.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker + Docker Compose (Linux)
- 8GB RAM minimum (16GB recommended)

## Environment Variables

Copy `.env.example` to `.env` and configure as needed. Default values work for local development.

### Key Settings

```env
# Database
POSTGRES_USER=cfd_user
POSTGRES_PASSWORD=cfd_password
POSTGRES_DB=cfd_platform

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
FLOWER_PORT=5555

# CFD Tools (optional, for local tool integration)
OPENFOAM_DIR=/opt/OpenFOAM
GMSH_BIN=/usr/bin/gmsh
FREECAD_BIN=/usr/bin/freecad
```

## Docker Compose Services

- **frontend**: React application with hot-reload
- **backend**: FastAPI application with hot-reload
- **worker**: Celery worker for background tasks
- **postgres**: PostgreSQL database
- **redis**: Redis for Celery broker
- **flower**: Celery monitoring interface

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### View Logs
```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Services
```bash
docker-compose restart
```

### Stop Services
```bash
docker-compose down
```

### Clean Start (removes database)
```bash
docker-compose down -v
docker-compose up -d
```

### Run Database Migrations
```bash
docker-compose exec backend alembic upgrade head
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
Change ports in `.env`:
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

## Database Migrations

The platform uses Alembic for database migrations.

### Run Migrations

```bash
docker-compose exec backend alembic upgrade head
```

### Create New Migration

```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

### Migration Files

Migration files are located in `backend/alembic/versions/`. The initial migration (001_initial_migration.py) creates the core database schema including users, projects, meshes, and simulations tables.

## Health Checks

The backend provides health check endpoints:

- `/api/health`: Basic health check
- `/metrics`: Prometheus metrics endpoint

## Monitoring

### Prometheus Metrics

The backend exposes Prometheus metrics at `/metrics`:

- Request latency (histogram)
- Request count (counter)
- Error rates (counter)
- Active simulations (gauge)
- System memory usage (gauge)
- System CPU usage (gauge)

### Structured Logging

The platform uses structured logging. Configure logging in `core/logging_config.py`:
```python
setup_logging(log_level="INFO", log_file="/var/log/cfd-platform/app.log")
```

## Security

### Security Scanning

Run security scans locally:

```bash
# Python dependency check
pip install safety
safety check

# Python SAST
pip install bandit
bandit -r backend/

# Node.js dependency check
cd frontend
npm audit
```

### Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U cfd_user cfd_platform > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U cfd_user cfd_platform < backup.sql
```