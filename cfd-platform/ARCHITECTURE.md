# CFD Platform Architecture

> **Status**: Updated for React-only architecture (2026-07-06)
> **Previous**: Lit Elements hybrid architecture
> **Current**: React 18 with TypeScript

## Overview

Interactive real-time engineering analysis workspace with progressive fidelity simulation.
Local-first design with encrypted local storage, supporting multiple AI providers for
CAD geometry processing, mesh generation, CFD simulation, and optimization.

## Technology Stack

### Frontend
- **Framework**: React 18 + TypeScript
- **Build**: Vite 5.x
- **State**: Zustand with persist middleware (encrypted localStorage)
- **Routing**: React Router v6
- **Data Fetching**: TanStack Query v5
- **3D Visualization**: @react-three/fiber + @react-three/drei
- **Styling**: Tailwind CSS
- **Testing**: Vitest + Playwright

### Backend
- **Framework**: Python/FastAPI
- **Database**: SQLite (local), PostgreSQL (production)
- **Task Queue**: Background tasks for long-running simulations
- **Real-time**: Server-Sent Events (SSE) for progress streaming

### AI Providers (8 supported)
1. NVIDIA NIM
2. OpenAI (GPT-4, o1)
3. Anthropic (Claude)
4. OpenRouter
5. Ollama (local)
6. LM Studio (local)
7. Google Gemini
8. Groq

## Frontend Architecture

### Key Patterns
- **Components**: Functional React components with hooks
- **State Management**: Zustand stores with persistence
- **API Layer**: TanStack Query for caching, api.ts service for requests
- **3D**: React Three Fiber with declarative Three.js

### Directory Structure
```
frontend/src/
├── components/     # Reusable UI components
├── pages/          # Route-level page components
├── store/          # Zustand state stores
├── services/       # API client, AI provider services
├── hooks/          # Custom React hooks
├── utils/          # Pure utility functions
└── types/          # TypeScript type definitions
```

### Store Architecture
- `providerStore.ts`: AI provider configuration (encrypted)
- `projectStore.ts`: Project selection state
- `viewerStore.ts`: 3D viewer state (camera, field, color scale)

## Backend Architecture

### FastAPI Application
- **Location**: `backend/`
- **Port**: 8080
- **Routers**: projects, meshes, simulations, visualization, optimization, pipeline

### API Endpoints
```
/api/projects/          # Project CRUD
/api/meshes/           # Mesh operations
/api/simulations/      # Simulation management
/api/visualization/    # 3D data processing
/api/optimization/     # Design optimization
/api/pipeline/         # Workflow orchestration
```

## Migration Status

### Completed
- ✅ Phase 1: Codebase audit
- ✅ React-only direction confirmed
- ✅ index.html created for Vite entry point
- ✅ Package.json updated with React dependencies

### In Progress
- 🔄 Phase 2: Architecture documentation (this document)
- 🔄 Phase 3: Foundation work

### Pending
- ⏳ Phase 4: Core UI components
- ⏳ Phase 5: 3D visualization integration
- ⏳ Phase 6: AI integration
- ⏳ Phase 7: Backend API completion
- ⏳ Phase 8: Testing setup
- ⏳ Phase 9: Documentation
- ⏳ Phase 10: Docker/infrastructure
- ⏳ Phase 11: Performance optimization
- ⏳ Phase 12: Deployment

## ADR - Architecture Decision Log

### ADR-001: React over Lit Elements
**Date**: 2026-07-06
**Decision**: Use React 18 instead of Lit Elements
**Rationale**: 
- Team familiarity with React patterns
- Better ecosystem for complex state management
- Easier integration with TanStack Query
- Mature React Three Fiber for 3D

### ADR-002: Zustand over Redux
**Date**: 2026-07-06
**Decision**: Use Zustand with persist middleware
**Rationale**:
- Simpler API than Redux
- Built-in persistence with encryption
- Good TypeScript support
- Minimal boilerplate

### ADR-003: Local-First Architecture
**Date**: 2026-07-06
**Decision**: Prioritize local storage with optional cloud sync
**Rationale**:
- Better offline support
- Privacy for sensitive engineering data
- Reduced infrastructure costs
- Faster iteration for individual users