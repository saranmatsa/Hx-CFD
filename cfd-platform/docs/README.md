# CFD Platform Documentation

A browser-based Computational Fluid Dynamics (CFD) platform built with React, FastAPI, and OpenFOAM.

## Features

- **Mesh Generation**: Create and manage computational meshes using Gmsh
- **CFD Simulation**: Run simulations with OpenFOAM solvers
- **3D Visualization**: Interactive 3D visualization of results using Three.js and VTK.js
- **Design Optimization**: Optimize designs using OpenMDAO and Nevergrad
- **Project Management**: Organize your CFD projects with full version history

## Architecture

```
cfd-platform/
├── frontend/          # React + TypeScript frontend
├── backend/          # FastAPI backend
├── shared/           # Shared types and schemas
├── infrastructure/   # Docker and Kubernetes configs
└── docs/            # Documentation
```

## Quick Start

### Using Docker Compose

```bash
docker-compose up -d
```

### Manual Setup

#### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Technology Stack

- **Frontend**: React 18, TypeScript, Three.js, React Three Fiber, Zustand, TanStack Query
- **Backend**: FastAPI, SQLAlchemy, Celery, Redis
- **CFD Engines**: OpenFOAM, Gmsh, FreeCAD
- **Visualization**: VTK.js, ParaView
- **Optimization**: OpenMDAO, Nevergrad

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](../LICENSE) file for details.

## Third-Party Licenses

See [THIRD_PARTY_LICENSES.md](../THIRD_PARTY_LICENSES.md) for information about open-source components used in this project.