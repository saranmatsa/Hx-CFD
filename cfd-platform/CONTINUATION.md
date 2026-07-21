# HX CFD — Continuation Status

Last updated: 2026-07-19

## Current result

The HX CFD desktop backend is now a real, local managed service. The intended execution path is in place:

```text
React frontend → Tauri command → private local FastAPI API → workflow service → repository adapter → engineering engine
```

The browser preview at `http://127.0.0.1:5173` is only a frontend preview. Real engineering actions require the HX CFD desktop shell because Tauri owns the backend endpoint and its per-launch authentication token.

## Completed work

### Desktop backend lifecycle

- Tauri starts and manages one long-lived FastAPI backend process.
- The backend binds to an ephemeral loopback port only.
- The backend API uses a per-launch bearer token kept inside Tauri; it is not exposed to the webview.
- The desktop workflow router returns `401` for unauthenticated workflow access.
- Startup is serialized so multiple frontend surfaces do not start duplicate backend processes.
- Tauri stops the complete backend process tree on shutdown on Windows.
- Legacy public API routes are not mounted for the managed desktop path.

Key files:

- `src/backend.rs`
- `src/commands.rs`
- `backend/src/cfd_backend/main.py`
- `backend/src/cfd_backend/api/v1/workflow.py`

### Workflow and project storage

- Local project create, open, rename, archive, delete, snapshots, stage configuration, execution, artifacts, and export are routed through Tauri to FastAPI.
- Project artifacts are exposed through opaque IDs rather than raw local paths.
- Preview artifacts can be returned to the UI as bounded data content.
- Workflow stages fail truthfully when required engines or upstream evidence are unavailable; they do not fabricate solver or result output.

Key files:

- `backend/src/cfd_backend/services/workflow_service.py`
- `backend/src/cfd_backend/api/v1/workflow.py`
- `frontend/src/services/desktopWorkflow.ts`

### Geometry and meshing

- Geometry preparation uses FreeCAD when it is installed and runnable.
- Gmsh provides a real solid-geometry fallback for STEP/STP, IGES/IGS, and BREP.
- STL and OBJ explicitly require FreeCAD; they are not silently sent through an invalid Gmsh fallback.
- Meshing performs real Gmsh volume meshing, meshio conversion, VTK/PyVista analysis, preview generation, and quality reporting.
- Boundary groups are explicit: selected inlet/outlet/wall/symmetry surfaces become physical groups. Remaining faces stay `unassigned` unless the user explicitly groups them as walls.
- The OpenFOAM case adapter validates patch mapping before solver execution.

Key files:

- `backend/src/cfd_backend/services/engineering_orchestrator.py`
- `backend/src/cfd_backend/services/workflow_service.py`
- `backend/tests/test_gmsh_geometry_fallback.py`
- `backend/tests/test_gmsh_boundary_groups.py`

### Reports, optimization, and surrogate stages

- Reports require verified project-owned VTK and preview evidence, then generate a real local PDF and HTML companion report.
- Optimization rejects non-finite evaluator objectives.
- Surrogate training requires actual model output, writes a model manifest, and publishes model files as exportable artifacts.
- PhysicsNeMo was manually exercised and produced real surrogate/checkpoint output.

Key files:

- `backend/src/cfd_backend/services/workflow_service.py`
- `backend/tests/test_pdf_report.py`
- `backend/tests/test_optimization_adapter.py`
- `backend/tests/test_surrogate_artifacts.py`

### Release/runtime packaging

- Release builds stage backend source, the managed Python environment, and base CPython into `bin/backend-runtime`.
- Release discovery prefers the staged managed runtime before any old frozen sidecar.
- The embedded runtime launches with the correct `PYTHONHOME`, managed site packages, and bootstrap script.
- PyInstaller is now optional: set `HX_CFD_BUILD_FROZEN_SIDECAR=1` only when intentionally producing a frozen sidecar.
- Tauri bundles `bin/backend-runtime/**/*`.
- The Inno installer copies the managed runtime instead of relying on the stale `cfd-backend.exe`.

Key files:

- `build.rs`
- `src/backend.rs`
- `tauri.conf.json`
- `installer/src/HXCFD.iss`

## Verification completed

- Managed FastAPI smoke test passed:
  - `GET /health` returned `200` and `healthy`.
  - Unauthenticated workflow engine inventory returned `401`.
  - Authenticated inventory returned all 14 canonical engine records.
  - Authenticated project creation and opening persisted locally.
- Direct staged-runtime test passed using the packaged Python runtime:
  - health endpoint `200`;
  - unauthenticated engine request `401`;
  - authenticated inventory `200` with Gmsh `4.15.2` ready;
  - local project create/open succeeded.
- Full Python test suite passed: **22 tests**.
- `cargo fmt --check` passed.
- `git diff --check` passed (only pre-existing line-ending warnings in frontend files).

## Current local engine reality

### Available and exercised

- Gmsh
- meshio
- VTK / PyVista
- OpenMDAO
- Nevergrad
- PhysicsNeMo / PhysicsNeMo-CFD
- Three.js / React Three Fiber / drei (frontend rendering stack)

### Not currently runnable on this machine

- FreeCAD
- OpenFOAM
- ParaView

Their source checkouts may exist, but no runnable executables were found. HX CFD reports them as unavailable and blocks dependent stages instead of simulating them.

## Remaining work

### Required before claiming all 14 engines are operational

1. Install or configure runnable local executables for FreeCAD, OpenFOAM, and ParaView.
2. Refresh engine inventory from HX CFD after installation and verify each reports `ready`.
3. Run an end-to-end OpenFOAM case:
   - import geometry;
   - prepare geometry;
   - create mesh with explicit boundary groups;
   - generate OpenFOAM case;
   - run `gmshToFoam`, `checkMesh`, and the selected solver;
   - run `foamToVTK` and results visualization.
4. Run a FreeCAD STL/OBJ import and closed-solid validation flow.
5. Run ParaView-backed advanced visualization if ParaView integration is required beyond the existing VTK/PyVista path.

### Packaging follow-up

1. Run a full production `tauri build` when time permits. It stages a roughly 1 GB local Python runtime, so it can take longer than a normal frontend build.
2. Test the produced installer on a clean Windows user profile or VM with no system Python installation.
3. Confirm the installer starts HX CFD, the backend reaches healthy state automatically, and projects are stored under the application data directory.
4. Consider code-signing the release executable and installer before distribution.

### Cleanup / product follow-up

- The inactive legacy non-desktop API contains old mock-oriented code such as `optimization_service.py`. It is not mounted in the Tauri-managed desktop path, but it should be removed or clearly isolated in a future cleanup.
- The active Improve screen currently routes its main action through the report stage. If the product needs the visible advanced evaluator/training controls to execute optimization or surrogate stages directly, wire those controls to the existing real `optimization` and `surrogate` workflow stages. This is a frontend reachability task, not a backend-engine implementation gap.
- Keep the browser preview non-authoritative: it should not be changed to call the private FastAPI endpoint directly.

## Safe next commands

From `C:\CFD\cfd-platform`:

```powershell
# Backend regression suite
backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -p 'test_*.py' -q

# Rust formatting check
cargo fmt --check

# Production bundle (managed runtime is staged automatically)
cargo tauri build
```

Do not set `HX_CFD_BUILD_FROZEN_SIDECAR` unless deliberately testing the optional PyInstaller path.


# Build, Packaging, and Environment Handover

This section is the practical checklist for resuming development or producing a distributable HX CFD desktop build.

## Repository layout

```text
C:\CFD\cfd-platform
├── frontend\                         React + TypeScript + Tailwind + Three.js UI
├── src\                              Rust/Tauri desktop bridge
├── backend\
│   ├── src\cfd_backend\              FastAPI workflow backend and engine adapters
│   ├── tests\                        Backend regression suite
│   ├── pyproject.toml                 Python dependency declaration
│   └── .venv\                        Managed build/runtime environment (local only)
├── bin\backend-runtime\              Generated release runtime; do not hand-edit
├── build.rs                           Stages the managed runtime for release builds
├── tauri.conf.json                    Tauri configuration and resource list
├── installer\src\HXCFD.iss          Inno Setup installer definition
└── CONTINUATION.md                    This handover document
```

## Build-machine prerequisites

Use a 64-bit Windows 10 (1809+) or Windows 11 build machine.

Required to build the application:

- Git.
- Node.js LTS and npm.
- Rust stable with the `x86_64-pc-windows-msvc` toolchain.
- Microsoft C++ Build Tools / Windows SDK required by Rust and Tauri.
- Python **3.11 x64** for the managed backend environment.
- WebView2 Runtime for desktop testing.
- Inno Setup 6 only when compiling the optional standalone installer.
- Sufficient free disk space: allow at least **8 GB** free. The staged backend runtime is currently approximately **1 GB** before installer compression.

The installed HX CFD application should not require a system Python installation. Python is a build-time requirement because the release bundle embeds the managed runtime.

## Frontend build

From the repository root:

```powershell
Set-Location C:\CFD\cfd-platform
npm --prefix frontend ci
npm --prefix frontend run build
```

Expected output:

```text
frontend\dist\
```

Use `npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173` only for browser UI development. That server is not the desktop product and cannot execute private engineering workflows on its own.

## Python backend environment

The current working environment is:

```text
backend\.venv\Scripts\python.exe
```

The declared dependencies are in `backend\pyproject.toml`. Core packages include FastAPI, Uvicorn, SQLAlchemy/aiosqlite, Gmsh, meshio, VTK, PyVista, OpenMDAO, and Nevergrad. The `cfd` optional dependency group contains PhysicsNeMo / PhysicsNeMo-CFD and OpenFOAM parser support.

To inspect the exact working environment before rebuilding it, preserve a dependency snapshot:

```powershell
backend\.venv\Scripts\python.exe -m pip freeze | Set-Content backend\requirements-working-lock.txt
backend\.venv\Scripts\python.exe -m pip check
```

A clean environment can be created with:

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -e ".\backend[dev,cfd]"
```

Important: verify the resulting environment contains the packages actually used by report generation and the local engineering stack. The project currently has no committed fully pinned lock file, so keep a `pip freeze` snapshot from the working environment before recreating it.

## Rust/Tauri build

Useful validation commands:

```powershell
Set-Location C:\CFD\cfd-platform
cargo fmt --check
cargo check --offline
cargo build --release
```

`cargo build --release` performs the following through `build.rs`:

1. Builds the frontend from `frontend\`.
2. Stages `backend\src`, `backend\.venv`, and the base CPython runtime into `bin\backend-runtime`.
3. Does **not** build PyInstaller by default.
4. Produces the desktop executable at:

```text
target\release\cfd-platform-tauri.exe
```

### Important current Tauri bundle configuration issue

`tauri.conf.json` currently contains:

```json
"beforeDevCommand": "npm run dev -- --host 127.0.0.1 --port 5173",
"beforeBuildCommand": "npm run build"
```

but there is no `package.json` at the repository root; it is in `frontend\`. Before relying on `cargo tauri dev` or `cargo tauri build`, update those commands to use the frontend directory, for example:

```json
"beforeDevCommand": "npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173",
"beforeBuildCommand": "npm --prefix frontend run build"
```

Then install the Tauri CLI if needed and bundle:

```powershell
cargo install tauri-cli --version "^2" --locked
cargo tauri build
```

Do not claim a full installer/bundle build is complete until this configuration path is exercised from a clean shell.

## Managed backend runtime

Expected generated release layout:

```text
bin\backend-runtime\
├── HX_CFD_RUNTIME
├── launch_backend.py
├── backend\src\cfd_backend\main.py
├── python\python.exe
└── venv\Lib\site-packages\
```

Tauri release launch behavior:

1. Finds `bin\backend-runtime\backend\src\cfd_backend\main.py`.
2. Launches `bin\backend-runtime\python\python.exe`.
3. Sets `PYTHONHOME` to `bin\backend-runtime\python`.
4. Adds managed source and site packages to Python module resolution.
5. Creates an ephemeral local port and a per-launch API bearer token.
6. Sets local application data directories and starts FastAPI.
7. Waits for `/health` before reporting the backend as running.

Tauri passes these private runtime variables:

```text
CFD_PLATFORM_TAURI=1
CFD_PLATFORM_TAURI_TOKEN=<per-launch secret>
HOST=127.0.0.1
PORT=<ephemeral local port>
DATA_DIR=<app data>\data
DATABASE_URL=sqlite+aiosqlite:///<app data>/data/cfd.db
LOGS_DIR=<app data>\logs
PROJECTS_DIR=<app data>\projects
TEMP_DIR=<app data>\tmp
CACHE_DIR=<app data>\cache
PYTHONUNBUFFERED=1
PYTHONNOUSERSITE=1
PYTHONHOME=<bundled python directory>
PYTHONPATH=<backend source>;<managed site-packages>
```

Do not expose the port or token to React/browser code.

### Optional PyInstaller sidecar

The frozen sidecar is optional and not the default runtime. Only use it deliberately:

```powershell
$env:HX_CFD_BUILD_FROZEN_SIDECAR = "1"
cargo build --release
Remove-Item Env:HX_CFD_BUILD_FROZEN_SIDECAR
```

Do not use the old `bin\backend\cfd-backend.exe` as proof that the current backend works; it was previously stale and is not the preferred release path.

## Installer build

The installer source of record is:

```text
installer\src\HXCFD.iss
```

It expects:

```text
target\release\cfd-platform-tauri.exe
bin\backend-runtime\**
```

After a successful release build, compile the Inno script using Inno Setup:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\src\HXCFD.iss
```

Expected installer output directory:

```text
installer\output\
```

Installer smoke test requirements:

1. Test on a clean Windows profile or VM.
2. Do not install Python on the test VM.
3. Install HX CFD.
4. Launch `HX CFD.exe`.
5. Confirm backend automatically reaches healthy state.
6. Confirm unauthenticated localhost workflow requests are rejected.
7. Create a local project and verify data is written under the user application-data location.
8. Uninstall and verify the private backend process tree stops without killing unrelated `python.exe` processes.

## External engineering engine setup

The backend can only execute engines that are installed and runnable locally. Configure their executable paths before claiming full-stack capability.

| Engine / capability | Current status | Needed to complete |
| --- | --- | --- |
| Gmsh | Ready and tested | Keep Python package/runtime available. |
| meshio | Ready and tested | Keep managed package available. |
| VTK / PyVista | Ready and tested | Keep managed packages available. |
| OpenMDAO | Ready and tested | Keep managed package available. |
| Nevergrad | Ready and tested | Keep managed package available. |
| PhysicsNeMo / CFD | Ready and manually tested | Preserve compatible local Python/CUDA dependencies as applicable. |
| FreeCAD | Not runnable | Install/configure executable; test STEP/IGES/BREP/STL/OBJ import. |
| OpenFOAM | Not runnable | Install/configure Windows-compatible executable/toolchain; test `gmshToFoam`, `checkMesh`, solver, and `foamToVTK`. |
| ParaView | Not runnable | Install/configure executable; test advanced visualization integration. |
| Three.js / R3F / drei | Frontend dependency | Installed through `frontend\package-lock.json`. |

Never replace an unavailable external solver, CAD engine, or visualizer with dummy output. The intended behavior is an actionable unavailable/error state.

## Required end-to-end acceptance checklist

Run these tests before declaring a release usable:

- [ ] `npm --prefix frontend run build` succeeds.
- [ ] Backend test suite succeeds.
- [ ] `cargo fmt --check` succeeds.
- [ ] `cargo check --offline` succeeds.
- [ ] `cargo build --release` succeeds and recreates `bin\backend-runtime`.
- [ ] Direct staged-runtime health/auth/project-create test succeeds.
- [ ] `cargo tauri build` succeeds after correcting the frontend command configuration above.
- [ ] Installer builds successfully.
- [ ] Clean-VM install and automatic backend startup succeeds without system Python.
- [ ] Geometry → mesh workflow passes using Gmsh.
- [ ] Explicit mesh boundary groups are visible and correct.
- [ ] OpenFOAM chain passes after OpenFOAM is installed.
- [ ] Results conversion/visualization passes after required engines are installed.
- [ ] PDF report is generated only from verified real result evidence.
- [ ] Optimization and surrogate stages publish real artifacts.

## Fast diagnostics

### Backend does not start in desktop app

1. Open HX CFD backend logs from the desktop diagnostics surface.
2. Confirm `bin\backend-runtime\HX_CFD_RUNTIME`, `python\python.exe`, `launch_backend.py`, and backend source exist beside packaged resources.
3. Confirm the staged runtime was not replaced by a stale sidecar.
4. Confirm the local data directory is writable.
5. Confirm no security product blocked the embedded `python.exe`.
6. Verify the backend database URL uses `sqlite+aiosqlite:///`, not a synchronous `sqlite:///` URL.

### A workflow says an engine is unavailable

1. Refresh engine inventory.
2. Check the engine executable and version from the backend logs.
3. Configure the local executable/path rather than adding a mock fallback.
4. Re-run the smallest relevant workflow test.

### Build is slow

- The managed runtime is roughly 1 GB and resource scanning/copying can make release packaging and some Rust checks slow.
- Run frontend and backend tests independently while investigating build problems.
- Do not interrupt a release staging operation after it removes/replaces `bin\backend-runtime`; if interrupted, rerun the release stage or restore the completed generated runtime before packaging.

## Files that should not be casually removed

- `backend\.venv\` — currently contains the working local engineering Python environment.
- `bin\backend-runtime\` — generated managed release runtime.
- `Cargo.lock` and `frontend\package-lock.json` — dependency reproducibility inputs.
- `backend\pyproject.toml` — backend dependency declaration.
- `tauri.conf.json`, `build.rs`, and `src\backend.rs` — desktop lifecycle and bundling contract.
- `installer\src\HXCFD.iss` — installer contract.
