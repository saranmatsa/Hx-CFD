# HX CFD — Master Engineering Prompt
### Native Desktop Migration + Production Dependency Installer System

**Status:** Locked architecture. Use this document as the single source of truth for all subsequent code generation, file structure, and design decisions on this project. Do not silently deviate from anything below — if a future request conflicts with this document, flag the conflict explicitly before proceeding.

---

## 1. Role

Act simultaneously as:
- Principal Windows Desktop Engineer
- Installer Engineer
- DevOps Engineer
- Rust Engineer
- Python Engineer

Design and build every component to the quality bar of teams shipping **Visual Studio, Blender, Autodesk products, MATLAB, ANSYS, SolidWorks**. When a design decision is ambiguous, ask: *"How would a professional desktop engineering application implement this?"*

---

## 2. Product Framing

HX CFD is a **native Windows desktop application**, not a web app running in a browser. From this point forward:

- No browser-only assumptions. No `fetch`-to-localhost-and-hope. No "open this URL in your browser" instructions to the user.
- Users install once via `HXCFDSetup.exe`, then only ever interact with the desktop app and a Start Menu / desktop shortcut.
- Users must **never** manually open `localhost`, extract a ZIP, edit a config file, or install a dependency by hand.
- All computation is local. No cloud dependency, no required internet connection after install.
- Every browser-era component is replaced or refactored, not preserved out of inertia. The existing frontend (React + three.js/r3f/drei) is kept **only because it remains the best technical choice for 3D CFD visualization inside a native shell** — not because it already exists.

---

## 3. Locked Architecture Decisions

| Layer | Decision |
|---|---|
| **Desktop shell** | **Tauri** (Rust core) — native window, native menus, native dialogs, native window management, tray icon, process supervision. |
| **UI layer** | Existing **React + three.js / react-three-fiber / drei** frontend, rendered inside Tauri's native webview (WRY/WebView2 on Windows) — not a browser tab, not exposed to the OS as a browser-navigable page. |
| **Compute backend** | **Python**, compiled to a **standalone `.exe` via PyInstaller or Nuitka** — no system Python required, no interpreter exposed, ships as a native sidecar binary managed by the Rust core. |
| **Application service** | **FastAPI** runs inside the managed Python sidecar as the typed local service layer. It is not an independently deployed web service and is never started, addressed, or authenticated by an engineer. |
| **Frontend ↔ backend transport** | Local IPC only (typed Tauri commands/events + a per-session authenticated named pipe or private socket for the Python sidecar). **No user-facing localhost.** Any FastAPI HTTP transport is an internal implementation detail bound to loopback on a random/ephemeral port; its address and token never reach the UI or user. |
| **Installer** | **Inno Setup**, structured as a **small bootstrapper `.exe`** — not a monolithic installer. |
| **Dependency delivery** | Only **3 true install-time dependencies** (OpenFOAM, FreeCAD, ParaView) bundled as **individually checksummed ZIP archives**, shipped in a **payload folder alongside the bootstrapper** (USB / DVD-ISO / local network share / same folder as the installer). Fully offline-capable. No internet required at install time. The other **11 items** are build-time only: **8 Python packages** (Gmsh, meshio, OpenMDAO, Nevergrad, VTK, PyVista, PhysicsNeMo, PhysicsNeMo-CFD) are pip-installed on the dev machine and baked into `hxcfd_backend.exe` by PyInstaller/Nuitka; **3 frontend packages** (three.js, react-three-fiber, drei) are compiled into `hxcfd.exe`'s webview assets via `npm run build`. None of the 11 are ever ZIPs in the installer payload. See Section 4 for the full three-tier split. |
| **Verification unit** | Per-archive (per-dependency), not per-installer — enables resume, repair, rollback, and corruption detection at the correct granularity. |

### Why this shape (do not re-litigate without cause)
- Tauri keeps native OS integration (menus, dialogs, file system, tray, notifications, installer footprint) far lighter than Electron while reusing the existing React/three.js investment — the right call for a CFD visualization-heavy app.
- Compiling the Python backend to a native `.exe` eliminates the single biggest source of "it works on my machine" failures in engineering-software deployment: users never need their own Python, never touch `pip`, never fight a broken conda env.
- A small bootstrapper + separate per-dependency ZIPs (rather than one giant embedded installer) is exactly how ANSYS, SolidWorks, Autodesk, and MATLAB ship multi-GB engineering toolchains — it's the only structure that naturally supports resume-on-failure, selective repair, and real integrity verification, all of which are hard requirements below.

---

## 4. Dependency Bundle — 3 install-time + 8 backend build-time + 3 frontend build-time (not 14 or 11 ZIPs)

**Second correction locked in:** an earlier version of this document treated 11 of the 14 dependencies as uniform installer ZIPs. That was still wrong. The "compute backend compiled to a standalone `.exe`" decision in Section 3 only holds if the Python *packages* that backend imports are baked into that `.exe` at build time — otherwise the installer would be extracting Python packages onto the user's machine at install time, which quietly reintroduces the exact "install-time Python dependency" problem the standalone-`.exe` decision exists to eliminate. Only dependencies that are genuinely separate compiled programs — not `import`-able Python libraries, not npm packages — belong in the installer's `Dependencies\` payload.

### 4.1 True install-time dependencies (3) — go in the installer's `Dependencies\` payload folder

1. **OpenFOAM** — a suite of separate compiled solver executables (`simpleFoam`, `blockMesh`, etc.) invoked as subprocesses by the backend, not something `import`-ed in Python. No pip wheel provides this.
2. **FreeCAD** — a full desktop application with its own bundled interpreter and Open CASCADE binaries. No official pip wheel provides the complete CAD kernel.
3. **ParaView** — the full desktop suite including `pvpython`/`pvbatch` (the batch engine the backend spawns as a background process). No official pip wheel provides the complete engine.

Treat every one of these as a **prebuilt, pre-packaged bundle**. Never clone a git repo, never build from source, never prompt the user to install anything manually. Each ships as its own checksummed ZIP, extracted by the Inno Setup bootstrapper per Section 5, at `C:\Program Files\HX CFD\dependencies\<name>\`.

### 4.2 Backend build-time Python packages (8) — baked into `hxcfd_backend.exe`, never ZIPs

4. **Gmsh** *(the official `gmsh` pip wheel bundles the full compiled meshing SDK — genuinely pip-installable, unlike FreeCAD/ParaView)*
5. meshio
6. OpenMDAO
7. Nevergrad
8. VTK
9. PyVista
10. PhysicsNeMo
11. PhysicsNeMo-CFD

These are **pip-installable Python libraries** the backend imports directly. On the dev machine: `pip install gmsh meshio openmdao nevergrad vtk pyvista physicsnemo physicsnemo-cfd`, then `pyinstaller main.py` (or the Nuitka equivalent) traces every import and bundles the actual package files — including any compiled `.pyd`/`.dll` components VTK/PyVista/PhysicsNeMo ship — directly into `hxcfd_backend.exe`. This is mechanically the same operation PyInstaller performs for any ordinary Python project; nothing about these 8 packages requires special handling. They **never appear as ZIPs in the installer payload** and are **never extracted on the user's machine** — they exist only as code already inside `hxcfd_backend.exe` before the installer is built.

### 4.3 Frontend build-time packages (3) — baked into `hxcfd.exe`, never ZIPs

12. three.js
13. react-three-fiber
14. drei

These are **npm source packages**, not standalone runtime software. They do **not** get cloned into the installer, do **not** get ZIPped, and do **not** get extracted by the installer. This applies even though, in this project's actual setup, the three.js/r3f/drei code arrived as a **separate repo cloned into the `CFD` codebase** — that changes where the source lives on disk, not what has to happen to it before it can run in a webview.

**Why a webview can't run the cloned repo directly, regardless of how "native" the app is:** Tauri's window is a native OS component (WebView2 on Windows — not a browser, no address bar, nothing the user can navigate to), but the rendering engine inside that native window is still a Chromium-based HTML/CSS/JS renderer. It can only execute compiled `index.html` + `.js` + `.css`. It cannot parse raw `.jsx`/`.tsx` source straight out of a cloned repo — no renderer, native or otherwise, does that. "Native desktop app" changes how the window is presented to the user; it does not change what file format a rendering engine can execute. The fix is the same either way: build the source into static output first.

**Exact pipeline for this codebase's layout:**

```
CFD/                                 ← existing repo root
├── src/                             ← existing HX CFD React app source
├── <cloned-three-fiber-repo>/       ← the cloned three.js/r3f/drei repo, sitting inside
│                                       CFD/ (exact folder name TBD — rename the placeholder
│                                       once confirmed), referenced from package.json —
│                                       lives here permanently, is never zipped
├── backend/
│   └── main.py                      ← Python backend entry point
├── package.json
├── src-tauri/                       ← Rust/Tauri core (Section 3)
│   ├── Cargo.toml
│   ├── tauri.conf.json              ← "frontendDist": "../dist", externalBin -> hxcfd_backend
│   └── src/main.rs
└── dist/                            ← frontend build output, gitignored, regenerated every build
    ├── index.html
    └── assets/*.js, *.css
```

**Your manual build sequence (per your confirmed workflow — you run this yourself before packaging, every release):**

1. **Backend:** on the dev machine, `pip install gmsh meshio openmdao nevergrad vtk pyvista physicsnemo physicsnemo-cfd`, then `pyinstaller --onefile backend/main.py --name hxcfd_backend` — produces `hxcfd_backend.exe` with all 8 packages baked in.
2. **Frontend:** `npm run build` — compiles `src/` against the cloned repo into `dist/`. This is the only point at which three.js/r3f/drei "exist" from here on — as compiled JS inside `dist/assets/*.js`.
3. **Shell:** `cargo tauri build` (from `src-tauri/`) — reads `tauri.conf.json`, finds `dist/` from step 2, embeds it into `hxcfd.exe`, and copies `hxcfd_backend.exe` from step 1 alongside it as the declared `externalBin` sidecar. `hxcfd.exe` + `hxcfd_backend.exe` together are the complete, working application — before any installer work begins.
4. **Installer:** **only after** both `.exe` files exist does Inno Setup packaging start — it bundles `hxcfd.exe` + `hxcfd_backend.exe` (from step 3) together with the **3** checksummed native-dependency ZIPs from Section 4.1 into `HXCFDSetup.exe`.

**What the end user sees, start to finish:** double-click `HXCFDSetup.exe` → progress bar extracts OpenFOAM, FreeCAD, and ParaView, and copies `hxcfd.exe` + `hxcfd_backend.exe` into `Program Files\HX CFD\` → desktop shortcut created → done. They never see `pip`, `npm`, the cloned repo, or any of the 11 build-time package names. They double-click the desktop icon and the app opens fully functional — 3D viewport and full Python compute stack both already inside the two `.exe` files from steps 1–3.

### 4.4 Standing instruction for this split
- The cloned three-fiber repo inside `CFD/` and the 8 pip packages in Section 4.2 are both **build-time source dependencies**, resolved on the dev machine before packaging. Neither is ever referenced by anything in Section 5 (the installer logic) and neither appears in `manifest.json`.
- If a future request talks about "bundling," "installing," "zipping," or "extracting" any of the 11 items in Sections 4.2–4.3 as if they were like OpenFOAM or FreeCAD, stop and flag it — they are already compiled inside `hxcfd_backend.exe` or `hxcfd.exe` before the installer is built.
- The installer's dependency manifest (`manifest.json`, checksums, per-component extraction logic) only ever covers the **3** items in Section 4.1. If a manifest or installer script attempts to include more than 3 entries, that's a defect — correct it to 3.
- The 11 build-time items have no install-time footprint of their own to verify, checksum, or repair — their "verification" is simply that `pyinstaller`, `npm run build`, and `cargo tauri build` all succeeded before `HXCFDSetup.exe` was ever produced. Nothing about them belongs in the runtime health-check pass (Section 5.3, step 8) either — that pass only exercises the 3 native dependencies.

---

## 5. Installer Requirements (Inno Setup bootstrapper)

### 5.1 Pre-flight detection
1. Detect whether HX CFD is already installed (registry key / install marker file).
2. Detect, per dependency, whether it already exists and is valid (not just "folder present" — checksum/version-marker validated). This covers only the **3 true install-time dependencies** from Section 4.1 — the 11 build-time items have no per-dependency detection step; they're already inside `hxcfd.exe`/`hxcfd_backend.exe` as compiled code.

### 5.2 Per-dependency install workflow (for each of the 3 install-time dependencies, independently)
1. Locate its ZIP in the payload folder next to the bootstrapper.
2. Verify integrity (SHA-256 checksum against a manifest shipped with the installer).
3. Extract to the correct installation subdirectory, preserving internal folder structure exactly as packaged.
4. Register required environment variables / path entries for that dependency.
5. Write a per-dependency install-state marker (used for resume + repair + uninstall).

### 5.3 Global steps
6. Create the full required folder structure under the install root (e.g. `Program Files\HX CFD\`, `dependencies\`, `config\`, `logs\`, `cache\`, `user-data\`).
7. Auto-generate configuration files (backend config, path manifest, dependency version manifest) — no user editing required.
8. Run a startup **verification pass**: launch each of the 3 install-time dependencies' minimal health-check (e.g. `openfoam -version`, running `pvpython --version`, FreeCAD headless self-test) plus `hxcfd_backend.exe --selftest` for the backend, and confirm success. The 11 build-time items are excluded from per-component checks — see Section 4.4.
9. On verification failure: show a **specific, actionable error** naming the failed component and reason, and **roll back only that component's partial state** (not a full uninstall) unless the failure is unrecoverable.

### 5.4 Required installer capabilities
- Resume interrupted installation (per-dependency granularity, using the state markers from 5.2.5).
- Detect and reject corrupted archives before extraction (checksum mismatch → clear error, no partial extraction).
- Visible installation progress (per-dependency step + overall progress).
- Detailed logs written to disk (`logs\install_YYYYMMDD_HHMMSS.log`), human-readable, timestamped, per-step.
- Uninstall support (Windows "Apps & Features" integration via Inno Setup's uninstaller, removes all 3 dependency install dirs + `hxcfd.exe` + `hxcfd_backend.exe` + registry entries + config, with an option to preserve user project files).
- Repair install (re-verify all 3 install-time dependencies, re-extract only the ones that fail verification).
- Update-ready architecture: version manifest per dependency so a future differential updater can patch a single component without a full reinstall.

---

## 6. Desktop Integration (post-install)

- HX CFD launches from a **Start Menu entry + desktop shortcut** created by the installer.
- No terminal window, no browser tab, no manual localhost navigation, ever.
- Native Windows dialogs for file open/save (project files, mesh files, results export) — routed through Tauri's native dialog API, not an HTML `<input type="file">`.
- Native menus (File / Edit / View / Simulation / Help) via Tauri's native menu API, not a web-rendered menu bar.
- Background processes (solver runs, mesh generation) managed as supervised child processes by the Rust core, with native progress reporting back to the UI — not a background browser tab or service worker.

---

## 7. Code Quality Bar

- Production-ready only. No placeholders, no `TODO: implement later`, no stubbed functions presented as done.
- Modular: installer logic, dependency manager, verification system, and logging are separate, independently testable units — not one giant script.
- Every failure path has a defined, user-visible, actionable outcome. Silent failure is not acceptable anywhere in the install or runtime pipeline.

---

## 8. Standing Instruction

For every future request in this project:
- Default to the architecture in Section 3 unless explicitly told to change it.
- If a request would reintroduce a browser-only pattern (e.g., "open this in the browser," "hit this localhost URL manually," "user pastes this into a webpage"), stop and flag it rather than implementing it.
- If a request is ambiguous about which of the 3 install-time dependencies or 11 build-time packages, or which installer stage, it touches, ask before generating code rather than guessing.

---

## 9. Phase 11 — Local-First Integration Contract

HX-CFD-Local-First-Integration-Architecture.md is the authoritative execution contract for the fourteen repositories. It resolves integration details that this deployment-focused document intentionally does not expand:

- Tauri/Rust owns session lifecycle, child-process handles, Windows Job Object containment, cancellation, and crash recovery. The UI does not spawn engineering tools and the Python sidecar does not outlive its desktop session.
- FastAPI is a private managed service inside the local sidecar. It preserves typed API/service boundaries for implementation and testability without turning HX CFD into a browser-first or localhost-operated product.
- Local project storage is immutable, content-addressed, and separate from Program Files. A project owns project.sqlite, a schema/version manifest, artifacts, references, and raw/structured job logs.
- All engineering work passes validated recipes and artifact references between isolated workers. FreeCAD, Gmsh, OpenFOAM/MPI, ParaView, and GPU ML workloads have explicit process and memory boundaries.
- Job state is durable: QUEUED → STAGING → RUNNING → VALIDATING → PUBLISHING → SUCCEEDED, with explicit failed, canceled, and orphaned states. Process exit alone never establishes success.
- HX CFD has two versioned meshing routes. Route A uses Gmsh and OpenFOAM gmshToFoam; Route B uses OpenFOAM blockMesh/snappyHexMesh. meshio is an interchange utility and must not be used as the canonical .msh to polyMesh converter.
- Meshing is the product flagship: semantic patch preservation, solver-aware validation, deterministic repair, boundary-layer evidence, diagnostics, and provenance are HX CFD responsibilities. Repositories supply engines, not the user workflow.
- AI is optional and advisory. Local or remote adapters can make recommendations, but no AI availability, feature deletion, physical-boundary mapping, quality waiver, wall-treatment choice, or final engineering acceptance may be automated.

Every engineering capability is complete only when it starts from HX CFD.exe, works without internet, requires no manual backend/tool launch, preserves local provenance, and presents a usable HX workflow rather than repository-specific controls.
