# Development Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- OpenFOAM (for local CFD simulations)
- Gmsh (for mesh generation)

## Project Structure

```
cfd-platform/
├── frontend/          # React frontend application
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API service modules
│   │   ├── store/        # Zustand state stores
│   │   ├── hooks/        # Custom React hooks
│   │   └── types/        # TypeScript type definitions
│   └── ...
├── backend/          # FastAPI backend application
│   ├── api/         # API route handlers
│   ├── core/        # Core functionality (config, security, etc.)
│   ├── db/          # Database models and schemas
│   ├── schemas/     # Pydantic schemas
│   ├── services/    # Business logic services
│   └── worker/      # Celery worker tasks
├── shared/          # Shared code between frontend and backend
│   ├── types/       # TypeScript types
│   └── schemas/     # Python Pydantic schemas
└── infrastructure/  # Docker and Kubernetes configurations
```

## Setting Up Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/cfd-platform.git
cd cfd-platform
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -m db.init_db

# Run the server
uvicorn main:app --reload
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### 4. Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Running Tests

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

### Frontend Tests

```bash
cd frontend
npm run test
```

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use Black for formatting

### TypeScript

- Follow ESLint rules
- Use strict mode
- Prefer interfaces over types
- Maximum line length: 100 characters

## Adding New Features

### 1. Database Models

Add new models in `backend/db/models.py`:

```python
class NewModel(Base):
    __tablename__ = "new_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 2. Pydantic Schemas

Add schemas in `backend/schemas/`:

```python
class NewModelBase(BaseModel):
    name: str

class NewModelCreate(NewModelBase):
    pass

class NewModelResponse(NewModelBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### 3. API Routes

Add routes in `backend/api/`:

```python
@router.post("/", response_model=NewModelResponse)
def create_new_model(
    data: NewModelCreate,
    db: Session = Depends(get_db)
):
    # Implementation
    pass
```

### 4. Frontend Components

Add components in `frontend/src/components/`:

```typescript
export default function NewComponent() {
  return <div>New Component</div>
}
```

## Deployment

### Docker

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
# Apply configurations
kubectl apply -f infrastructure/k8s/

# Check status
kubectl get pods
```

## Troubleshooting

### Common Issues

1. **Database connection errors**: Check PostgreSQL is running and credentials are correct
2. **Redis connection errors**: Verify Redis is accessible
3. **OpenFOAM not found**: Ensure OpenFOAM is installed and sourced
4. **Port conflicts**: Check no other services are using ports 3000, 8000, or 5432