# HX CFD Desktop Engine Integration Matrix

HX CFD invokes engineering work only through the typed desktop bridge:

`React → Tauri command → private backend contract → LocalWorkflowService → EngineeringOrchestrator → repository adapter → local artifact`

The frontend does not call a localhost port, and it does not synthesize a successful run when a local tool is missing.

## Workflow mapping

| Desktop workflow | Tauri command | Service and adapter | Engines | Published artifacts |
| --- | --- | --- | --- | --- |
| Prepare Geometry | `execute_workflow_stage("geometry")` | `LocalWorkflowService.execute_stage` → `EngineeringOrchestrator._prepare_geometry` | FreeCAD headless when available; otherwise Gmsh/OpenCASCADE for STEP, IGES, and BREP solids | `prepared.step` (FreeCAD) or `prepared.brep` (Gmsh), `geometry-report.json` |
| Generate Mesh | `execute_workflow_stage("meshing")` | `_generate_mesh` | Gmsh, meshio, VTK, PyVista; OpenFOAM when installed | A real tetrahedral `mesh.msh`, `mesh.vtk`, real `mesh-preview.png`, `mesh-quality.json`, and an OpenFOAM case only after successful optional conversion/checkMesh |
| Configure Simulation | `execute_workflow_stage("physics")` | `_write_physics_case` | local recipe service | versioned `physics.json` |
| Run Simulation | `execute_workflow_stage("solver")` | `_run_solver` | OpenFOAM | OpenFOAM case and solver log |
| Analyze Results | `execute_workflow_stage("results")` | `_process_results` | OpenFOAM, VTK, PyVista; ParaView if installed | VTK dataset, `result-preview.png`, `result-summary.json`, optional ParaView image |
| Export Report | `execute_workflow_stage("reports")` | `_publish_report` | VTK, PyVista | `report.html` with result metadata |
| Optimize Design (Expert) | `execute_workflow_stage("optimization")` | `_optimize_design` | OpenMDAO, Nevergrad | `optimization.json` and candidate history |
| Train Surrogate (Expert) | `execute_workflow_stage("surrogate")` | `_train_surrogate` | PhysicsNeMo, PhysicsNeMo-CFD | trainer-produced model files and `surrogate.json` |

## Repository validation

| Repository | Adapter and use site | Desktop status at validation | Runtime conclusion |
| --- | --- | --- | --- |
| FreeCAD | `EngineeringOrchestrator._prepare_geometry_with_freecad` | Adapter connected; unavailable locally | Preferred native CAD preparation route when installed; Gmsh handles supported solid exchange files when it is absent. |
| Gmsh | `_prepare_geometry_with_gmsh`, `_gmsh_volume_mesh` | Connected and ready | Uses OpenCASCADE import and `healShapes` for STEP/IGES/BREP solid preparation, then creates the real 3D mesh. |
| meshio | `_mesh_diagnostics` | Connected and ready | Converts the generated Gmsh mesh to VTK. |
| OpenFOAM | `_generate_mesh`, `_run_solver`, `_process_results` | Adapter connected; unavailable locally | Gmsh meshing, VTK conversion, quality analysis, and preview remain operational. OpenFOAM conversion/checkMesh is deferred and the solver/results stages remain blocked until it is installed. |
| OpenMDAO | `_run_openmdao_nevergrad` | Connected and ready | Used by Expert Optimize with a project-owned `evaluate(design)` module. |
| Nevergrad | `_run_openmdao_nevergrad` | Connected and ready | Produces candidates and recorded optimization history. |
| PhysicsNeMo | `_train_surrogate` | Connected and ready in its isolated repository runtime | Runs the project-owned trainer with the checked-out PhysicsNeMo source, without contaminating the general CFD runtime. |
| PhysicsNeMo-CFD | `_train_surrogate` | Connected and ready in the same isolated repository runtime | Is exposed as `physicsnemo.cfd` through the checked-out CFD extension source path. |
| VTK | `_mesh_diagnostics`, `_result_summary` | Connected and ready | Validates mesh/result data and contributes metadata. |
| PyVista | `_mesh_diagnostics`, `_result_summary` | Connected and ready | Computes mesh quality and creates a result preview from the real dataset. |
| ParaView | `_paraview_preview` | Adapter connected; unavailable locally | Runs as an optional batch renderer only when `pvpython` is present. |
| three.js | `frontend/src/components/viewport/Viewport3D.tsx` | Bundled and connected | Presents the actual PyVista-generated preview in the desktop viewport. |
| react-three-fiber | `Viewport3D.tsx` | Bundled and connected | Owns the React composition of the result artifact viewport. |
| drei | `Viewport3D.tsx` | Bundled and connected | Provides fitting and orbit controls for the result artifact viewport. |

## Failure semantics

`workflow_service.py` creates a durable job before adapter dispatch. Missing engines, missing source files, non-zero subprocess exits, invalid geometry, failed `checkMesh`, and missing VTK output transition that job to `FAILED` with its error persisted in the project SQLite ledger. Successful runs publish project-owned `refs/<stage>/latest.json` evidence; snapshots return those references so a preview survives route changes and desktop restarts. Reconfiguring a stage clears its own and downstream latest pointers while preserving the historical run directories. No static turbine, streamline, residual, monitor, or report values are used as substitutes for backend output.

## Validation evidence

The integration was compiled with:

```text
frontend: npm run build
backend: python -m compileall -q src/cfd_backend
desktop bridge: cargo fmt --check && cargo check -q
```

The managed project runtime found Gmsh, meshio, OpenMDAO, Nevergrad, VTK, PyVista, PhysicsNeMo, and PhysicsNeMo-CFD ready; three.js, react-three-fiber, and drei bundled. FreeCAD, OpenFOAM, and ParaView have local source checkouts but no verified executable build, so their adapters remain accurately unavailable. The local FastAPI service responded successfully from its private loopback health endpoint. A real Gmsh-generated BREP box was prepared through the durable workflow with FreeCAD unavailable: the job reached `SUCCEEDED`, published `prepared.brep`, reported one solid with a volume of `120.0`, and recorded `Gmsh OpenCASCADE healShapes`. A subsequent real meshing run generated a 3D `mesh.msh`, a clean VTK derivative, PyVista quality data, and a preview image with OpenFOAM accurately reported as deferred. STL remains rejected by this solid-CAD preparation route rather than being misrepresented as a watertight solid.
