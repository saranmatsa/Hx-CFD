# HX CFD — Dependency Role Map
### What each of the 14 bundled components is actually used for

This document maps every dependency in the bundle to its specific job in the HX CFD pipeline, which architecture layer it lives in (Python backend `.exe` vs. Tauri/React frontend), and why it's used as-is rather than reimplemented. Read alongside `HX_CFD_Master_Engineering_Prompt.md`.

---

## Pipeline overview

```
Geometry → semantic boundaries → mesh route → solver-native mesh → solve → results → viewport
FreeCAD       HX registry      Gmsh OR      OpenFOAM      OpenFOAM  VTK/PyVista  three.js/r3f/drei
                                  snappyHexMesh
meshio is an on-demand interchange import/export utility, not the canonical mesh pipeline.
```

The compiled Python sidecar orchestrates all stages left of the viewport, but native and heavy workloads run in isolated supervised workers. Only the presentation stack runs in the Tauri webview.

## Phase 11 integration corrections

The detailed lifecycle, storage, data ownership, failure handling, and user abstraction for every repository are defined in HX-CFD-Local-First-Integration-Architecture.md. That document takes precedence wherever earlier role descriptions are simplified or conflict with these rules:

- Tauri/Rust supervises the session and all native child process trees. The sidecar service is FastAPI-based but private, local, and never a user-operated localhost service.
- FreeCADCmd, Gmsh jobs, OpenFOAM/MPI, ParaView batch jobs, and GPU ML jobs are isolated workers. The UI never launches them and never owns their memory.
- Artifact references and validated recipes pass across process boundaries; project state is local, immutable, versioned, and separate from Program Files.
- Route A uses Gmsh plus OpenFOAM gmshToFoam. Route B uses OpenFOAM blockMesh and snappyHexMesh. meshio must not be used to convert MSH into an OpenFOAM polyMesh.
- Repository names are implementation provenance, not ordinary user-facing workflow labels. HX CFD exposes semantic workflow screens, diagnostics, and advanced provenance instead.

---

## 1. Geometry & meshing

### FreeCAD
**Role:** Parametric CAD kernel. This is where the user's 3D geometry — the part or assembly being analyzed (a heat exchanger, duct, enclosure, whatever HX CFD targets) — is defined, edited, and parameterized.
**Used for:** Loading/editing CAD geometry (STEP, IGES, native FreeCAD files), applying parametric changes driven by the optimization loop (Section 3), exporting clean geometry for meshing.
**Layer:** Backend-supervised FreeCADCmd/headless adapter. FreeCAD's own `FreeCAD`/`Part`/`PartDesign` APIs execute in a disposable geometry worker; no FreeCAD GUI is shown to the user.
**Why not reimplemented:** A parametric CAD kernel is a multi-decade engineering effort (boundary representation, constraint solving, STEP/IGES translators). FreeCAD's Open CASCADE-based kernel is the only realistic option short of licensing a commercial kernel.

### Gmsh
**Role:** Mesh generator. Takes the geometry FreeCAD produces and generates the volumetric/surface mesh OpenFOAM needs to solve on.
**Used for:** 2D/3D unstructured mesh generation, mesh refinement control (boundary layers, size fields), batch/scripted meshing driven by the backend so the user never opens a separate meshing GUI.
**Layer:** A disposable backend-supervised mesh worker, using the Gmsh Python API by default and the pinned `gmsh` CLI only where an adapter requires it.
**Why not reimplemented:** Robust unstructured meshing (especially boundary-layer-aware meshing for CFD) is its own deep discipline; Gmsh is a de facto standard specifically because OpenFOAM users rely on it.

### meshio
**Role:** On-demand mesh interchange reader/writer and lightweight structural inspector.
**Used for:** Importing and exporting supported interchange formats, inspecting cell/field structure, and normalizing compatible mesh/result artifacts for downstream visualization. It is **not** the canonical conversion path from Gmsh MSH to OpenFOAM `polyMesh`; that conversion is owned by OpenFOAM `gmshToFoam`, which preserves solver-native patch semantics.
**Layer:** Python backend, inside a disposable mesh or post-processing worker.
**Why not reimplemented:** Every external interchange format has dialect and metadata edge cases. meshio supplies a maintained adapter layer, while HX CFD owns compatibility reporting, semantic patch preservation, artifact provenance, and the decision to accept or reject a conversion.

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
**Layer:** Dedicated local optimization worker, with durable checkpoints and isolated child analysis jobs.
**Why not reimplemented:** OpenMDAO provides the orchestration, convergence, and gradient-management infrastructure for coupled multi-tool optimization loops — recreating this bookkeeping (component graphs, connections, driver interfaces) from scratch would just be a worse copy of OpenMDAO.

### Nevergrad
**Role:** Gradient-free ("black-box") optimizer. Plugs into OpenMDAO as the driver when the objective function (a full CFD run) has no usable analytic gradient.
**Used for:** Searching the design-parameter space (geometry dimensions, operating conditions) when you can't differentiate through a CFD solve directly — genetic algorithms, CMA-ES, and similar strategies from Nevergrad's library.
**Layer:** Local optimization worker, integrated through an HX study adapter rather than exposed directly to the UI.
**Why not reimplemented:** Nevergrad packages a wide, well-tested library of black-box optimization algorithms; picking and correctly implementing even one of these from scratch (e.g. CMA-ES) is substantial work Nevergrad already does correctly.

---

## 4. ML acceleration

### PhysicsNeMo
**Role:** Physics-informed machine learning framework. Used to train and run surrogate models that approximate what OpenFOAM would compute, but orders of magnitude faster — critical for making the Nevergrad/OpenMDAO optimization loop (which needs many pipeline evaluations) tractable.
**Used for:** Training neural surrogate models on prior OpenFOAM runs, then substituting the surrogate for the full solver during exploratory optimization passes (with periodic full-fidelity OpenFOAM runs to validate/retrain).
**Layer:** Separately pinned local GPU worker. GPU/CUDA availability is preflighted and reported; HX does not silently substitute a different execution mode. This is the largest single component in the bundle by disk size.
**Why not reimplemented:** Physics-informed neural network architectures (Fourier neural operators, graph neural network solvers, etc.) are active research-grade implementations; PhysicsNeMo packages NVIDIA's reference implementations correctly and keeps them GPU-optimized.

### PhysicsNeMo-CFD
**Role:** CFD-specific model zoo and utilities built on top of PhysicsNeMo.
**Used for:** Pretrained/pretrainable surrogate architectures specifically shaped for CFD field prediction (pressure/velocity fields over a mesh), rather than generic PhysicsNeMo building blocks — this is what actually gets wired into the OpenMDAO/Nevergrad loop as the fast objective evaluator.
**Layer:** The same isolated, separately version-pinned local GPU worker as PhysicsNeMo.
**Why not reimplemented:** Same reasoning as PhysicsNeMo — this is the CFD-domain-specialized layer NVIDIA maintains on top of the general framework; writing new CFD surrogate architectures is a research project, not an integration task.

---

## 5. Post-processing & data handling

### VTK
**Role:** The foundational visualization/data-model toolkit. Everything else in this section is built on it.
**Used for:** Reading normalized solver/result artifacts, representing simulation fields (scalar/vector fields on unstructured meshes) in memory, and providing the actual rendering pipeline (filters, mappers, renderers) for contours, streamlines, cutting planes, and derived fields.
**Layer:** Disposable backend post-processing worker. VTK does the heavy processing; only decimated geometry, field chunks, and display metadata cross into the frontend.
**Why not reimplemented:** VTK is the industry-standard scientific visualization pipeline (used by ParaView, itself, and most engineering visualization software); its filter/mapper architecture represents decades of accumulated scientific-visualization algorithms.

### PyVista
**Role:** Pythonic wrapper around VTK. This is the actual API the backend code calls — not raw VTK.
**Used for:** All backend-side post-processing logic: loading result fields, computing derived quantities (vorticity, wall shear stress, etc.), generating contour/streamline/slice geometry, and exporting simplified/decimated meshes for the frontend 3D viewport.
**Layer:** Disposable backend post-processing worker, with derived artifacts cached by input and visualization recipe.
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
| 1 | FreeCAD | Geometry / CAD | Supervised FreeCADCmd worker |
| 2 | Gmsh | Route-A meshing / Route-B surface preparation | Supervised mesh worker |
| 3 | meshio | On-demand interchange import/export | Mesh or post worker |
| 4 | OpenFOAM | CFD solve | Backend-supervised process |
| 5 | OpenMDAO | Optimization orchestration | Dedicated optimization worker |
| 6 | Nevergrad | Black-box optimization strategy | Dedicated optimization worker |
| 7 | PhysicsNeMo | ML surrogate framework | Isolated local GPU worker |
| 8 | PhysicsNeMo-CFD | CFD-specific surrogate models | Isolated local GPU worker |
| 9 | VTK | Data model / rendering pipeline | Disposable post-processing worker |
| 10 | PyVista | Post-processing API | Disposable post-processing worker |
| 11 | ParaView | Batch/headless post-processing | Backend-supervised process |
| 12 | three.js | 3D rendering | Frontend (Tauri webview) |
| 13 | react-three-fiber | React ↔ three.js bridge | Frontend (Tauri webview) |
| 14 | drei | Viewport UI helpers | Frontend (Tauri webview) |

**Pattern to notice:** everything computational and data-heavy (1–11) is orchestrated by HX CFD's private local service and runs in the appropriate isolated local worker; it remains off-limits to the ordinary user workflow and is never a user-operated network service. Only final, already-processed, decimated visual geometry and field metadata cross into the UI layer — the boundary that keeps this a native desktop application rather than a disguised local web server.
