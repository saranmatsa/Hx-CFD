# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-01

### Added

- Initial project structure
- Backend FastAPI application with:
  - User authentication (JWT)
  - Project management
  - Mesh generation with Gmsh
  - Simulation execution with OpenFOAM
  - Visualization data endpoints
  - Optimization workflows
- Frontend React application with:
  - Login page
  - Dashboard with project list
  - Project detail view
  - Simulation viewer with 3D visualization
- Docker and Kubernetes deployment configurations
- Shared TypeScript and Python types
- API documentation
- Development guide
- Deployment guide

### Technology Stack

- **Frontend**: React 18, TypeScript, Three.js, Zustand, TanStack Query
- **Backend**: FastAPI, SQLAlchemy, Celery, Redis
- **CFD**: OpenFOAM, Gmsh, FreeCAD
- **Visualization**: VTK.js, ParaView
- **Optimization**: OpenMDAO, Nevergrad