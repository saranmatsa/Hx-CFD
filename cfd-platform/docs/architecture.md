# CFD Platform - Architecture Overview

## System Architecture

The CFD Platform follows a modern microservices-inspired architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   React     │  │   Three.js  │  │     VTK.js              │ │
│  │   Frontend  │  │   3D Views  │  │     Scientific Viz      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      Nginx                                   ││
│  │  - SSL Termination  - Load Balancing  - Caching              ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend Services                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   FastAPI   │  │   Celery    │  │     PostgreSQL          │ │
│  │   REST API  │  │   Workers   │  │     Database            │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│         │                │                      │               │
│         └────────────────┼──────────────────────┘               │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │    Redis     │                               │
│                   │   Broker    │                               │
│                   └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CFD Processing Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   OpenFOAM  │  │    Gmsh     │  │      FreeCAD            │ │
│  │  Solvers    │  │   Meshing   │  │    Geometry             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend

**Technology Stack:**
- React 18 with TypeScript
- Three.js for 3D visualization
- React Three Fiber for declarative 3D
- VTK.js for scientific visualization
- Zustand for state management
- TanStack Query for data fetching
- TailwindCSS for styling

**Key Features:**
- Real-time 3D mesh visualization
- Interactive simulation controls
- Results visualization with field plots
- Responsive design

### Backend

**Technology Stack:**
- FastAPI for REST API
- SQLAlchemy for ORM
- Pydantic for data validation
- Celery for async task processing
- Redis for caching and message broker

**API Structure:**
```
/api/v1/
├── auth/           # Authentication endpoints
├── projects/       # Project management
├── meshes/         # Mesh operations
├── simulations/    # Simulation control
├── visualization/  # Visualization data
└── optimization/   # Optimization workflows
```

### Database Schema

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    User     │     │   Project    │     │     Mesh     │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id          │────<│ owner_id     │     │ id           │
│ email       │     │ id           │────<│ project_id   │
│ username    │     │ name         │     │ name         │
│ password    │     │ description  │     │ status       │
│ created_at  │     │ status       │     │ file_path    │
└──────────────┘     └──────────────┘     └──────────────┘
                           │
                           │
                     ┌──────────────┐     ┌──────────────┐
                     │ Simulation   │     │Visualization │
                     ├──────────────┤     ├──────────────┤
                     │ id           │     │ id           │
                     │ project_id   │────>│ project_id   │
                     │ mesh_id      │     │ simulation_id│
                     │ solver       │     │ type         │
                     │ status       │     └──────────────┘
                     └──────────────┘
                           │
                           │
                     ┌──────────────┐
                     │ Optimization │
                     ├──────────────┤
                     │ id           │
                     │ project_id   │
                     │ simulation_id│
                     │ algorithm    │
                     │ status       │
                     └──────────────┘
```

### CFD Processing

**OpenFOAM Integration:**
- Containerized solver execution
- Support for multiple solvers (simpleFoam, pimpleFoam, etc.)
- Real-time progress monitoring
- Automatic result extraction

**Gmsh Integration:**
- Python API for mesh generation
- Configurable mesh parameters
- Multiple mesh types support

**Optimization:**
- OpenMDAO for multidisciplinary optimization
- Nevergrad for gradient-free optimization
- Parallel evaluation support

## Data Flow

### Mesh Generation

```
User Request → API → Mesh Service → Gmsh → File Storage → Response
```

### Simulation Execution

```
User Request → API → Create Simulation Record
                    ↓
              Celery Task → OpenFOAM Container
                    ↓
              Progress Updates → WebSocket → Frontend
                    ↓
              Results → File Storage → Database Update
```

### Visualization

```
User Request → API → Load VTK Data → Process → Frontend 3D Render
```

## Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS protection
- Rate limiting
- Input validation with Pydantic
- SQL injection prevention via ORM

## Scalability

- Horizontal scaling via Kubernetes
- Redis caching for frequently accessed data
- Celery workers for async processing
- Database connection pooling
- Static file caching in nginx