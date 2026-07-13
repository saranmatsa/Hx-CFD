# HX CFD Platform

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Rust 1.70+](https://img.shields.io/badge/Rust-1.70%2B-orange.svg)](https://www.rust-lang.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue.svg)](https://www.typescriptlang.org/)

**A unified desktop and web-based platform for computational fluid dynamics: upload CAD models, generate meshes, run simulations, and visualize results—all without leaving your application.**

---

## The Problem

Traditional CFD workflows fragment work across multiple disconnected tools:

- Export geometry from CAD software (FreeCAD, SolidWorks, Fusion 360)
- Manually configure mesh parameters in Gmsh
- Edit OpenFOAM case files and boundary conditions by hand
- Execute simulations from command-line terminals
- Export results to external visualization software (ParaView)
- Repeat iterations when parameters change, re-doing setup each time

This context-switching creates friction, introduces errors, makes workflows hard to reproduce, and prevents team collaboration on parameter studies.

---

## The Solution

HX CFD Platform provides a unified desktop application that connects your entire CAD-to-results workflow:

- **No command-line required** — Configure and run simulations through an intuitive desktop interface
- **Automatic mesh generation** — Upload STEP/IGES files, specify element sizing, generate meshes instantly
- **Integrated simulation execution** — Run OpenFOAM solvers with form-based configuration
- **Built-in visualization** — View scalar and vector fields in 3D without exporting
- **Project organization** — Manage geometries, meshes, simulations, and results in structured workspaces
- **Dependency management** — Automatic detection and installation of required tools

---

## Key Features

### ✅ Implemented

| Feature | Status | Notes |
|---------|--------|-------|
| **CAD Import** | Available | STEP, IGES, and other supported formats via FreeCAD |
| **Mesh Generation** | Available | Gmsh integration with configurable element size, growth rate, and boundary layers |
| **OpenFOAM Integration** | Available | Supports simpleFoam, pimpleFoam, interFoam, rhoCentralFoam, dnsFoam |
| **Turbulence Models** | Available | kEpsilon, kOmega, SpalartAllmaras, LES models |
| **Results Visualization** | Available | Scalar and vector field extraction via VTK with interactive 3D viewer |
| **Project Management** | Available | Organize geometries, meshes, simulations, results; track iterations |
| **Desktop Application** | Available | Tauri-based native desktop app (Windows, macOS, Linux) |
| **Backend API** | Available | FastAPI REST service for programmatic access |
| **Backend Process Management** | Available | Automatic startup, monitoring, and lifecycle management |
| **System Information** | Available | CPU, memory, OS detection for dependency verification |

### ⚠️ Experimental

| Feature | Status | Notes |
|---------|--------|-------|
| **AI-Assisted Configuration** | Experimental | Multi-provider support (OpenAI, Anthropic, Groq, Ollama, LM Studio, NVIDIA NIM, Google Gemini, OpenRouter); configuration validated but not production-tested |
| **Optimization Workflows** | Experimental | Nevergrad and OpenMDAO integrations present; endpoints return placeholder responses |

### 📋 Planned

| Feature | Status | Notes |
|---------|--------|-------|
| **Advanced Visualization** | Planned | Enhanced 3D rendering, field animations, streamlines |
| **Parameter Studies** | Planned | Batch simulation across parameter ranges with comparison |
| **Results Comparison** | Planned | Side-by-side visual and numerical comparison of multiple runs |
| **Multi-User Collaboration** | Planned | Team workspaces, shared projects, concurrent editing |
| **Cloud Integration** | Planned | Distributed job submission and data storage |

---

## System Architecture

### Desktop Application Architecture

```
┌──────────────────────────────────────────────────────┐
│         HX CFD Desktop Application (Tauri)           │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │   Frontend (React + TypeScript + Three.js)     │  │
│  │   • Project dashboard                          │  │
│  │   • CAD import interface                        │  │
│  │   • Mesh configuration UI                       │  │
│  │   • Simulation setup forms                      │  │
│  │   • 3D results viewer                           │  │
│  └────────────────────────────────────────────────┘  │
│                        ↓                              │
│  ┌────────────────────────────────────────────────┐  │
│  │   Tauri Bridge (Rust)                          │  │
│  │   • Backend process lifecycle management       │  │
│  │   • System resource detection                  │  │
│  │   • File system operations                     │  │
│  │   • Logging and monitoring                     │  │
│  └────────────────────────────────────────────────┘  │
│                        ↓                              │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│     CFD Backend (Python FastAPI Sidecar)             │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────────────��───────────────────────┐  │
│  │   REST API (FastAPI)                           │  │
│  │   • Projects and workspace management          │  │
│  │   • Geometry and mesh operations               │  │
│  │   • Simulation execution and monitoring        │  │
│  │   • Results retrieval and export               │  │
│  │   • Health checks and status                   │  │
│  └────────────────────────────────────────────────┘  │
│                        ↓                              │
│  ┌────────────────────────────────────────────────┐  │
│  │   Service Layer                                │  │
│  │   • MeshService: Gmsh integration              │  │
│  │   • SimulationService: OpenFOAM orchestration  │  │
│  │   • OptimizationService: Nevergrad/OpenMDAO   │  │
│  │   • VisualizationService: VTK post-processing │  │
│  │   • AIService: LLM provider integrations       │  │
│  └────────────────────────────────────────────────┘  │
│                        ↓                              │
│  ┌────────────────────────────────────────────────┐  │
│  │   External Tools                               │  │
│  │   • OpenFOAM: CFD simulation solver            │  │
│  │   • Gmsh: 3D mesh generation                   │  │
│  │   • FreeCAD: CAD model import                  │  │
│  │   • ParaView: Visualization (optional)         │  │
│  │   • Python Scientific Stack: Compute           │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Component Breakdown

#### Frontend (React + TypeScript)
- **Framework**: React 18+ with TypeScript
- **3D Graphics**: Three.js with react-three-fiber for WebGL rendering
- **State Management**: Zustand for client state, TanStack Query for server state
- **Build Tool**: Vite for fast development and optimized production builds
- **Visualization**: VTK.js for scientific visualization

#### Desktop Layer (Tauri 2)
- **Purpose**: Provide native OS integration without Electron bloat
- **Responsibilities**:
  - Backend process lifecycle (spawn, monitor, restart, shutdown)
  - System information detection (OS, CPU, memory, architecture)
  - File system operations with security sandboxing
  - Logging and event forwarding from backend to frontend
  - Dialog boxes and notifications

#### Backend (Python FastAPI)
- **Framework**: FastAPI with async/await for high-concurrency I/O
- **Database**: SQLAlchemy 2.0 ORM with Alembic migrations; SQLite or PostgreSQL
- **Task Queue**: Celery with Redis for async job execution
- **Logging**: Structlog with rich formatting
- **Validation**: Pydantic v2 for strict type validation

#### Services
- **MeshService**: Wraps Gmsh Python API for mesh generation
- **SimulationService**: Orchestrates OpenFOAM via subprocess, monitors execution
- **OptimizationService**: Provides optimization endpoints using Nevergrad and OpenMDAO
- **VisualizationService**: Extracts VTK-compatible data from simulation results

#### External CFD Tools
- **OpenFOAM**: Industry-standard open-source CFD solver
- **Gmsh**: Automatic 3D finite element mesh generator
- **FreeCAD**: CAD model import and parameter editing
- **ParaView**: Visualization support (optional, for advanced workflows)

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 18+ | UI framework |
| TypeScript | 5.0+ | Type-safe JavaScript |
| Vite | 5.0+ | Build tool and dev server |
| Three.js | Latest | 3D graphics engine |
| react-three-fiber | Latest | React renderer for Three.js |
| VTK.js | Latest | Scientific visualization |
| Zustand | Latest | Lightweight state management |
| TanStack Query | v5+ | Server state management |
| TailwindCSS | Latest | Utility-first CSS framework |

### Desktop (Tauri)

| Technology | Version | Purpose |
|-----------|---------|---------|
| Tauri | 2.0+ | Desktop application framework |
| Rust | 1.70+ | System-level operations |
| Tokio | 1.30+ | Async runtime |
| Serde | 1.0+ | Serialization |

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Core language |
| FastAPI | 0.109+ | REST API framework |
| Uvicorn | 0.27+ | ASGI server |
| Pydantic | 2.5+ | Data validation |
| SQLAlchemy | 2.0+ | ORM |
| Alembic | 1.13+ | Database migrations |
| Celery | 5.3+ | Async task queue |
| Redis | 5.0+ | Message broker and cache |
| NumPy | 1.26+ | Numerical computing |
| SciPy | 1.12+ | Scientific algorithms |
| Pandas | 2.1+ | Data manipulation |

### CFD Tools

| Tool | Purpose | License |
|------|---------|---------|
| OpenFOAM | CFD solver | GPL-3.0 |
| Gmsh | Mesh generation | GPL-3.0 |
| FreeCAD | CAD import | LGPL-2.1 |
| ParaView | Visualization | BSD-3-Clause |

### Scientific Libraries

| Library | Purpose |
|---------|---------|
| Meshio | Mesh I/O and format conversion |
| PyVista | 3D data structures and visualization |
| Trimesh | 3D geometry processing |
| VTK | Scientific visualization |
| Nevergrad | Gradient-free optimization |
| OpenMDAO | Multidisciplinary design optimization |
| PhysicsNeMo | NVIDIA physics simulation framework |

---

## Repository Structure

```
HXCFD/
├── README.md                          # This file
├── LICENSE                            # GPL-3.0 license
├── NOTICE                             # Copyright and attribution
├── THIRD_PARTY_LICENCES.md            # Third-party software licenses
├── sonar-project.properties           # SonarQube configuration
│
├── cfd-platform/                      # Main application
│   ├── Cargo.toml                     # Rust dependencies (Tauri)
│   ├── tauri.conf.json                # Tauri application configuration
│   ├── build.py                       # Python backend build script
│   ├── build.rs                       # Rust build script
│   ├── backend.spec                   # PyInstaller specification
│   │
│   ├── src/                           # Tauri frontend (Rust)
│   │   ├── main.rs                    # Application entry point
│   │   ├── backend.rs                 # Backend process manager
│   │   └── commands.rs                # IPC commands
│   │
│   ├── backend/                       # FastAPI backend (Python)
│   │   ├── pyproject.toml             # Python dependencies
│   │   ├── src/cfd_backend/
│   │   │   ├── main.py                # FastAPI app entry point
│   │   │   ├── database.py            # Database configuration
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── projects.py    # Project endpoints
│   │   │   │       ├── meshes.py      # Mesh endpoints
│   │   │   │       ├── simulations.py # Simulation endpoints
│   │   │   │       ├── optimization.py# Optimization endpoints
│   │   │   │       └── visualize.py   # Visualization endpoints
│   │   │   ├── models/
│   │   │   │   ├── base.py            # Base SQLAlchemy models
│   │   │   │   ├── project.py         # Project models
│   │   │   │   ├── mesh.py            # Mesh models
│   │   │   │   ├── simulation.py      # Simulation models
│   │   │   │   └── user.py            # User/auth models
│   │   │   ├── services/
│   │   │   │   ├── mesh_service.py    # Mesh generation service
│   │   │   │   ├── simulation_service.py # CFD execution
│   │   │   │   ├── optimization_service.py# Optimization
│   │   │   │   └── dependencies.py    # Service container
│   │   │   └── core/
│   │   │       ├── config.py          # Settings and configuration
│   │   │       ├── exceptions.py      # Custom exceptions
│   │   │       └── logging.py         # Logging setup
│   │   └── tests/
│   │
│   ├── frontend/                      # React application (TypeScript)
│   │   ├── package.json               # Node dependencies
│   │   ├── src/
│   │   │   ├── main.tsx               # Frontend entry point
│   │   │   ├── App.tsx                # Root component
│   │   │   ├── pages/                 # Route components
│   │   │   ├── components/            # Reusable UI components
│   │   │   ├── hooks/                 # Custom React hooks
│   │   │   ├── services/              # API client services
│   │   │   ├── store/                 # Zustand stores
│   │   │   └── utils/                 # Helper functions
│   │   └── dist/                      # Production build output
│   │
│   └── icons/                         # Application icons
│       ├── 32x32.png
│       ├── 128x128.png
│       ├── icon.icns                  # macOS icon
│       └── icon.ico                   # Windows icon
│
├── hx-cfd-bootstrapper/               # Windows installer (.NET/WPF)
│   ├── HxCfdBootstrapper.csproj       # C# project file
│   ├── appsettings.json               # Configuration
│   ├── components.json                # Component registry
│   └── src/
│       ├── App.xaml                   # Application root
│       ├── MainWindow.xaml            # Main UI window
│       ├── Models/                    # Data models
│       ├── Services/                  # Business logic
│       ├── ViewModels/                # MVVM view models
│       └── Converters/                # XAML value converters
│
└── [submodule references]
    ├── OpenFOAM                       # External CFD solver
    ├── Gmsh                           # Mesh generation tool
    ├── FreeCAD                        # CAD software
    ├── ParaView                       # Visualization tool
    ├── OpenMDAO                       # Optimization framework
    ├── Nevergrad                      # Gradient-free optimization
    └── [others...]
```

---

## Installation

### System Requirements

- **OS**: Windows 10+, macOS 10.13+, or Linux (Ubuntu 20.04+)
- **Python**: 3.10 or later
- **Memory**: 4 GB minimum (8 GB recommended)
- **Disk Space**: 10 GB for tools and dependencies

### Prerequisites

1. **Python 3.10+**
   ```bash
   python --version  # Windows
   python3 --version # macOS/Linux
   ```

2. **Node.js 18+** (for frontend development)
   ```bash
   node --version
   npm --version
   ```

3. **Rust 1.70+** (for building desktop app)
   ```bash
   rustc --version
   cargo --version
   ```

4. **OpenFOAM** (installed and `OPENFOAM_DIR` environment variable set)
   ```bash
   source $OPENFOAM_DIR/etc/bashrc  # Linux/macOS
   # or set OPENFOAM_DIR environment variable on Windows
   ```

5. **Gmsh** (installed and `GMSH_BIN` environment variable set)
   ```bash
   gmsh --version
   ```

### Quick Start with Docker

```bash
cd cfd-platform
docker-compose up -d
```

Access the web interface at `http://localhost:3000`.

### Build Desktop Application

#### Development Build

```bash
cd cfd-platform
npm install                    # Install dependencies
cargo tauri dev                # Run in development mode
```

The application will launch with hot-reloading enabled.

#### Production Build

```bash
cd cfd-platform
cargo tauri build              # Build optimized binary
```

Output locations:
- **Windows**: `src-tauri/target/release/`
- **macOS**: `src-tauri/target/release/bundle/dmg/`
- **Linux**: `src-tauri/target/release/bundle/appimage/`

### Run Backend Locally

**Setup virtual environment:**
```bash
cd cfd-platform/backend
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -e ".[dev]"
```

**Run database migrations:**
```bash
alembic upgrade head
```

**Start development server:**
```bash
cfd-backend-dev
# Or with auto-reload:
uvicorn cfd_backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Frontend Development Server

```bash
cd cfd-platform/frontend
npm install
npm run dev
```

Access at `http://localhost:5173` (Vite dev server).

---

## Configuration

### Environment Variables

Create `.env` in `cfd-platform/backend/`:

```bash
# API Configuration
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/cfddb
# For development with SQLite:
# DATABASE_URL=sqlite:///./cfd.db

# External Tools
OPENFOAM_DIR=/opt/openfoam
GMSH_BIN=/usr/bin/gmsh
FREECAD_BIN=/usr/bin/freecad

# Redis (for task queue)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# AI Provider API Keys (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
NIM_API_KEY=
```

### Database Setup

PostgreSQL (production):
```bash
createdb cfddb
alembic upgrade head
```

SQLite (development):
```bash
alembic upgrade head  # Creates ./cfd.db
```

---

## Usage

### Desktop Application Workflow

1. **Launch the application** — Open HX CFD from your applications menu
2. **Create a project** — Name your workspace (e.g., "Airfoil Analysis 2024")
3. **Import CAD geometry** — Drag-and-drop STEP/IGES files or use file browser
4. **Configure mesh** — Set element size, growth rate, boundary layer parameters
5. **Create simulation** — Select OpenFOAM solver, set boundary conditions via forms
6. **Execute pipeline** — Click "Run" to generate mesh and execute simulation
7. **View results** — Inspect pressure, velocity fields in 3D viewer
8. **Export data** — Save results as VTK, CSV, or scientific image formats

### API Usage (Programmatic Access)

```bash
# Get API documentation
curl http://localhost:8000/docs

# List projects
curl http://localhost:8000/api/v1/projects

# Create new project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "description": "My CFD study"}'

# Start mesh generation
curl -X POST http://localhost:8000/api/v1/meshes/generate \
  -F "geometry=@airfoil.step" \
  -F "config={\"element_size\": 0.01}"

# Monitor simulation
curl http://localhost:8000/api/v1/simulations/{sim_id}/status

# Get results
curl http://localhost:8000/api/v1/simulations/{sim_id}/results \
  > results.vtu
```

---

## Desktop Architecture Details

### Backend Lifecycle Management

The Tauri bridge (`src/backend.rs`) manages the Python FastAPI backend:

1. **Auto-Start on Launch**
   - Detects backend executable (PyInstaller-built or Python script)
   - Configures Python environment (PYTHONPATH, unbuffered output)
   - Spawns process with stdout/stderr capture

2. **Log Forwarding**
   - Captures backend logs in real-time
   - Forwards to frontend for display
   - Maintains rolling buffer (1000 latest entries)

3. **Health Monitoring**
   - Periodically pings `/api/health` endpoint
   - Updates frontend with backend status
   - Auto-restarts on crash (configurable)

4. **Graceful Shutdown**
   - Catches window close request
   - Sends SIGTERM to backend
   - Waits up to 10 seconds for clean shutdown
   - Force-kills if timeout exceeded

### Process Models

**Development Mode** (auto-reload):
```
Tauri Window → Backend Script (main.py) → Uvicorn Server
```

**Production Mode** (bundled executable):
```
Tauri Window → PyInstaller Executable (cfd-backend) → Uvicorn Server
```

### Local Services

When running locally or in development:

- **Frontend**: Vite dev server on `http://localhost:5173`
- **Backend**: Uvicorn on `http://localhost:8000`
- **Database**: SQLite in `./cfd.db` or PostgreSQL at configured URL
- **Redis**: Optional, for Celery task queue
- **Tauri IPC Bridge**: Enables Rust↔Frontend communication

---

## Development

### Prerequisites for Contributors

- Rust toolchain (`rustup`)
- Python 3.10+ with pip and venv
- Node.js 18+ with npm
- Git

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/saranmatsa/HXCFD.git
cd HXCFD

# Backend setup
cd cfd-platform/backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -e ".[dev]"

# Frontend setup
cd ../frontend
npm install

# Tauri setup (Rust)
cd ..
cargo build
```

### Running Tests

**Backend tests:**
```bash
cd cfd-platform/backend
pytest                      # All tests
pytest -v                   # Verbose
pytest --cov=src           # With coverage
pytest tests/test_mesh_service.py  # Single file
```

**Frontend tests:**
```bash
cd cfd-platform/frontend
npm run test
npm run test:coverage
```

**Rust tests:**
```bash
cd cfd-platform
cargo test
```

### Code Quality

**Backend formatting and linting:**
```bash
cd cfd-platform/backend
black src/                  # Format
ruff check src/             # Lint
mypy src/                   # Type check
isort src/                  # Sort imports
```

**Frontend formatting:**
```bash
cd cfd-platform/frontend
npm run lint
npm run format
```

### Building Documentation

```bash
cd cfd-platform/backend
pip install -e ".[docs]"
mkdocs serve
# Visit http://localhost:8000
```

---

## Known Limitations

- **Optimization endpoints**: Return placeholder responses; optimization framework integration is not yet production-ready
- **AI features**: Configuration present but not validated in production workflows
- **Team collaboration**: Single-user only; multi-user support planned for future release
- **Large meshes**: Performance may degrade with meshes >10M elements; streaming visualization planned
- **ParaView integration**: Present in configuration but not actively used in current pipeline

---

## Roadmap

### Short-term (Next Release)

- [ ] Stabilize optimization service implementation
- [ ] Add parameter study batch execution
- [ ] Improve error messages and validation feedback
- [ ] Performance optimization for large mesh visualization
- [ ] Documentation improvements

### Mid-term

- [ ] Multi-user collaboration and team workspaces
- [ ] Cloud job submission and distributed execution
- [ ] Results comparison and side-by-side analysis
- [ ] Advanced visualization (streamlines, field animations)
- [ ] Support for additional CFD solvers

### Long-term

- [ ] Web-based portal for remote access
- [ ] Machine learning-assisted parameter optimization
- [ ] Integration with commercial CAD software
- [ ] High-performance computing cluster support
- [ ] Real-time collaborative editing

---

## Contributing

Contributions are welcome. Please follow these guidelines:

### Code Style

- **Python**: Follow PEP 8; use Black formatter, Ruff linter
- **Rust**: Use `cargo fmt` and `clippy`
- **TypeScript**: Use ESLint and Prettier
- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`, etc.)

### Contribution Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make changes and add tests
4. Run linters and tests locally
5. Commit with descriptive messages
6. Push to your fork
7. Open a Pull Request

### Areas for Contribution

- Mesh visualization improvements
- Additional OpenFOAM solver support
- Performance optimization
- Documentation and tutorials
- Bug fixes and issue resolution

---

## Troubleshooting

### Backend fails to start

**Symptoms**: "Backend not found" or "Python not found" errors

**Solutions**:
- Verify Python 3.10+ is installed and in PATH
- Set `PYTHONPATH` environment variable if using development mode
- Run with `CFD_BACKEND_DEBUG=1` for detailed logs

### OpenFOAM not detected

**Solutions**:
- Ensure OpenFOAM is installed
- Set `OPENFOAM_DIR` environment variable
- Verify `$OPENFOAM_DIR/etc/bashrc` exists

### Mesh generation timeout

**Solutions**:
- Reduce element size or mesh complexity
- Increase available disk space
- Check `TEMP` directory has >5 GB free

### High memory usage

**Solutions**:
- Reduce mesh resolution
- Disable visualization during simulation
- Close other applications
- Increase system RAM if needed

---

## License

This project is licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE) for details.

**Summary**: You are free to use, modify, and distribute this software under the terms of GPL-3.0. Any modifications or derived works must also be licensed under GPL-3.0.

### Third-Party Licenses

This project integrates several open-source projects:

| Project | License | Purpose |
|---------|---------|---------|
| OpenFOAM | GPL-3.0 | CFD simulation engine |
| Gmsh | GPL-3.0 | Mesh generation |
| FreeCAD | LGPL-2.1 | CAD model import |
| ParaView | BSD-3-Clause | Visualization toolkit |
| FastAPI | MIT | REST API framework |
| React | MIT | UI framework |
| Tauri | MIT/Apache-2.0 | Desktop framework |
| NumPy | BSD-3-Clause | Scientific computing |
| Pandas | BSD-3-Clause | Data analysis |
| OpenMDAO | Apache-2.0 | Optimization framework |
| Nevergrad | MIT | Gradient-free optimization |

See [THIRD_PARTY_LICENCES.md](THIRD_PARTY_LICENCES.md) for complete attribution and license texts.

---

## Acknowledgements

HX CFD Platform stands on the shoulders of exceptional open-source projects:

- **[OpenFOAM](https://www.openfoam.com/)** — The foundation of modern open-source CFD
- **[Gmsh](https://gmsh.info/)** — Powerful and flexible mesh generation
- **[FreeCAD](https://www.freecad.org/)** — Community-driven CAD platform
- **[FastAPI](https://fastapi.tiangolo.com/)** — Modern, fast web framework
- **[React](https://react.dev/)** — Declarative UI programming
- **[Tauri](https://tauri.app/)** — Lightweight desktop application framework
- **[Three.js](https://threejs.org/)** — Accessible 3D graphics
- **[OpenMDAO](https://openmdao.org/)** — Multidisciplinary design optimization framework

---

## FAQ

**Q: Do I need to install OpenFOAM separately?**  
A: Yes, currently OpenFOAM must be installed and `OPENFOAM_DIR` environment variable must be set. Future releases will include automated installation.

**Q: Can I run this on macOS?**  
A: Yes, the desktop application (Tauri) supports macOS 10.13+. Ensure OpenFOAM and Gmsh are installed via Homebrew or from source.

**Q: What simulation types are supported?**  
A: Currently: incompressible steady-state (simpleFoam), transient (pimpleFoam), multiphase (interFoam), compressible (rhoCentralFoam), and DNS (dnsFoam). More solvers can be added via plugin architecture.

**Q: Can I use this for teaching?**  
A: Yes! The graphical interface removes barriers to CFD learning. Educational use is encouraged under GPL-3.0 terms.

**Q: How large can meshes be?**  
A: Tested up to 10M elements; performance degrades with larger meshes. Streaming visualization is on the roadmap.

**Q: Is cluster support planned?**  
A: Yes, distributed job submission and HPC cluster integration are planned for mid-term roadmap.

**Q: How do I report bugs?**  
A: Open an issue on GitHub with reproduction steps, logs, and system information.

---

## Vision

HX CFD Platform envisions a future where computational fluid dynamics is accessible to every engineer:

- **Accessible**: Intuitive graphical interface removes CFD tooling barriers
- **Integrated**: Unified workflow from geometry to visualization
- **Extensible**: Plugin architecture enables solver and tool additions
- **Open**: GPL-licensed and community-driven development
- **Collaborative**: Team workspaces enable shared CFD research
- **Scalable**: From laptop to high-performance computing clusters

By eliminating context-switching and manual configuration, HX CFD enables engineers to focus on the physics and design optimization that matters.

---

**For questions, issues, or contributions, visit the [GitHub repository](https://github.com/saranmatsa/HXCFD).**
