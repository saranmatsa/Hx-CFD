# CFD Platform - Browser-based CFD Simulation Platform

An open-source browser-based CFD (Computational Fluid Dynamics) platform that enables engineers and researchers to perform CFD simulations directly in the browser on their local machine.

## Features

- **CAD Import & Editing**: Import STEP/STL files, edit CAD parameters interactively
- **Mesh Generation**: Generate computational meshes using Gmsh integration
- **CFD Simulation**: Run OpenFOAM simulations with full solver support
- **Post-Processing**: Analyze and visualize pressure, velocity, streamlines
- **Aerodynamic Coefficients**: Calculate and display drag and lift coefficients
- **3D Visualization**: Interactive browser-based 3D viewer using Three.js/R3F
- **AI Optimization**: Future-ready integration with OpenMDAO and Nevergrad

## Tech Stack

### Core Engines
- OpenFOAM - CFD solver
- Gmsh - Mesh generation
- FreeCAD - CAD operations
- ParaView - Visualization

### Frontend
- React 18
- TypeScript
- Three.js / React Three Fiber
- VTK.js
- Zustand (state management)
- TanStack Query (server state)

### Backend
- FastAPI
- PyVista
- Meshio
- NumPy / SciPy
- Celery (job queue)
- Redis (message broker)

### Optimization
- OpenMDAO
- Nevergrad

## Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker + Docker Compose (Linux)
- 8GB RAM minimum (16GB recommended)

### One-Command Setup

#### Windows
```powershell
.\setup.ps1
```

#### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/cfd-platform.git
cd cfd-platform
```

2. Configure environment:
```bash
cp .env.example .env
```

3. Start with Docker Compose:
```bash
docker-compose up -d
```

4. Run database migrations:
```bash
docker-compose exec backend alembic upgrade head
```

5. Access the application:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Manual Development Setup (Without Docker)

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

**Note**: For manual setup, you'll need PostgreSQL and Redis running locally.

## Architecture

```
cfd-platform/
├── backend/          # FastAPI backend
│   ├── api/          # API endpoints
│   │   ├── __init__.py
│   │   ├── mesh_routes.py
│   │   ├── simulation_routes.py
│   │   ├── visualization_routes.py
│   │   └── pipeline_routes.py    # NEW: Pipeline orchestration API
│   ├── core/         # Core functionality
│   ├── services/     # Business logic
│   │   ├── mesh_service.py
│   │   ├── simulation_service.py
│   │   └── visualization_service.py
│   ├── workers/      # Background job processing
│   ├── integrations/ # External tool integrations
│   │   ├── freecad/  # FreeCAD Python API client
│   │   ├── gmsh/     # Gmsh Python API client
│   │   ├── openfoam/ # OpenFOAM CLI client
│   │   ├── vtk/      # VTK post-processing client
│   │   └── pipeline/ # Pipeline orchestrator
│   └── db/           # Database models
├── frontend/         # React application
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── hooks/       # Custom React hooks
│   │   ├── services/    # API services
│   │   ├── store/       # State management
│   │   └── types/       # TypeScript types
├── shared/           # Shared types and schemas
├── infrastructure/   # Docker, Kubernetes configs
└── docs/             # Documentation
```

## Automated CFD Pipeline

The platform provides a fully automated CFD pipeline that orchestrates multiple tools:

```
STEP/IGES → FreeCAD → Gmsh → OpenFOAM → VTK → Browser
```

### Pipeline Stages

| Stage | Tool | Description |
|-------|------|-------------|
| 1. CAD Import | FreeCAD | Import STEP/IGES files, convert to BREP |
| 2. Geometry Repair | FreeCAD | Fix CAD geometry issues, heal bodies |
| 3. Mesh Generation | Gmsh | Create computational mesh with boundary layers |
| 4. Case Setup | OpenFOAM | Configure boundary conditions, transport properties |
| 5. Simulation | OpenFOAM | Run CFD solver (simpleFoam, pimpleFoam, etc.) |
| 6. Post-Processing | VTK | Convert OpenFOAM results to VTK format |
| 7. Visualization | VTK | Generate images, extract slices, compute streamlines |

### Integration Clients

#### FreeCAD Client (`backend/integrations/freecad/client.py`)
```python
from backend.integrations.freecad import FreeCADClient

client = FreeCADClient()
result = await client.import_step("geometry.step")
boundaries = await client.get_boundary_conditions(result.body_id)
```

#### Gmsh Client (`backend/integrations/gmsh/client.py`)
```python
from backend.integrations.gmsh import GmshClient

client = GmshClient()
mesh = await client.create_mesh(geometry, mesh_size=0.05)
stats = await client.get_mesh_stats(mesh)
```

#### OpenFOAM Client (`backend/integrations/openfoam/client.py`)
```python
from backend.integrations.openfoam import OpenFOAMClient, SolverType

client = OpenFOAMClient()
case = await client.create_case("channel", solver=SolverType.SIMPLE_FOAM)
await client.run_simulation(case, end_time=1000)
```

#### VTK Client (`backend/integrations/vtk/client.py`)
```python
from backend.integrations.vtk import VTKClient

client = VTKClient()
vtk_file = await client.convert_openfoam_to_vtk(case_dir)
image = await client.generate_image(vtk_file, field="pressure")
```

#### Pipeline Orchestrator (`backend/integrations/pipeline/orchestrator.py`)
```python
from backend.integrations.pipeline import CFDOrchestrator, PipelineConfig

orchestrator = CFDOrchestrator(work_dir="/tmp/cfd")
result = await orchestrator.run_pipeline(
    input_file="geometry.step",
    output_dir="./output",
    parameters={"mesh_size": 0.05, "solver": "simpleFoam"}
)
```

### Pipeline API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pipeline/start` | Start a new pipeline job (upload STEP file) |
| GET | `/api/pipeline/status/{job_id}` | Get job status and progress |
| GET | `/api/pipeline/result/{job_id}` | Get final results |
| GET | `/api/pipeline/visualization/{job_id}` | Download visualization image |
| GET | `/api/pipeline/mesh/{job_id}` | Download mesh file |
| GET | `/api/pipeline/case/{job_id}` | Get OpenFOAM case directory info |
| POST | `/api/pipeline/cancel/{job_id}` | Cancel a running job |
| DELETE | `/api/pipeline/{job_id}` | Delete a job |
| GET | `/api/pipeline/jobs` | List all jobs |
| GET | `/api/pipeline/stages` | Get pipeline stage descriptions |

### Example: Start Pipeline Job

```bash
# Upload STEP file and start pipeline
curl -X POST http://localhost:8000/api/pipeline/start \
  -F "file=@geometry.step" \
  -F 'parameters={
    "mesh_size": 0.05,
    "solver": "simpleFoam",
    "end_time": 1000,
    "color_field": "pressure"
  }'

# Response
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Pipeline job created. Processing will begin shortly.",
  "status_url": "/api/pipeline/status/550e8400-e29b-41d4-a716-446655440000"
}
```

### Example: Check Job Status

```bash
curl http://localhost:8000/api/pipeline/status/550e8400-e29b-41d4-a716-446655440000

# Response
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "stages_completed": ["cad_import", "geometry_repair", "mesh_generation"],
  "current_stage": "case_setup",
  "progress": 0.43,
  "errors": [],
  "output_paths": {
    "mesh": "/tmp/cfd_pipeline/output/mesh.msh",
    "brep": "/tmp/cfd_pipeline/output/geometry.brep"
  },
  "execution_time": 45.2
}
```

## API Documentation

API documentation is available at `/api/docs` when the backend is running.

## License

See [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.