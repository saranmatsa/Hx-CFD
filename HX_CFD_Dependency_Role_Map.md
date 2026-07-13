# HX CFD — Dependency Role Map
### What each of the 14 bundled components is actually used for

This document maps every dependency in the bundle to its specific job in the HX CFD pipeline, which architecture layer it lives in (Python backend `.exe` vs. Tauri/React frontend), and why it's used as-is rather than reimplemented. Read alongside `HX_CFD_Master_Engineering_Prompt.md`.

---

## Pipeline overview

```
Geometry → Meshing → Solving → Optimization loop → ML acceleration → Post-processing → 3D viewport (UI)
FreeCAD    Gmsh       OpenFOAM   OpenMDAO/Nevergrad   PhysicsNeMo(-CFD)   VTK/PyVista/ParaView   three.js/r3f/drei
                       ↑______________meshio (format bridge between every stage)______________↑
```

All stages left of the viewport run inside the compiled Python backend `.exe` (the sidecar process). Only the last stage runs in the Tauri webview.

---

## 1. Geometry & meshing

### FreeCAD
**Role:** Parametric CAD kernel. This is where the user's 3D geometry — the part or assembly being analyzed (a heat exchanger, duct, enclosure, whatever HX CFD targets) — is defined, edited, and parameterized.
**Used for:** Loading/editing CAD geometry (STEP, IGES, native FreeCAD files), applying parametric changes driven by the optimization loop (Section 3), exporting clean geometry for meshing.
**Layer:** Python backend (FreeCAD ships its own Python API — `FreeCAD`/`Part`/`PartDesign` modules — invoked headlessly from the backend `.exe`, no FreeCAD GUI is shown to the user).
**Why not reimplemented:** A parametric CAD kernel is a multi-decade engineering effort (boundary representation, constraint solving, STEP/IGES translators). FreeCAD's Open CASCADE-based kernel is the only realistic option short of licensing a commercial kernel.

### Gmsh
**Role:** Mesh generator. Takes the geometry FreeCAD produces and generates the volumetric/surface mesh OpenFOAM needs to solve on.
**Used for:** 2D/3D unstructured mesh generation, mesh refinement control (boundary layers, size fields), batch/scripted meshing driven by the backend so the user never opens a separate meshing GUI.
**Layer:** Python backend (via Gmsh's Python API, or the bundled `gmsh` CLI binary invoked as a subprocess).
**Why not reimplemented:** Robust unstructured meshing (especially boundary-layer-aware meshing for CFD) is its own deep discipline; Gmsh is a de facto standard specifically because OpenFOAM users rely on it.

### meshio
**Role:** Universal mesh-format translator. The glue between every tool above and below it in the pipeline.
**Used for:** Converting Gmsh's native mesh format into OpenFOAM's `polyMesh` format, and converting OpenFOAM/solver output meshes into formats VTK/PyVista/ParaView can read (VTU, VTK legacy, XDMF, etc.) without the user ever touching a converter.
**Layer:** Python backend (pure Python library, imported directly).
**Why not reimplemented:** Every one of these tools uses a slightly different mesh file dialect; meshio already solves this translation problem comprehensively and is maintained specifically to stay in sync with new format revisions.

---

## 2. Solving

### OpenFOAM
**Role:** The CFD solver itself — this is the computational core of HX CFD. Everything upstream exists to feed it a mesh + boundary conditions; everything downstream exists to consume its results.
**Used for:** Running the actual fluid-flow / heat-transfer simulation (whichever solver variant HX CFD targets — e.g. `simpleFoam`, `pimpleFoam`, `chtMultiRegionFoam`), reading its convergence residuals for live progress reporting in the UI.
**Layer:** Backend-managed native process. OpenFOAM's own binaries (Linux-native tools, run here via the bundled WSL/native-Windows build depending on which OpenFOAM-for-Windows distribution is packaged) are spawned and supervised as a background child process by the Rust core, with stdout/residual parsing piped back to the UI for live progress — this is the "background process" requirement from the master prompt.
**Why not reimplemented:** OpenFOAM is a ~20-year, million-line C++ CFD codebase implementing the finite-volume method, turbulence models, and multiphysics solvers. Reimplementing any meaningful fraction of it is out of scope for any application-layer project.

---

## 3. Optimization loop

### OpenMDAO
**Role:** Multidisciplinary design optimization (MDO) framework. Wraps the geometry→mesh→solve→post-process pipeline into a single differentiable/iterable "analysis" that an optimizer can drive.
**Used for:** Defining the design variables (geometry parameters from FreeCAD), the objective/constraints (derived from OpenFOAM results), and orchestrating repeated pipeline runs during an optimization study (e.g. "find the fin geometry that minimizes pressure drop for a given heat duty").
**Layer:** Python backend.
**Why not reimplemented:** OpenMDAO provides the orchestration, convergence, and gradient-management infrastructure for coupled multi-tool optimization loops — recreating this bookkeeping (component graphs, connections, driver interfaces) from scratch would just be a worse copy of OpenMDAO.

### Nevergrad
**Role:** Gradient-free ("black-box") optimizer. Plugs into OpenMDAO as the driver when the objective function (a full CFD run) has no usable analytic gradient.
**Used for:** Searching the design-parameter space (geometry dimensions, operating conditions) when you can't differentiate through a CFD solve directly — genetic algorithms, CMA-ES, and similar strategies from Nevergrad's library.
**Layer:** Python backend, invoked as an OpenMDAO driver plugin.
**Why not reimplemented:** Nevergrad packages a wide, well-tested library of black-box optimization algorithms; picking and correctly implementing even one of these from scratch (e.g. CMA-ES) is substantial work Nevergrad already does correctly.

---

## 4. ML acceleration

### PhysicsNeMo
**Role:** Physics-informed machine learning framework. Used to train and run surrogate models that approximate what OpenFOAM would compute, but orders of magnitude faster — critical for making the Nevergrad/OpenMDAO optimization loop (which needs many pipeline evaluations) tractable.
**Used for:** Training neural surrogate models on prior OpenFOAM runs, then substituting the surrogate for the full solver during exploratory optimization passes (with periodic full-fidelity OpenFOAM runs to validate/retrain).
**Layer:** Python backend. GPU-accelerated where a local CUDA-capable GPU is present; falls back to CPU otherwise. This is the largest single component in the bundle by disk size.
**Why not reimplemented:** Physics-informed neural network architectures (Fourier neural operators, graph neural network solvers, etc.) are active research-grade implementations; PhysicsNeMo packages NVIDIA's reference implementations correctly and keeps them GPU-optimized.

### PhysicsNeMo-CFD
**Role:** CFD-specific model zoo and utilities built on top of PhysicsNeMo.
**Used for:** Pretrained/pretrainable surrogate architectures specifically shaped for CFD field prediction (pressure/velocity fields over a mesh), rather than generic PhysicsNeMo building blocks — this is what actually gets wired into the OpenMDAO/Nevergrad loop as the fast objective evaluator.
**Layer:** Python backend, on top of PhysicsNeMo.
**Why not reimplemented:** Same reasoning as PhysicsNeMo — this is the CFD-domain-specialized layer NVIDIA maintains on top of the general framework; writing new CFD surrogate architectures is a research project, not an integration task.

---

## 5. Post-processing & data handling

### VTK
**Role:** The foundational visualization/data-model toolkit. Everything else in this section is built on it.
**Used for:** Reading solver output (via meshio-converted files), representing simulation fields (scalar/vector fields on unstructured meshes) in memory, and providing the actual rendering pipeline (filters, mappers, renderers) that produces the pixels for contour plots, streamlines, cutting planes, etc.
**Layer:** Python backend (as a dependency of PyVista) — VTK does the heavy data processing (isosurfaces, slicing, interpolation) server-side; only the final geometry/pixel data needed for display crosses into the frontend.
**Why not reimplemented:** VTK is the industry-standard scientific visualization pipeline (used by ParaView, itself, and most engineering visualization software); its filter/mapper architecture represents decades of accumulated scientific-visualization algorithms.

### PyVista
**Role:** Pythonic wrapper around VTK. This is the actual API the backend code calls — not raw VTK.
**Used for:** All backend-side post-processing logic: loading result fields, computing derived quantities (vorticity, wall shear stress, etc.), generating contour/streamline/slice geometry, and exporting simplified/decimated meshes for the frontend 3D viewport.
**Layer:** Python backend.
**Why not reimplemented:** PyVista exists specifically to make VTK's notoriously verbose C++-style API usable from application code without losing any of VTK's capability — using VTK directly would mean reimplementing PyVista's convenience layer for no benefit.

### ParaView
**Role:** Batch/headless post-processing engine (via `pvpython`/`pvbatch`), not a GUI shown to the user.
**Used for:** Heavier post-processing tasks that benefit from ParaView's server-client rendering architecture and its wider filter catalog than PyVista exposes directly (e.g. large time-series animations, specific advanced filters), run as a background batch job by the backend and exporting results/images/data that feed back into the app — never launched as its own visible application window.
**Layer:** Backend-managed background process (ParaView's Python-batch mode, spawned and supervised like OpenFOAM).
**Why not reimplemented:** ParaView's batch engine gives you a second, complementary set of large-scale/parallel post-processing capabilities beyond what PyVista's in-process VTK usage covers, without having to build a distributed rendering/processing pipeline from scratch.

---

## 6. In-app 3D viewport (frontend)

### three.js
**Role:** The WebGL 3D rendering engine actually drawing the interactive 3D viewport inside the Tauri webview.
**Used for:** Rendering the geometry, mesh, and result-field overlays (colored by pressure/velocity/temperature, etc.) that the backend exports (as decimated/simplified geometry + field data from PyVista/VTK) into an interactive, rotatable/zoomable 3D scene — this is the desktop equivalent of a CAD/CFD tool's 3D viewport, e.g. what SolidWorks or ParaView shows in their main window.
**Layer:** Frontend, running inside Tauri's native webview — **not** a browser tab, not reachable via any URL the user could type. It's bundled as a vendored frontend asset, loaded locally from disk by the Tauri app shell.
**Why not reimplemented:** three.js is a mature, GPU-accelerated WebGL abstraction; reimplementing a 3D rendering engine to draw mesh/field data would be reinventing exactly what three.js already does well, for no architectural benefit inside a webview-hosted frontend.

### react-three-fiber
**Role:** React renderer for three.js — lets the 3D viewport be built as React components/state rather than imperative three.js scene-graph code.
**Used for:** Declaratively composing the viewport scene (camera, lights, mesh objects, result overlays, UI controls like clipping planes or colorbar legends) as React components that re-render when the backend pushes new result data.
**Layer:** Frontend, inside the Tauri webview.
**Why not reimplemented:** Since the existing frontend is already React-based, r3f is the standard bridge that lets 3D content participate in the same component/state model as the rest of the UI — bypassing it would mean maintaining two separate UI paradigms (React for panels/menus, raw three.js for the viewport) for no gain.

### drei
**Role:** Helper-component library for react-three-fiber.
**Used for:** Ready-made viewport conveniences — orbit/trackball camera controls, gizmos (view-cube style axis indicators, common in CAD tools), model loaders, environment/lighting helpers — the small but numerous utilities every 3D viewport needs.
**Layer:** Frontend, inside the Tauri webview.
**Why not reimplemented:** drei's components (`OrbitControls`, `GizmoHelper`, `Html`, etc.) are exactly the boilerplate every r3f-based viewport needs; each one individually is simple, but hand-rolling all of them offers no advantage over using the maintained, tested versions.

---

## Quick-reference table

| # | Dependency | Pipeline stage | Runs in |
|---|---|---|---|
| 1 | FreeCAD | Geometry / CAD | Backend `.exe` |
| 2 | Gmsh | Mesh generation | Backend `.exe` |
| 3 | meshio | Format conversion (cross-cutting) | Backend `.exe` |
| 4 | OpenFOAM | CFD solve | Backend-supervised process |
| 5 | OpenMDAO | Optimization orchestration | Backend `.exe` |
| 6 | Nevergrad | Black-box optimizer | Backend `.exe` |
| 7 | PhysicsNeMo | ML surrogate framework | Backend `.exe` (GPU if available) |
| 8 | PhysicsNeMo-CFD | CFD-specific surrogate models | Backend `.exe` (GPU if available) |
| 9 | VTK | Data model / rendering pipeline | Backend `.exe` |
| 10 | PyVista | Post-processing API | Backend `.exe` |
| 11 | ParaView | Batch/headless post-processing | Backend-supervised process |
| 12 | three.js | 3D rendering | Frontend (Tauri webview) |
| 13 | react-three-fiber | React ↔ three.js bridge | Frontend (Tauri webview) |
| 14 | drei | Viewport UI helpers | Frontend (Tauri webview) |

**Pattern to notice:** everything computational and data-heavy (1–11) stays in the Python backend, entirely off-limits to the user and never exposed as a network service. Only the final, already-processed, already-decimated visual result (12–14) crosses into the UI layer — which is exactly the boundary that keeps this a native desktop app rather than a disguised local web server.
