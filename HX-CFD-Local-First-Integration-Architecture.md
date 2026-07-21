# HX CFD — Local-First Integration Architecture

## Status

This is the Phase 11 implementation contract for the fourteen engineering repositories. It is subordinate only to explicit product requirements and must be read with:

- HX_CFD_Master_Engineering_Prompt.md
- HX_CFD_Dependency_Role_Map.md
- HX-CFD-Master-Prompt-v2.md

HX CFD is the product. The repositories below are implementation engines. No screen, workflow label, project file, or normal error message should require an engineer to understand which repository executed a task.

---

## 1. Non-negotiable platform contract

HX CFD is a local-first Windows desktop application. The engineer starts HX CFD.exe; Tauri starts and supervises everything required for that session. A browser, terminal, Python interpreter, localhost URL, cloud account, or separately launched engineering tool is never part of the user workflow.

| Concern | Locked decision |
|---|---|
| Desktop host | Tauri/Rust owns the window, menus, file dialogs, notifications, process tree, shutdown, and recovery. |
| UI | React + TypeScript runs only inside the Tauri webview. three.js, react-three-fiber, and drei are presentation dependencies, not a second application. |
| Application service | FastAPI runs inside the managed local Python sidecar. It supplies typed service contracts and development/test adapters; it is never a user-facing server. |
| Transport | UI uses typed Tauri commands/events. Rust communicates with the Python sidecar over a per-session authenticated named pipe or private loopback socket. If FastAPI uses HTTP internally, it binds only to loopback on an ephemeral port and its address/token never reaches the UI or user. |
| Tool execution | Rust launches native tools from validated LaunchSpecs. Each engineering job is isolated in a worker process or native process tree. Never construct a shell command string. |
| Project data | Projects and artifacts remain local by default under the user's selected project root. Program Files contains immutable app/tool binaries only. |
| Cloud | Optional export, update, telemetry, and remote AI providers may be added through explicit adapters. Core geometry, meshing, solving, post-processing, and project access work without internet. |
| AI | An advisory capability with local and remote provider adapters. No AI provider is required to execute a CFD workflow. |

The normal runtime is:

    React/TypeScript UI
              |
       typed Tauri commands/events
              |
       Rust session supervisor
          |              |
     project store   private IPC
                         |
                  FastAPI Python sidecar
                         |
                  durable job coordinator
          _________/____|_____________
         /           |       |         \
    FreeCADCmd   mesh worker OpenFOAM  post/ML workers

Rust retains every child handle and assigns native children to a Windows Job Object. Closing the app, cancelling a job, or recovering after a crash must terminate the complete descendant tree without touching unrelated processes.

---

## 2. Persistent data, memory, and job model

### 2.1 Local storage

Use separate locations for immutable software, mutable application state, and project evidence:

| Location | Contents | Ownership |
|---|---|---|
| Program Files\HX CFD | signed HX CFD binaries, pinned native-tool distributions, read-only defaults | installer/update service |
| LocalAppData\HX CFD | session state, state.sqlite, cache index, crash reports, application logs | desktop runtime |
| Documents\HX CFD Projects\<project> or an engineer-selected local/network folder | project manifest, project.sqlite, immutable artifacts, job logs, run references | the project and its owner |

Every project has:

    project.sqlite                 durable entities, job state, artifact references
    manifest.json                  schema/version/tool bill of materials
    objects\sha256\<digest>        immutable content-addressed artifacts
    runs\<run-id>                  human-navigable links, reports, exported evidence
    refs                           current geometry/mesh/case/result revision pointers

Never write a project, mesh, solver case, user log, or cache into Program Files. Project artifacts are immutable after publication; a changed geometry, mesh recipe, or solver setup creates a new revision.

### 2.2 Artifact formats and ownership

| Artifact family | Canonical form | Owner |
|---|---|---|
| Source geometry | original STEP, IGES, or native source plus import metadata | geometry service |
| Editable CAD | FCStd where needed; repaired canonical BREP/STEP for downstream tasks | geometry service |
| Mesh route A | Gmsh MSH 4.1 plus physical-group metadata, then OpenFOAM constant/polyMesh | mesh service |
| Mesh route B | triangulated surface, OpenFOAM dictionaries, then constant/polyMesh | mesh service |
| Simulation | OpenFOAM case tree and immutable dictionaries | solver service |
| Results | OpenFOAM native fields plus normalized VTU/VTM/PVD, CSV/JSON metrics | results service |
| Viewport payload | decimated GLB/Draco geometry, field chunks, legend/selection metadata | visualization service |

Workers own memory only while they run: FreeCAD owns an open document, Gmsh a model, VTK/PyVista a data set, and PhysicsNeMo a CUDA context/tensors. The UI owns WebGL resources. Cross-process communication is by artifact reference and metadata, never shared mutable in-memory models.

### 2.3 Jobs, caches, and error contract

Persist each transition before emitting it:

    QUEUED -> STAGING -> RUNNING -> VALIDATING -> PUBLISHING -> SUCCEEDED
                 |            |             |
              CANCELED     FAILED        ORPHANED

The cache key includes input artifact hashes, canonical recipe, adapter version, executable/package checksum, fixed random seed, and resource profile. Cache entries may be reused only if every key component matches.

Every failure sent to the desktop has this shape:

    code, category, component, stage, retryable, action, job_id, log_artifact_id

Store structured JSONL events and raw stdout/stderr as project artifacts. Validation, CAD topology, patch-mapping, and mesh-quality failures are engineering failures and are never blindly retried. Worker-start, temporary file-lock, or transient disk failures may retry a bounded number of times in a fresh staging directory. Solver divergence and cancelled jobs preserve evidence and require an explicit engineer decision.

---

## 3. Repository integration contracts

### 3.1 FreeCAD

**Purpose.** FreeCAD provides parametric CAD import, editable geometry, OpenCASCADE-backed BREP operations, and a headless validation/repair boundary. It exists so HX CFD does not recreate a CAD kernel or STEP/IGES translator.

**Placement and integration.** Mandatory when the source is CAD. It executes after project import and before geometry validation, defeaturing, and both mesh routes. The Rust supervisor starts FreeCADCmd or an equivalent headless FreeCAD adapter per geometry job; it is not embedded in the long-lived Python process. Inputs are original CAD artifacts, unit settings, and an immutable repair recipe. Outputs are a geometry report and canonical BREP/STEP artifact. The worker exits after publication.

**Boundaries.** FreeCAD should import, inspect, parameterize, heal where the recipe allows, and export. It should not decide CFD regions, boundary names, mesh sizes, wall treatment, or solver settings. Its CPU and memory use can spike on large assemblies; stage in a short-path local directory and cap concurrent imports.

**Failure handling.** Invalid topology, import-unit ambiguity, unsupported CAD entities, and repair failure are non-retryable validation results. Capture the original file, adapter logs, and a geometry diagnostic artifact. A worker crash is retryable once in a fresh process.

**HX CFD abstraction.** Present Import Geometry, Geometry Health, Repair Suggestions, and revision-aware parameters—not FreeCAD workbenches or macros. Advanced users may inspect source/repair provenance, never need to launch FreeCAD.

### 3.2 Gmsh

**Purpose.** Gmsh creates deterministic surface and unstructured volume meshes with size fields and physical groups. It exists to supply a mature, scriptable CAD-conformal meshing route.

**Placement and integration.** It is mandatory for mesh route A and optional for route B surface preparation. It follows accepted geometry/semantic boundaries and precedes OpenFOAM normalization and quality validation. Invoke the Gmsh Python API in a dedicated mesh worker; use direct Gmsh CLI only when a pinned adapter cannot express the operation. Inputs are canonical geometry, a compiled MeshRecipe, and semantic boundary registry. Outputs are MSH 4.1, mesh statistics, physical-group mapping, and logs. Each job creates/disposes its own Gmsh model.

**Boundaries.** Gmsh should tessellate, classify entities, create fields, and generate route-A mesh. It should not own project persistence, convert MSH into OpenFOAM polyMesh through meshio, decide whether a feature is physically important, or run the CFD solver. It is CPU/memory intensive; use size bounds, deterministic seeds, and job-level RAM/resource limits.

**Failure handling.** Geometry/field incompatibility, invalid physical groups, and quality-rule breach become actionable mesh diagnostics with no blind retry. A temporary worker failure can retry once. Preserve the .geo-equivalent compiled recipe, MSH, logs, and statistics.

**HX CFD abstraction.** Expose Mesh Recipe, Surface Sizing, Volume Sizing, Refinement Regions, and Boundary Names. Gmsh fields and entity IDs appear only in an Advanced Diagnostics drawer.

### 3.3 meshio

**Purpose.** meshio is an interchange reader/writer and lightweight mesh inspection utility. It exists to normalize non-canonical import/export formats without adding a separate viewer or format-specific code path for each exporter.

**Placement and integration.** Optional, on demand, at import/export or result normalization. It can follow Gmsh or OpenFOAM outputs and precede VTK/PyVista conversion. It must not be the canonical Gmsh-to-OpenFOAM conversion path; route-A conversion uses OpenFOAM gmshToFoam to preserve solver-native semantics. meshio runs in the short-lived mesh or post worker. Inputs/outputs are artifact files such as MSH, VTU, VTK, XDMF, and MED; no project object is held in memory after the worker exits.

**Boundaries.** meshio should translate supported interchange files and report cell/field structure. It should not repair topology, create boundary layers, infer patches, or rewrite an OpenFOAM case. It is usually I/O and memory bound on large meshes; stream/chunk where the chosen format permits and avoid unnecessary materialization.

**Failure handling.** Unsupported dialect, mixed cell types, lost field data, or malformed file reports a conversion diagnostic and retains the source artifact. Do not silently drop data. Retry only read/write locking failures.

**HX CFD abstraction.** Offer Import Mesh and Export Results with a compatibility report. The engineer chooses an interchange goal, not a meshio command.

### 3.4 OpenFOAM

**Purpose.** OpenFOAM is the solver-native mesh utility suite and CFD execution engine. It owns OpenFOAM case construction, native conversion, meshing utilities such as blockMesh/snappyHexMesh, checkMesh, decomposition, and solver execution.

**Placement and integration.** Mandatory for every OpenFOAM solve. It follows either route-A MSH output through gmshToFoam or route-B surface preparation. It executes checkMesh before a case can be solved and follows physics/case compilation. Run it as a supervised native process tree, including MPI children, with an isolated run directory. Inputs are immutable mesh/case artifacts and a resource profile; outputs include polyMesh, fields, residual logs, and normalized run metrics.

**Boundaries.** OpenFOAM should own solver-native conversion, hex-dominant route-B meshing, boundary-layer extrusion in snappyHexMesh, quality checks, and solving. It should not import CAD, be a UI process, decide physical setup, write UI layout state, or hide dictionary changes from provenance.

**Performance and failure.** It is CPU, RAM, disk, and sometimes network-I/O intensive. Use local fast scratch, explicit MPI/process limits, decomposed-case cleanup policies, and parse stdout incrementally. Syntax/topology/quality failures are non-retryable; transient launch failures can restart in a fresh run. Divergence is reported with convergence evidence and is never silently restarted.

**HX CFD abstraction.** Present Solver Setup, Mesh Quality, Run Controls, Residuals, and Results. Preserve raw dictionaries and logs behind Advanced/Export, while ordinary workflows operate through validated semantic forms.

### 3.5 OpenMDAO

**Purpose.** OpenMDAO defines a reproducible multidisciplinary optimization graph: design variables, analyses, objectives, constraints, and recorded studies. It exists to make multi-run engineering studies traceable rather than an ad-hoc loop.

**Placement and integration.** Optional and used only in an Optimization Study after a valid baseline workflow exists. It follows geometry/physics/solver/result contracts and orchestrates trial jobs; Nevergrad or another compatible driver may execute within the study. Use a dedicated optimization worker with serialized study state and child analysis jobs. Inputs are a StudyRecipe and artifact references; outputs are trial records, objective/constraint tables, and a selected candidate revision.

**Boundaries.** OpenMDAO should represent the study graph and derivative/recording semantics. It should not execute CAD/Gmsh/OpenFOAM in-process, own the desktop queue, or claim a surrogate is physically validated. It is orchestration and memory intensive for large recordings; store artifacts by reference, checkpoint between trials, and cap parallel trial count.

**Failure handling.** Invalid design domains and failed analysis trials become explicit failed evaluations. Retry only infrastructure failures. Resume from the last durable checkpoint; never fabricate a missing objective.

**HX CFD abstraction.** Show Design Variables, Objectives, Constraints, Study Progress, and Candidate Comparison. The component graph is exportable/advanced-only.

### 3.6 Nevergrad

**Purpose.** Nevergrad supplies gradient-free optimization strategies for noisy, non-differentiable, and expensive CFD objectives. It exists because ordinary full CFD runs generally do not provide usable derivatives.

**Placement and integration.** Optional inside an OpenMDAO-backed or HX-managed optimization study. It runs after valid variable/objective definitions and before each trial analysis. Integrate as a Python adapter in the optimization worker, seeded and version-pinned. Inputs are normalized variable domains and evaluation results; outputs are candidate vectors, recommendation state, and optimizer checkpoint data.

**Boundaries.** Nevergrad should propose candidates and receive scalar/vector evaluations. It should not know FreeCAD, OpenFOAM, mesh files, or UI interaction; the study adapter owns those mappings. It is normally CPU-light relative to CFD, but can consume memory for large populations. Bound population and retained history.

**Failure handling.** Reject invalid domains before the optimizer starts. Failed CFD trials are reported to the study policy rather than re-run automatically. Save checkpoints after every accepted evaluation.

**HX CFD abstraction.** Offer Strategy, Budget, Parallelism, Seed, and Stop Conditions. Show engineering trade-offs rather than algorithm class names by default.

### 3.7 PhysicsNeMo

**Purpose.** PhysicsNeMo supplies GPU-accelerated physics-ML infrastructure for local surrogate training/inference. It exists to reduce the number of expensive full simulations in exploratory studies, never to replace validation.

**Placement and integration.** Optional after a curated dataset of comparable validated simulations exists. It follows result normalization and may provide estimates to optimization studies. Start a dedicated GPU worker per study or inference session, ideally in a separately pinned Python/CUDA environment compatible with the selected version. Inputs are versioned training datasets and model recipes; outputs are model artifacts, evaluation metrics, uncertainty data, and field predictions.

**Boundaries.** PhysicsNeMo should train/infer models and measure model quality. It should not generate authoritative solver results, mutate project geometry, own GPU scheduling across the app, or bypass acceptance gates. It is GPU/VRAM/RAM intensive; preflight CUDA/driver/VRAM, isolate the worker, use mixed precision only after validation, and keep model data local.

**Failure handling.** Missing compatible GPU, CUDA mismatch, out-of-memory, poor validation score, and dataset incompatibility are explicit states. Retry only worker start or transient resource allocation. Do not substitute a CPU or remote provider silently.

**HX CFD abstraction.** Show Surrogate Assist as optional, with data coverage, accuracy, uncertainty, hardware status, and mandatory validation plan. It must be visibly distinct from a solved result.

### 3.8 PhysicsNeMo-CFD

**Purpose.** PhysicsNeMo-CFD contributes CFD-oriented data pipelines and model patterns on top of PhysicsNeMo. It exists to avoid treating CFD fields as generic tensors.

**Placement and integration.** Optional and dependent on PhysicsNeMo. It follows normalized mesh/result datasets and precedes surrogate evaluation. It shares the isolated GPU worker, but its adapter is separately version-pinned because its Python and CUDA compatibility can differ. Inputs are CFD field datasets, mesh/domain metadata, and model recipes; outputs are CFD-oriented model checkpoints and validation reports.

**Boundaries.** It should supply CFD surrogate capabilities only. It should not write OpenFOAM fields as if they were solved, change a mesh recipe, or decide whether a surrogate is accepted for engineering use. GPU/VRAM profile and failure treatment are the same as PhysicsNeMo.

**HX CFD abstraction.** Surface it under the same Surrogate Assist screen; advanced users select a model family only after seeing compatibility and validation requirements.

### 3.9 VTK

**Purpose.** VTK provides the fundamental in-memory scientific-data model and filters for field conversion, cutting, probing, streamlines, and derived data.

**Placement and integration.** Mandatory for backend visualization and data transformation after a mesh/result artifact exists. It follows OpenFOAM/meshio normalization and precedes PyVista convenience calls or viewport packaging. It runs in a post-processing worker per heavy job. Inputs are results/mesh artifacts; outputs are derived datasets and intermediate visualization products.

**Boundaries.** VTK should perform scientific-data transformation, not own UI rendering, project state, or user-facing orchestration. It is memory intensive; use LOD, time-step selection, data-array pruning, and out-of-core/partitioned approaches when available.

**Failure handling.** Missing fields, incompatible arrays, corrupt result files, and memory exhaustion create diagnostic reports. Retry only temporary access failures; avoid re-reading a full time series if an artifact cache is valid.

**HX CFD abstraction.** Present Slice, Contour, Streamlines, Probe, Compare, and Export. VTK pipelines are persisted as semantic visualization recipes.

### 3.10 PyVista

**Purpose.** PyVista is the application-level Python interface over VTK for routine mesh/result loading and post-processing.

**Placement and integration.** Mandatory for normal interactive post-processing, following result normalization. It runs lazily in a disposable post worker and produces derived VTK datasets or viewport-friendly artifacts. Inputs are result artifact IDs and VisualizationRecipes; outputs are derived fields, sampled data, surface geometry, and visual package metadata.

**Boundaries.** PyVista should express common visualization workflows, while VTK remains the low-level implementation. It should not become a persistent GUI, solve equations, own project storage, or transfer huge raw arrays directly to the webview.

**Performance and failure.** CPU/RAM intensive on large transient data. Cache derived results by recipe/hash, reduce before crossing the UI boundary, and cancel promptly. Field absence and invalid filters become actionable local diagnostics.

**HX CFD abstraction.** The UI exposes result operations and exact units; PyVista is invisible except in Advanced Provenance.

### 3.11 ParaView

**Purpose.** ParaView contributes a batch/parallel post-processing engine for filters, rendering, and time series beyond the routine PyVista path.

**Placement and integration.** Optional, used on demand for large/advanced analysis or report/video generation after results exist. Launch pvpython or pvbatch as a supervised isolated worker. Inputs are artifact paths and a generated PVSM/Python recipe; outputs are images, movies, data extracts, and provenance. It never launches a visible ParaView application window.

**Boundaries.** ParaView should handle advanced or scalable post-processing only. It should not be the default viewport, project database, mesher, or solver. It can be CPU/GPU/RAM/IO intensive; use low-resolution previews, fixed time ranges, resource profiles, and job cancellation.

**Failure handling.** Missing plugins, incompatible reader/filter, GPU rendering failure, and worker crash produce a report with the retained recipe. Retry fresh process startup only. A PyVista-compatible fallback may be offered when it preserves the requested operation.

**HX CFD abstraction.** Offer Advanced Analysis and Render Report actions; users choose an outcome, not pvbatch.

### 3.12 three.js

**Purpose.** three.js renders responsive GPU-accelerated scene geometry inside the desktop webview. It exists for direct manipulation of compact geometry, mesh, and result representations.

**Placement and integration.** Mandatory in the UI after backend visualization packaging. It receives only decimated geometry/field chunks and selection metadata, never a native solver case or giant unbounded data array. It remains loaded for the desktop session and owns WebGL resource disposal when a view closes.

**Boundaries.** It should render and interact; it should not calculate CFD results, parse OpenFOAM cases, launch jobs, or persist engineering data. GPU memory is the key constraint: budget textures/buffers, support LOD and field paging, and dispose deterministically.

**Failure handling.** WebGL context loss, unsupported GPU limits, or payload decode failure shows a recoverable viewport diagnostic and offers lower LOD/CPU-safe view. The underlying result artifact remains valid.

**HX CFD abstraction.** It is simply the Geometry/Mesh/Results viewport. Engineers interact with orbit, selection, clipping, legends, and probes—not renderer APIs.

### 3.13 react-three-fiber

**Purpose.** react-three-fiber maps React state and component lifecycle to the three.js scene. It exists to keep the viewport coordinated with desktop UI state.

**Placement and integration.** Mandatory alongside three.js in the webview. It receives typed viewport state from the React store and releases scene resources as components unmount. It does not communicate with the backend directly; the application command layer does.

**Boundaries.** It should compose scene state and interactions. It should not host engineering business rules, API calls, global job state, or file access. Keep React renders bounded; memoize immutable geometry and isolate high-frequency view changes from application state.

**Failure handling.** Component/render exceptions are caught by a viewport error boundary, logged locally, and recover to a safe scene without killing the sidecar.

**HX CFD abstraction.** No separate concept is exposed. The viewport behaves as one native HX surface.

### 3.14 drei

**Purpose.** drei supplies well-tested react-three-fiber interaction helpers such as controls, gizmos, loaders, and performance aids.

**Placement and integration.** Mandatory only where a selected helper is used in the viewport. It executes in the webview after three.js/r3f; it owns no project artifacts or service lifecycle.

**Boundaries.** drei should provide presentation utilities only. It should not dictate CAD navigation semantics, perform file system access, or receive raw engineering data. Audit helpers for render/performance cost and load only the required components.

**Failure handling.** A failed helper or asset decoder is contained by the same viewport error boundary. Replace a failing convenience feature with a native/simple equivalent rather than breaking result access.

**HX CFD abstraction.** Engineers see a precise view cube, navigation controls, and measurement aids consistent with the HX design system—not a helper library.

---

## 4. Meshing is the flagship subsystem

### 4.1 Strategic decision

Yes: HX CFD should be known for the industry's most trustworthy solver-aware CFD meshing workflow, particularly for OpenFOAM-class simulation. The defensible product is not a generic claim to be the world's raw fastest mesher. It is a system that turns imperfect engineering geometry into a reproducible, inspectable, solver-ready mesh with correct physical patches, boundary layers, quality evidence, and an understandable recovery path.

Meshing is technically strategic because every solver, optimization study, surrogate dataset, and results interpretation depends on it. It is commercially strategic because engineers spend substantial time repairing geometry, recreating boundary intent, diagnosing quality failures, and wondering whether a mesh is actually safe to solve.

### 4.2 Mesh routes and exact order

HX CFD compiles an immutable MeshRecipe and selects one route before execution. Never blend routes halfway through a job.

**Route A — CAD-conformal unstructured**

    0. Snapshot source geometry, units, transforms, and semantic labels.
    1. FreeCAD import and canonical BREP/STEP creation.
    2. FreeCAD/OpenCASCADE geometry validation and permitted repair.
    3. Engineer confirms CFD domain and semantic boundary registry.
    4. HX applies approved defeaturing as a new geometry revision.
    5. Gmsh feature/surface preparation and physical-group validation.
    6. Gmsh surface mesh, volume mesh, and field/refinement generation.
    7. OpenFOAM gmshToFoam converts MSH into constant/polyMesh.
    8. HX verifies every expected physical group maps to an expected patch.
    9. OpenFOAM checkMesh plus HX quality-policy evaluation.
   10. VTK/PyVista creates diagnostic visualization artifacts.
   11. Engineer accepts the mesh revision.
   12. Solver case can execute.

**Route B — hex-dominant / snappyHexMesh**

    0-4. Same geometry, validation, semantic-boundary, and defeaturing steps.
    5. Gmsh or controlled FreeCAD tessellation creates input surfaces where required.
    6. OpenFOAM surfaceCheck and surfaceFeatureExtract inspect/prepare surfaces.
    7. OpenFOAM blockMesh creates background mesh.
    8. OpenFOAM snappyHexMesh executes castellate, snap, and addLayers.
    9. OpenFOAM checkMesh plus HX quality-policy evaluation.
   10-12. Same diagnostics, acceptance, and solver gate.

Gmsh BoundaryLayer fields are not a general 3D boundary-layer solution. Use them only where the selected Gmsh route supports the geometry and layer behavior. For robust 3D near-wall layers, Route B with snappyHexMesh addLayers is the default. Surface coverage and achieved thickness are measured results, not assumed intent.

### 4.3 Meshing responsibilities

| Capability | Primary owner | HX CFD value |
|---|---|---|
| Geometry import/repair | FreeCAD headless adapter | non-destructive repair recipe, revision comparison |
| Geometry validation | FreeCAD/OCC + HX policy | actionable health scores tied to meshing impact |
| Surface cleanup | FreeCAD/Gmsh/OpenFOAM depending route | retain semantic labels and report every change |
| Defeaturing | engineer-approved HX recipe executed by FreeCAD/Gmsh | protected-feature policy and full provenance |
| Feature detection | Gmsh/OpenFOAM | translate feature findings into mesh intent |
| Surface mesh | Gmsh or snappy input surface flow | semantic sizing controls |
| Volume mesh | Gmsh Route A or OpenFOAM Route B | explicit route selection and deterministic setup |
| Boundary layer generation | snappyHexMesh by default for robust 3D; Gmsh when justified | y-plus aware recipe and achieved-coverage report |
| Mesh quality/repair | OpenFOAM checkMesh plus HX policy | solver-aware thresholds, no hidden waivers |
| Adaptive refinement | OpenFOAM or a child mesh recipe | parent/child evidence and field-informed recommendations |
| Mesh visualization | VTK/PyVista -> three.js viewport | diagnostic views at appropriate LOD |
| AI generation/diagnostics | HX AI adapter | recommendation/ranking only, with evidence and no autonomous acceptance |

### 4.4 Automation boundaries

Fully automate safe, reversible, or evidentiary work: unit/transform detection with confirmation on ambiguity; non-destructive geometry checks; safe cleanup that preserves labels; cache lookup; patch-mapping verification; raw-log capture; quality reports; LOD creation; and bounded infrastructure retries.

Keep engineer-configurable: mesh route; sizing budget; local refinements; protected and removable features; y-plus target; first-layer height; layer count/growth; quality thresholds; solver resource profile; and final mesh acceptance.

AI must never decide to remove a feature, change a physical boundary mapping, choose turbulence/wall treatment or y-plus without review, waive a quality failure, approve a final mesh, or represent a surrogate as a validated CFD solution.

### 4.5 Meshing user experience

The Meshing module is a usable configuration workflow, not a placeholder:

1. **Geometry Health** — import status, units, open/invalid faces, repair proposal, revision history.
2. **Flow Domain & Patches** — named inlet/outlet/wall/symmetry regions, visual selection, unresolved mapping warnings.
3. **Mesh Strategy** — route selector with why/recommendation, editable target cell budget and cost estimate.
4. **Sizing & Features** — global/local size, curvature/proximity, protected features, refinement regions.
5. **Boundary Layers** — y-plus basis, first height, layers, growth, achieved-coverage results.
6. **Quality & Diagnostics** — checkMesh facts, policy verdict, worst cells/regions, clear recovery actions.
7. **Acceptance** — immutable mesh revision, recipe/tool versions, comparison to parent, explicit engineer approval.

Measure the flagship against solver-ready first-pass rate, CAD-to-accepted-mesh time, physical-patch preservation rate, achieved layer coverage, reproducibility, manual intervention rate, and downstream convergence outcomes.

---

## 5. Local AI architecture

AI is an adapter behind the same local service boundary:

    HX AI request
        -> local policy/redaction layer
        -> selected adapter: local model | remote provider | unavailable
        -> cited recommendation + confidence + source artifacts

No task is blocked when AI is unavailable. API keys belong in OS-backed secure storage; they never appear in project artifacts, logs, or the frontend bundle. Remote use requires an explicit per-provider consent setting that identifies what data leaves the machine. Local models run only when installed/configured and are resource-budgeted like any other GPU worker.

---

## 6. Delivery sequence and acceptance gates

Implement in this order:

1. **Desktop foundation:** replace fixed localhost coupling with Rust-supervised private IPC; retain FastAPI as managed sidecar service; retain child handles and add Job Object containment.
2. **Local durability:** add project.sqlite, artifact store, artifact hashing, durable jobs, logs, and crash reconciliation.
3. **Geometry and mesh path:** FreeCADCmd adapter, semantic boundary registry, Route A, OpenFOAM gmshToFoam/checkMesh gate, diagnostics.
4. **Route B and mesh acceptance:** snappyHexMesh pipeline, layer evidence, repair recommendations, comparison/acceptance UI.
5. **Solve and results:** case compiler, supervised OpenFOAM/MPI, VTK/PyVista visualization artifacts, typed progress/error events.
6. **Advanced workloads:** ParaView batch adapter, OpenMDAO/Nevergrad studies, then separately pinned PhysicsNeMo workers.
7. **Optional AI:** local/remote adapters, explicit consent, advisory-only policy, offline tests.

A release cannot claim a workflow stage is complete until it can start from HX CFD.exe, run offline with bundled tools, survive cancellation/restart, produce provenance-complete local artifacts, and show an actionable failure state without exposing tool-specific operational steps to the engineer.

---

## 7. Standing rules

- Do not expose repository names as ordinary navigation or workflow stages.
- Do not use a user-visible web server, browser URL, cloud service, or terminal command as an execution requirement.
- Do not pass mutable project state between processes; pass artifact references and validated recipes.
- Do not trust process exit alone as job success; validate outputs and publish atomically.
- Do not silently fall back from a requested native/GPU/AI capability to a different execution model.
- Do not hide solver, mesh, model, or data version provenance.
- Do not label an incomplete adapter, mock, or placeholder screen as a completed engineering capability.

