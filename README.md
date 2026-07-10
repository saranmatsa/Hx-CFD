# CFD Platform

**A web-based workflow platform for computational fluid dynamics: upload CAD models, generate meshes, run simulations, and visualize results—all from a single interface.**

---

## The Problem

CFD workflows typically require juggling multiple disconnected tools:

- Export geometry from CAD software
- Manually configure mesh generation parameters in Gmsh or similar
- Set up case files and boundary conditions for OpenFOAM
- Run simulations from the command line
- Export results to separate visualization software
- Repeat iterations manually when parameters change

This fragmentation means context-switching between applications, manual file transfers, and difficulty reproducing or sharing workflows across a team.

---

## The Solution

CFD Platform provides a unified web interface that connects your CAD-to-results workflow:

- **No command-line required** — configure and run simulations through a browser
- **Automatic mesh generation** — upload STEP/IGES files, specify element sizing, generate meshes without opening separate software
- **Real-time progress tracking** — monitor simulation status and residuals as jobs run
- **Integrated visualization** — view scalar and vector fields without exporting to external tools
- **Project organization** — manage geometries, meshes, simulations, and results in structured projects

---

## Key Features

### Mesh Generation from CAD Files
Upload STEP or IGES geometry files directly. Configure element size, growth rate, and boundary layer settings through the interface. Generate meshes without leaving the browser.

### Simulation Execution
Run OpenFOAM solvers (simpleFoam, pimpleFoam, interFoam, and others) with configurable turbulence models. Set up cases through form-based inputs rather than editing text files manually.

### Results Visualization
View pressure, velocity, and other scalar fields directly in the browser. Extract vector fields and examine results without exporting to ParaView or other visualization tools.

### Pipeline Automation
Chain mesh generation, simulation, and visualization steps into automated pipelines. Upload a CAD file, specify configuration, and receive results when the pipeline completes.

### Project Management
Organize work into projects containing geometries, meshes, simulations, and results. Track iterations and compare outcomes across parameter studies.

### Multi-Provider AI Configuration
Connect to NVIDIA NIM, OpenAI, Anthropic, Ollama, LM Studio, Groq, Google Gemini, or OpenRouter for AI-assisted parameter configuration. *(AI integration is experimental—see Project Status below.)*

---

## Example Workflow

1. **Create a project** named "Airfoil Analysis"
2. **Upload** a STEP file containing your geometry
3. **Configure mesh** — set element size to 0.01m, enable boundary layers with 3 layers
4. **Create a simulation** — select simpleFoam solver with k-epsilon turbulence model
5. **Start the pipeline** — the platform generates the mesh, runs the simulation, and extracts results
6. **View results** — examine pressure distribution and velocity fields in the built-in viewer
7. **Iterate** — adjust parameters and re-run without re-uploading geometry

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (SQLite works for development)
- Redis 6+
- OpenFOAM installed and `OPENFOAM_DIR` environment variable set
- Gmsh installed and `GMSH_BIN` environment variable set

### Run with Docker Compose

```bash
cd cfd-platform
docker-compose up -d
```

Access the web interface at `http://localhost:3000`.

### Run Locally

**Backend:**

```bash
cd cfd-platform
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Frontend:**

```bash
cd cfd-platform/frontend
npm install
npm run dev
```

Access the web interface at `http://localhost:5173`.

---

## Installation

### Environment Variables

Create a `.env` file in `cfd-platform/` with:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/cfddb
# Or for development:
# DATABASE_URL=sqlite:///./cfd.db

# External Tools
OPENFOAM_DIR=/path/to/OpenFOAM
GMSH_BIN=/path/to/gmsh
FREECAD_BIN=/path/to/freecad

# Optional: AI Provider API Keys
NIM_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
```

### Database Setup

```bash
cd cfd-platform
alembic upgrade head
```

### Frontend Configuration

```bash
cd cfd-platform/frontend
cp .env.example .env  # Configure API endpoint if not running locally
```

---

## Usage

### Web Interface

1. **Dashboard** — Overview of projects and recent activity
2. **Projects** — Create and manage project workspaces
3. **Upload** — Drag-and-drop CAD files (STEP, IGES)
4. **Simulations** — Configure and launch simulation runs
5. **Pipeline** — Monitor automated workflow execution
6. **Settings** — Configure AI providers and system dependencies

### API Access

The backend exposes a REST API at `/api/v1/`. Authenticate with JWT tokens:

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Create project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project"}'

# Start pipeline
curl -X POST http://localhost:8000/api/v1/pipeline/start \
  -H "Authorization: Bearer <token>" \
  -F "file=@geometry.step" \
  -F "project_id=<uuid>" \
  -F "config={\"element_size\": 0.1, \"solver\": \"simpleFoam\"}"
```

---

## Supported Workflows
### Available

| Workflow | Status | Notes |
|----------|--------|-------|
| CAD file upload (STEP, IGES) | Available | Drag-and-drop interface |
| Mesh generation (Gmsh) | Available | Configurable element size, growth rate, boundary layers |
| OpenFOAM simulation | Available | Supports simpleFoam, pimpleFoam, interFoam, rhoCentralFoam, dnsFoam |
| Turbulence models | Available | kEpsilon, kOmega, SpalartAllmaras, LES models |
| Results visualization | Available | Scalar and vector field extraction via VTK |
| Pipeline automation | Available | End-to-end CAD-to-results workflow |
| Project management | Available | Organize geometries, meshes, simulations |
| Multi-user access | Available | JWT authentication |

### Experimental

| Feature | Status | Notes |
|---------|--------|-------|
| AI-assisted configuration | Experimental | Connects to LLM providers; not fully validated |
| Optimization workflows | Experimental | Endpoints exist but return placeholder data |

### Planned

| Feature | Status | Notes |
|---------|--------|-------|
| Advanced visualization | Planned | Enhanced 3D rendering and animation |
| Parameter studies | Planned | Batch simulation across parameter ranges |
| Results comparison | Planned | Side-by-side comparison of simulation results |

---

## Project Status

CFD Platform is under active development. Core mesh generation, simulation, and visualization workflows are functional. AI-assisted features and optimization workflows are experimental.

**Known limitations:**

- Optimization endpoints return placeholder responses
- AI provider integration is configured but not fully validated in production use
- FreeCAD and ParaView integrations are present in configuration but not actively used in the pipeline

---

## Documentation

- [Quick Start Guide](cfd-platform/QUICKSTART.md)
- [Architecture Overview](cfd-platform/ARCHITECTURE.md)
- [Contributing Guidelines](cfd-platform/CONTRIBUTING.md)
- [Engineering Audit](cfd-platform/ENGINEERING_AUDIT.md)

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](cfd-platform/CONTRIBUTING.md) for guidelines on code style, testing, and pull request process.

Key areas for contribution:

- Visualization improvements
- Additional solver support
- AI integration validation
- Documentation

---

## License

See [LICE# Prompt: Implement Automatic Dependency Installation

Act as a Principal Software Architect, DevOps Engineer, and Platform Engineer.

Implement a complete dependency installation and management system for this application.

## Goal

A new user should be able to clone the repository, run the setup process once, and have every required dependency automatically installed and configured.

The user should never need to manually search for downloads, clone third-party repositories, or configure paths.

## Dependencies to Manage

The installer must support the following external software:

* OpenFOAM
* Gmsh
* FreeCAD
* ParaView
* PyVista
* Meshio
* OpenMDAO
* Nevergrad
* PhysicsNeMo
* PhysicsNeMo CFD
* Three.js
* React Three Fiber
* VTK.js
* Drei

## Installation Strategy

For each dependency:

1. Detect whether it is already installed.
2. Determine the installed version.
3. Verify that it works correctly.
4. If missing, install it using the official installation method.
5. Configure environment variables if required.
6. Register the dependency inside the application.
7. Verify the installation after completion.

Do not hardcode download links if official package managers, release APIs, or package registries exist.

Prefer the official installation mechanism for every dependency.

Examples:

* Python libraries → pip
* JavaScript libraries → npm
* Docker images → Docker
* Official installers → official releases
* AI models → official model manager (for example, Ollama)

## User Interface

Create a Dependency Manager page displaying:

* Name
* Installed
* Missing
* Current Version
* Latest Version
* Install
* Update
* Remove
* Verify
* Installation Progress
* Installation Logs

## Installation Workflow

When the user presses "Install All":

* Check every dependency.
* Skip those already installed.
* Install only missing dependencies.
* Continue if one dependency fails.
* Show progress for every dependency.
* Display a final installation summary.

## Error Handling

Handle:

* Missing internet connection
* Unsupported operating systems
* Permission issues
* Installation failures
* Version conflicts
* Corrupted installations

Provide clear recovery instructions.

## Extensibility

The dependency manager must be modular.

Adding a future dependency should require only implementing a new provider, without changing the core installation engine.

The final implementation should feel similar to professional installers such as Visual Studio Installer, Unity Hub, or Docker Desktop, where users click "Install" and the application manages all required dependencies automatically.
NSE](LICENSE) in the project root.