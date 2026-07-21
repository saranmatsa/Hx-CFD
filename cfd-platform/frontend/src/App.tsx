import { useEffect, useMemo, useState, type ReactNode } from "react";
import { open, save } from "@tauri-apps/plugin-dialog";
import { Viewport3D } from "./components/viewport/Viewport3D";
import {
  archiveLocalProject,
  checkBackendHealth,
  configureWorkflowStage,
  createLocalProject,
  deleteLocalProject,
  executeWorkflowStage,
  exportWorkflowArtifact,
  getBackendStatus,
  getEngineInventory,
  getWorkflowSnapshot,
  listLocalProjects,
  openLocalProject,
  renameLocalProject,
  readWorkflowArtifact,
  startBackend,
  type EngineCapability,
  type LocalProject,
  type WorkflowArtifact,
  type WorkflowArtifactContent,
  type WorkflowExecution,
  type WorkflowSnapshot,
} from "./services/desktopWorkflow";

type AppScreen = "wind-tunnel" | "projects" | "profile" | "documentation";
type TunnelStep = "import" | "mesh" | "setup" | "run" | "results" | "improve";
type BackendReadiness = "checking" | "starting" | "ready" | "offline";
type IconName =
  | "tunnel"
  | "projects"
  | "profile"
  | "docs"
  | "import"
  | "mesh"
  | "setup"
  | "run"
  | "results"
  | "improve"
  | "search"
  | "bell"
  | "chevron"
  | "play"
  | "gear"
  | "plus"
  | "close"
  | "check"
  | "warning"
  | "spark"
  | "report"
  | "folder"
  | "cpu"
  | "help"
  | "archive"
  | "trash"
  | "eye";

type Field = {
  label: string;
  value: string;
  options?: string[];
  unit?: string;
  placeholder?: string;
};

const iconPaths: Record<IconName, ReactNode> = {
  tunnel: (
    <>
      <path d="M3 6h13.5A4.5 4.5 0 0 1 21 10.5V18H3z" />
      <path d="M3 6V4h13.5A4.5 4.5 0 0 1 21 8.5v2M7 18v3m10-3v3M7 11h7" />
    </>
  ),
  projects: (
    <>
      <path d="M3 6.5A2.5 2.5 0 0 1 5.5 4H10l2 2.5h6.5A2.5 2.5 0 0 1 21 9v8.5a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" />
      <path d="M3 9h18" />
    </>
  ),
  profile: (
    <>
      <circle cx="12" cy="8" r="3.4" />
      <path d="M4.5 20c.8-4 3.3-6 7.5-6s6.7 2 7.5 6" />
    </>
  ),
  docs: (
    <>
      <path d="M5 3h11l3 3v15H5z" />
      <path d="M16 3v4h4M8 12h8M8 16h6" />
    </>
  ),
  import: (
    <>
      <path d="M12 15V3m0 0L7.5 7.5M12 3l4.5 4.5" />
      <path d="M5 13v6h14v-6" />
    </>
  ),
  mesh: <path d="M4 5h16M4 12h16M4 19h16M7 3l3 18M17 3l-3 18" />,
  setup: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.05 2.05-.06-.06A1.7 1.7 0 0 0 15.8 18.6a1.7 1.7 0 0 0-1 1.55v.1h-2.9v-.1a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.05-2.05.06-.06A1.7 1.7 0 0 0 7.3 15a1.7 1.7 0 0 0-1.55-1H5.6v-2.9h.15a1.7 1.7 0 0 0 1.55-1 1.7 1.7 0 0 0-.34-1.88l-.06-.06L8.95 6.1l.06.06A1.7 1.7 0 0 0 10.9 6.5a1.7 1.7 0 0 0 1-1.55v-.1h2.9v.1a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.05 2.05-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.55 1h.1V14h-.1a1.7 1.7 0 0 0-1.54 1Z" />
    </>
  ),
  run: (
    <>
      <path d="M5 5h5v5H5zM14 14h5v5h-5zM7.5 10v2a2 2 0 0 0 2 2H14" />
      <path d="m12 17 2 2 2-2" />
    </>
  ),
  results: (
    <>
      <path d="M4 20V4M4 20h17" />
      <path d="m7 15 4-4 3 2 5-7" />
    </>
  ),
  improve: (
    <>
      <path d="M4 19 9 13l3 3 7-10" />
      <path d="M15 6h4v4" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="m15 15 5 5" />
    </>
  ),
  bell: <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />,
  chevron: <path d="m8 10 4 4 4-4" />,
  play: <path d="m9 5 10 7-10 7z" />,
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M4 12h2m12 0h2M12 4v2m0 12v2M6.3 6.3l1.4 1.4m8.6 8.6 1.4 1.4m0-11.4-1.4 1.4m-8.6 8.6-1.4 1.4" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  check: <path d="m5 12 4 4L19 6" />,
  warning: (
    <>
      <path d="M12 3 2.8 20h18.4L12 3Z" />
      <path d="M12 9v4m0 3h.01" />
    </>
  ),
  spark: (
    <path d="M12 2.8 13.9 9l6.3 1.9-6.3 1.9L12 19l-1.9-6.2-6.3-1.9L10.1 9 12 2.8Z" />
  ),
  report: (
    <>
      <path d="M6 3h9l3 3v15H6zM14 3v4h4" />
      <path d="M9 12h6m-6 4h6" />
    </>
  ),
  folder: (
    <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H10l2 2.5h6.5A2.5 2.5 0 0 1 21 10v7.5a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" />
  ),
  cpu: (
    <>
      <rect x="7" y="7" width="10" height="10" rx="1" />
      <path d="M9 1v3m6-3v3M9 20v3m6-3v3M1 9h3m16 0h3M1 15h3m16 0h3" />
    </>
  ),
  help: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.6 9a2.5 2.5 0 1 1 4.52 1.48c-.7.9-2.12 1.37-2.12 2.52" />
      <path d="M12 17h.01" />
    </>
  ),
  archive: (
    <>
      <path d="M4 7h16v13H4zM3 4h18v3H3z" />
      <path d="M9 12h6" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16M10 11v5m4-5v5M6 7l1 14h10l1-14M9 7V4h6v3" />
    </>
  ),
  eye: (
    <>
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="2.5" />
    </>
  ),
};

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.55"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {iconPaths[name]}
    </svg>
  );
}

function MaverickMark({ className = "h-7 w-10" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 96 54"
      fill="none"
      aria-label="Maverick"
    >
      <path
        d="M8 27C8 13 25 7 48 7s40 6 40 20-17 20-40 20S8 41 8 27Z"
        stroke="currentColor"
        strokeWidth="3.8"
      />
      <path
        d="M29 35V19l19 17 19-17v16"
        stroke="currentColor"
        strokeWidth="4.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const nav: Array<{ id: AppScreen; label: string; icon: IconName }> = [
  { id: "wind-tunnel", label: "Wind Tunnel", icon: "tunnel" },
  { id: "projects", label: "Projects", icon: "projects" },
  { id: "profile", label: "Profile", icon: "profile" },
  { id: "documentation", label: "Documentation", icon: "docs" },
];

const steps: Record<
  TunnelStep,
  {
    label: string;
    backend: string;
    icon: IconName;
    title: string;
    description: string;
    action: string;
    fields: Field[];
    advanced?: Field[];
  }
> = {
  import: {
    label: "Import + prepare",
    backend: "geometry",
    icon: "import",
    title: "Bring the model into the tunnel",
    description:
      "Choose a solid CAD exchange file. HX CFD prepares STEP, IGES, or BREP geometry before any mesh is created.",
    action: "Prepare geometry",
    fields: [
      {
        label: "Source",
        value: "",
        placeholder: "Select a STEP, IGES, or BREP solid",
      },
    ],
    advanced: [
      {
        label: "Units",
        value: "Millimeters",
        options: ["Millimeters", "Meters", "Inches"],
      },
    ],
  },
  mesh: {
    label: "Mesh",
    backend: "meshing",
    icon: "mesh",
    title: "Build a trustworthy flow volume",
    description:
      "Select the mesh intent. Use the Geometry report's surface IDs to name flow boundaries; HX CFD never guesses an inlet or outlet.",
    action: "Generate mesh",
    fields: [
      {
        label: "Mesh quality",
        value: "Balanced",
        options: ["Fast", "Balanced", "Fine"],
      },
    ],
    advanced: [
      { label: "Base size", value: "1.20", unit: "mm" },
      {
        label: "Boundary layers",
        value: "12",
        options: ["0", "6", "12", "18"],
      },
      { label: "Growth rate", value: "1.18" },
      {
        label: "Inlet surface IDs",
        value: "",
        placeholder: "Geometry report IDs, e.g. 1",
      },
      {
        label: "Outlet surface IDs",
        value: "",
        placeholder: "Geometry report IDs, e.g. 2",
      },
      {
        label: "Wall surface IDs",
        value: "",
        placeholder: "Optional comma-separated IDs",
      },
      {
        label: "Symmetry surface IDs",
        value: "",
        placeholder: "Optional comma-separated IDs",
      },
      {
        label: "Unassigned surfaces",
        value: "Keep as unassigned patch",
        options: ["Keep as unassigned patch", "Group remaining as walls"],
      },
    ],
  },
  setup: {
    label: "Setup",
    backend: "physics",
    icon: "setup",
    title: "Set the aerodynamic case",
    description:
      "Define the fluid and turbulence model before the solver is armed. Advanced inputs remain available for engineering review.",
    action: "Save simulation setup",
    fields: [
      {
        label: "Fluid",
        value: "Air (ideal gas)",
        options: ["Air (ideal gas)", "Water (liquid)"],
      },
      {
        label: "Energy equation",
        value: "Disabled",
        options: ["Enabled", "Disabled"],
      },
    ],
    advanced: [
      {
        label: "Turbulence model",
        value: "k-ω SST",
        options: ["k-ε Realizable", "k-ω SST"],
      },
      { label: "Reference pressure", value: "101325", unit: "Pa" },
      {
        label: "Inlet patch",
        value: "inlet",
        placeholder: "Named OpenFOAM inlet patch",
      },
      {
        label: "Outlet patch",
        value: "outlet",
        placeholder: "Named OpenFOAM outlet patch",
      },
      {
        label: "Wall patches",
        value: "walls",
        placeholder: "Comma-separated named wall patches",
      },
      {
        label: "Symmetry patches",
        value: "",
        placeholder: "Optional comma-separated patches",
      },
      { label: "Inlet velocity", value: "20, 0, 0", unit: "m/s" },
      { label: "Turbulence intensity", value: "5", unit: "%" },
      { label: "Turbulence length scale", value: "0.01", unit: "m" },
    ],
  },
  run: {
    label: "Run",
    backend: "solver",
    icon: "run",
    title: "Run the CFD case",
    description:
      "Create a local solver revision from the accepted mesh and setup. HX CFD reports the real solver outcome, never artificial progress.",
    action: "Run local solver",
    fields: [
      {
        label: "Run type",
        value: "Steady flow",
        options: ["Steady flow", "Transient flow"],
      },
    ],
    advanced: [
      { label: "Maximum iterations", value: "5000" },
      { label: "Residual target", value: "1e-05" },
    ],
  },
  results: {
    label: "Results",
    backend: "results",
    icon: "results",
    title: "Review aerodynamic evidence",
    description:
      "Publish a result view from the completed solver artifacts. Field displays appear only when the real dataset is available.",
    action: "Generate result view",
    fields: [],
  },
  improve: {
    label: "Improve + report",
    backend: "reports",
    icon: "improve",
    title: "Turn evidence into a decision",
    description:
      "Generate a project report or run an optimization study against a project-owned evaluation function.",
    action: "Generate report",
    fields: [
      {
        label: "Template",
        value: "Engineering review",
        options: ["Engineering review", "Performance summary"],
      },
    ],
    advanced: [
      {
        label: "Evaluator module",
        value: "",
        placeholder: "Project optimization evaluator path",
      },
      { label: "Design variable", value: "scale" },
      { label: "Budget", value: "20" },
      {
        label: "Training module",
        value: "",
        placeholder: "Project PhysicsNeMo trainer path",
      },
      {
        label: "Dataset path",
        value: "",
        placeholder: "Labelled local surrogate dataset",
      },
    ],
  },
};

const orderedSteps = Object.keys(steps) as TunnelStep[];
const defaultValues = (step: TunnelStep) =>
  Object.fromEntries(
    [...steps[step].fields, ...(steps[step].advanced ?? [])].map((field) => [
      field.label,
      field.value,
    ]),
  );
const activeProjectDefault = "aero-turbine-study";

function shortError(error: unknown) {
  const detail = error instanceof Error ? error.message : String(error);
  if (/unavailable|not available/i.test(detail))
    return "A required local engineering tool is not ready on this workstation.";
  if (/blocked|configured|must be configured/i.test(detail))
    return "This action needs evidence from an earlier tunnel stage.";
  if (/source|cad file|geometry/i.test(detail))
    return "Select a valid local CAD file before preparing the geometry.";
  return "The engineering action did not complete. Review the technical details before retrying.";
}

function stageState(snapshot: WorkflowSnapshot | null, backend: string) {
  const job = snapshot?.jobs.find((job) => job.stage === backend) as
    | Record<string, unknown>
    | undefined;
  if (job?.state === "FAILED") return "attention";
  if (snapshot?.latest_outputs?.[backend]) return "complete";
  if (
    snapshot?.stages.find((stage) => stage.id === backend)?.status ===
    "configured"
  )
    return "ready";
  return "waiting";
}

function statusStyle(status: string) {
  if (status === "complete") return "border-lab-green/40 text-lab-green";
  if (status === "attention") return "border-lab-red/40 text-lab-red";
  if (status === "ready") return "border-lab-blue/40 text-[#9ec2ff]";
  return "border-lab-line text-lab-dim";
}

function artifactIdFrom(value: unknown): string | undefined {
  if (!value || typeof value !== "object") return undefined;
  const artifactId = (value as { artifact_id?: unknown }).artifact_id;
  return typeof artifactId === "string" ? artifactId : undefined;
}

function Panel({
  title,
  children,
  className = "",
  action,
}: {
  title: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <section
      className={`flex min-h-0 flex-col overflow-hidden rounded-[4px] border border-lab-line bg-lab-surface shadow-panel ${className}`}
    >
      <header className="flex h-9 shrink-0 items-center justify-between border-b border-lab-line px-3">
        <span className="text-[10px] font-medium uppercase tracking-[.09em] text-lab-muted">
          {title}
        </span>
        {action}
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}

function FieldControl({
  field,
  value,
  onChange,
}: {
  field: Field;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1.5 text-[11px] text-lab-muted">
      <span>{field.label}</span>
      {field.options ? (
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-8 rounded-[3px] border border-lab-line bg-lab-raised px-2 text-[11px] text-lab-ink outline-none transition-colors duration-100 ease-instrument hover:border-lab-strongLine"
        >
          {field.options.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
      ) : (
        <div className="flex h-8 items-center rounded-[3px] border border-lab-line bg-lab-raised transition-colors duration-100 ease-instrument hover:border-lab-strongLine">
          <input
            value={value}
            placeholder={field.placeholder}
            onChange={(event) => onChange(event.target.value)}
            className="min-w-0 flex-1 bg-transparent px-2 text-[11px] text-lab-ink outline-none placeholder:text-lab-dim"
          />
          {field.unit && (
            <span className="pr-2 font-data text-[10px] text-lab-dim">
              {field.unit}
            </span>
          )}
        </div>
      )}
    </label>
  );
}

function Maverick({
  open,
  onClose,
  step,
  execution,
  engines,
}: {
  open: boolean;
  onClose: () => void;
  step: TunnelStep;
  execution?: WorkflowExecution;
  engines: EngineCapability[];
}) {
  if (!open) return null;
  const ready = engines.filter(
    (engine) => engine.status === "ready" || engine.status === "bundled",
  ).length;
  return (
    <aside className="flex min-h-0 w-[288px] flex-col overflow-hidden rounded-[4px] border border-lab-line bg-lab-surface shadow-panel">
      <header className="flex h-10 items-center gap-2 border-b border-lab-line px-3">
        <MaverickMark className="h-5 w-8 text-lab-ink" />
        <div className="min-w-0 flex-1">
          <span className="block text-[11px] font-medium text-lab-ink">
            Maverick
          </span>
          <span className="block text-[9px] uppercase tracking-[.09em] text-lab-dim">
            Engineering companion
          </span>
        </div>
        <button
          onClick={onClose}
          className="grid h-6 w-6 place-items-center rounded-[3px] text-lab-muted transition-colors hover:bg-lab-hover hover:text-lab-ink"
          aria-label="Close Maverick"
        >
          <Icon name="close" size={15} />
        </button>
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-3">
        <div className="rounded-[3px] border border-lab-line bg-[#0a0c0e] p-3">
          <div className="mb-2 flex items-center gap-2 text-lab-ink">
            <MaverickMark className="h-5 w-7" />
            <span className="text-[11px] font-medium">
              Current tunnel context
            </span>
          </div>
          <p className="text-[11px] leading-5 text-lab-muted">
            Maverick has not generated engineering advice. Connect a local or
            remote AI provider in Profile to analyze project evidence.
          </p>
        </div>
        <div className="mt-3 border-t border-lab-line pt-3">
          <span className="text-[9px] uppercase tracking-[.09em] text-lab-dim">
            Workflow evidence
          </span>
          <dl className="mt-2 grid gap-2 text-[11px]">
            <div className="flex justify-between gap-3">
              <dt className="text-lab-muted">Active stage</dt>
              <dd className="font-data text-lab-ink">{steps[step].label}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-lab-muted">Local engines</dt>
              <dd className="font-data text-lab-ink">
                {ready} / {engines.length}
              </dd>
            </div>
            {execution && (
              <div className="flex justify-between gap-3">
                <dt className="text-lab-muted">Last job</dt>
                <dd className="font-data text-lab-green">saved</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
      <div className="border-t border-lab-line p-3">
        <div className="flex h-9 items-center gap-2 rounded-[3px] border border-lab-line bg-[#090b0d] px-2 text-[10px] text-lab-dim">
          <Icon name="spark" size={15} />
          <span>Provider not configured</span>
        </div>
      </div>
    </aside>
  );
}

function WindTunnel({
  projectId,
  snapshot,
  engines,
  onSnapshot,
}: {
  projectId: string;
  snapshot: WorkflowSnapshot | null;
  engines: EngineCapability[];
  onSnapshot: (value: WorkflowSnapshot) => void;
}) {
  const [step, setStep] = useState<TunnelStep>("import");
  const [values, setValues] = useState<Record<string, string>>(() =>
    defaultValues("import"),
  );
  const [advanced, setAdvanced] = useState(false);
  const [running, setRunning] = useState(false);
  const [detail, setDetail] = useState("");
  const [execution, setExecution] = useState<WorkflowExecution>();
  const [maverickOpen, setMaverickOpen] = useState(true);
  const definition = steps[step];
  const persistedFields = useMemo<Record<string, string>>(() => {
    const configuration = snapshot?.stages.find(
      (stage) => stage.id === definition.backend,
    )?.configuration;
    const fields = configuration?.fields;
    if (!fields || typeof fields !== "object" || Array.isArray(fields)) return {};
    return Object.fromEntries(
      Object.entries(fields).flatMap(([key, value]) =>
        typeof value === "string" || typeof value === "number"
          ? [[key, String(value)]]
          : [],
      ),
    );
  }, [definition.backend, snapshot]);
  const persistedFieldsKey = JSON.stringify(persistedFields);

  useEffect(() => {
    setValues({ ...defaultValues(step), ...persistedFields });
    setAdvanced(false);
    setDetail("");
    setExecution(undefined);
  }, [step, projectId, persistedFieldsKey]);
  const workflowStatus = stageState(snapshot, definition.backend);
  const stageOutput =
    execution?.output ?? snapshot?.latest_outputs?.[definition.backend];
  const preview =
    step === "results"
      ? (stageOutput?.results as Record<string, unknown> | undefined)
      : step === "mesh"
        ? (stageOutput?.mesh as Record<string, unknown> | undefined)
        : undefined;
  const previewArtifactId = artifactIdFrom(preview?.preview_artifact);
  const [previewSource, setPreviewSource] = useState<string>();
  const [artifactContent, setArtifactContent] =
    useState<WorkflowArtifactContent>();
  const [artifactNotice, setArtifactNotice] = useState("");
  const [artifactBusy, setArtifactBusy] = useState("");

  useEffect(() => {
    let cancelled = false;
    setPreviewSource(undefined);
    if (!previewArtifactId) return () => {
      cancelled = true;
    };
    void readWorkflowArtifact(previewArtifactId, projectId)
      .then((artifact) => {
        if (cancelled || artifact.encoding !== "base64") return;
        setPreviewSource(
          `data:${artifact.artifact.mime_type};base64,${artifact.content}`,
        );
      })
      .catch(() => {
        if (!cancelled) setPreviewSource(undefined);
      });
    return () => {
      cancelled = true;
    };
  }, [previewArtifactId, projectId]);

  useEffect(() => {
    setArtifactContent(undefined);
    setArtifactNotice("");
  }, [projectId, definition.backend]);

  const viewArtifact = async (artifact: WorkflowArtifact) => {
    setArtifactBusy(artifact.artifact_id);
    setArtifactNotice("");
    try {
      setArtifactContent(await readWorkflowArtifact(artifact.artifact_id, projectId));
    } catch (error) {
      setDetail(error instanceof Error ? error.message : String(error));
    } finally {
      setArtifactBusy("");
    }
  };

  const exportArtifact = async (artifact: WorkflowArtifact) => {
    setArtifactBusy(artifact.artifact_id);
    setArtifactNotice("");
    try {
      const destination = await save({ defaultPath: artifact.name });
      if (!destination) return;
      const exported = await exportWorkflowArtifact(
        artifact.artifact_id,
        destination,
        projectId,
      );
      setArtifactNotice(`${exported.name} exported from this project.`);
    } catch (error) {
      setDetail(error instanceof Error ? error.message : String(error));
    } finally {
      setArtifactBusy("");
    }
  };

  const chooseSource = async () => {
    try {
      const selected = await open({
        multiple: false,
        directory: false,
        filters: [
          {
            name: "CAD models",
            extensions: ["step", "stp", "iges", "igs", "brep"],
          },
        ],
      });
      if (typeof selected === "string")
        setValues((current) => ({ ...current, Source: selected }));
    } catch (error) {
      setDetail(error instanceof Error ? error.message : String(error));
    }
  };

  const execute = async (overrideBackend?: string) => {
    const backend = overrideBackend ?? definition.backend;
    setRunning(true);
    setDetail("");
    const fields = { ...values };
    if (step === "mesh") {
      const intent = fields["Mesh quality"];
      Object.assign(
        fields,
        intent === "Fast"
          ? {
              "Base size": "2.40",
              "Boundary layers": "6",
              "Growth rate": "1.22",
            }
          : intent === "Fine"
            ? {
                "Base size": "0.60",
                "Boundary layers": "18",
                "Growth rate": "1.12",
              }
            : {},
      );
    }
    if (step === "run")
      fields["Solver type"] =
        fields["Run type"] === "Transient flow"
          ? "Transient RANS"
          : "Steady RANS";
    try {
      const updated = await configureWorkflowStage(
        backend,
        { fields, source: "hx-cfd-desktop-wind-tunnel" },
        projectId,
      );
      onSnapshot(updated);
      const result = await executeWorkflowStage(backend, undefined, projectId);
      setExecution(result);
      const fresh = await getWorkflowSnapshot(projectId);
      onSnapshot(fresh);
    } catch (error) {
      setDetail(error instanceof Error ? error.message : String(error));
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="flex min-h-0 flex-1 bg-lab-canvas">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[58px] shrink-0 items-center justify-between border-b border-lab-line bg-[#060809] px-5">
          <div>
            <span className="text-[10px] uppercase tracking-[.1em] text-lab-dim">
              Wind tunnel
            </span>
            <h1 className="mt-0.5 text-[20px] font-medium tracking-[-.02em] text-lab-ink">
              {definition.title}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full border px-2 py-1 text-[9px] font-medium uppercase tracking-[.08em] ${statusStyle(workflowStatus)}`}
            >
              {workflowStatus === "attention"
                ? "Needs attention"
                : workflowStatus}
            </span>
            <button
              onClick={() => setMaverickOpen((value) => !value)}
              className="flex h-8 items-center gap-1.5 rounded-[3px] border border-lab-line bg-lab-surface px-2.5 text-[10px] text-lab-muted transition-colors duration-100 ease-instrument hover:border-lab-strongLine hover:bg-lab-hover hover:text-lab-ink"
            >
              <MaverickMark className="h-4 w-6" />
              Maverick
            </button>
          </div>
        </header>
        <nav className="flex h-12 shrink-0 items-stretch gap-1 overflow-x-auto border-b border-lab-line bg-[#080a0c] px-4">
          {orderedSteps.map((item, index) => {
            const itemDefinition = steps[item];
            const status = stageState(snapshot, itemDefinition.backend);
            return (
              <button
                key={item}
                onClick={() => setStep(item)}
                className={`group relative flex min-w-[98px] items-center gap-2 px-2.5 text-left transition-colors duration-100 ease-instrument ${step === item ? "bg-[#10151c] text-lab-ink" : "text-lab-muted hover:bg-lab-hover hover:text-lab-ink"}`}
              >
                <span
                  className={`grid h-5 w-5 place-items-center rounded-[3px] border text-[9px] font-data ${step === item ? "border-lab-blue bg-lab-blue text-white" : status === "complete" ? "border-lab-green/50 text-lab-green" : "border-lab-line text-lab-dim"}`}
                >
                  {status === "complete" ? (
                    <Icon name="check" size={12} />
                  ) : (
                    String(index + 1).padStart(2, "0")
                  )}
                </span>
                <span className="min-w-0">
                  <b className="block whitespace-nowrap text-[10px] font-medium">
                    {itemDefinition.label}
                  </b>
                  <small className="block text-[9px] text-lab-dim">
                    {status}
                  </small>
                </span>
                {step === item && (
                  <i className="absolute inset-x-0 bottom-0 h-px bg-lab-blue" />
                )}
              </button>
            );
          })}
        </nav>
        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_300px] gap-3 overflow-hidden p-3">
          <div className="grid min-h-0 grid-rows-[minmax(0,1fr)_176px] gap-3">
            <Panel
              title="Tunnel workspace"
              action={
                <div className="flex items-center gap-1 text-[9px] text-lab-dim">
                  <span className="h-1.5 w-1.5 rounded-full bg-lab-green" />
                  Local
                </div>
              }
              className="min-h-0"
            >
              <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_260px]">
                <div className="relative min-h-0 border-r border-lab-line bg-[#030405]">
                  {typeof previewSource === "string" ? (
                    <Viewport3D previewPath={previewSource} />
                  ) : (
                    <div className="flex h-full flex-col items-center justify-center px-8 text-center">
                      <div className="grid h-12 w-12 place-items-center rounded-[4px] border border-lab-line bg-lab-surface text-lab-muted">
                        <Icon name={definition.icon} size={22} />
                      </div>
                      <h2 className="mt-4 text-[13px] font-medium text-lab-ink">
                        {step === "import"
                          ? "No geometry loaded"
                          : step === "results"
                            ? "No result dataset published"
                            : "No tunnel evidence for this stage yet"}
                      </h2>
                      <p className="mt-2 max-w-[330px] text-[11px] leading-5 text-lab-muted">
                        {step === "import"
                          ? "Select a local CAD source to begin the engineering workflow."
                          : "Run the required upstream stage to publish real project evidence here."}
                      </p>
                    </div>
                  )}
                  <div className="absolute bottom-3 left-3 flex items-center gap-3 rounded-[3px] border border-lab-line bg-[#080a0c]/95 px-2 py-1.5 font-data text-[9px] text-lab-muted">
                    <span className="text-lab-green">Y</span>
                    <span className="text-lab-red">X</span>
                    <span className="text-[#5687e8]">Z</span>
                    <span>LOCAL EVIDENCE</span>
                  </div>
                </div>
                <div className="min-h-0 overflow-auto bg-lab-surface">
                  <div className="border-b border-lab-line p-3">
                    <span className="text-[9px] uppercase tracking-[.1em] text-lab-dim">
                      Stage configuration
                    </span>
                    <p className="mt-1 text-[11px] leading-5 text-lab-muted">
                      {definition.description}
                    </p>
                  </div>
                  <div className="grid gap-3 p-3">
                    {definition.fields.length ? (
                      definition.fields.map((field) => (
                        <div key={field.label} className="space-y-1">
                          {field.label === "Source" ? (
                            <label className="grid gap-1.5 text-[11px] text-lab-muted">
                              <span>CAD source</span>
                              <button
                                onClick={() => void chooseSource()}
                                className="flex h-8 w-full items-center justify-between rounded-[3px] border border-lab-line bg-lab-raised px-2 text-left text-[10px] text-lab-muted transition-colors hover:border-lab-strongLine hover:bg-lab-hover"
                              >
                                <span className="truncate">
                                  {values.Source || "Choose local CAD file"}
                                </span>
                                <Icon name="folder" size={14} />
                              </button>
                            </label>
                          ) : (
                            <FieldControl
                              field={field}
                              value={values[field.label] ?? ""}
                              onChange={(value) =>
                                setValues((current) => ({
                                  ...current,
                                  [field.label]: value,
                                }))
                              }
                            />
                          )}
                        </div>
                      ))
                    ) : (
                      <p className="text-[11px] leading-5 text-lab-muted">
                        No additional configuration is required for this
                        evidence view.
                      </p>
                    )}
                    <button
                      onClick={() => setAdvanced((value) => !value)}
                      className="flex items-center gap-1 text-[10px] text-lab-muted transition-colors hover:text-lab-ink"
                    >
                      <Icon name="chevron" size={13} />
                      {advanced ? "Hide" : "Show"} advanced controls
                    </button>
                    {advanced && (
                      <div className="grid gap-3 border-t border-lab-line pt-3">
                        {(definition.advanced ?? []).map((field) => (
                          <FieldControl
                            key={field.label}
                            field={field}
                            value={values[field.label] ?? ""}
                            onChange={(value) =>
                              setValues((current) => ({
                                ...current,
                                [field.label]: value,
                              }))
                            }
                          />
                        ))}
                      </div>
                    )}
                    <button
                      onClick={() => void execute()}
                      disabled={running}
                      className="flex h-9 items-center justify-center gap-2 rounded-[3px] border border-lab-blue bg-lab-blue px-3 text-[11px] font-medium text-white transition-colors duration-100 ease-instrument hover:bg-lab-blueHover disabled:opacity-50"
                    >
                      <Icon name={running ? "gear" : "play"} size={15} />
                      {running
                        ? "Executing local workflow…"
                        : definition.action}
                    </button>
                    {step === "improve" && (
                      <div className="grid gap-2">
                        <button
                          onClick={() => void execute("optimization")}
                          disabled={running}
                          className="flex h-8 items-center justify-center gap-2 rounded-[3px] border border-lab-line bg-lab-raised px-3 text-[10px] text-lab-muted transition-colors hover:border-lab-strongLine hover:bg-lab-hover hover:text-lab-ink disabled:opacity-50"
                        >
                          <Icon name="improve" size={14} />
                          Run optimization study
                        </button>
                        <button
                          onClick={() => void execute("surrogate")}
                          disabled={running}
                          className="flex h-8 items-center justify-center gap-2 rounded-[3px] border border-lab-line bg-lab-raised px-3 text-[10px] text-lab-muted transition-colors hover:border-lab-strongLine hover:bg-lab-hover hover:text-lab-ink disabled:opacity-50"
                        >
                          <Icon name="improve" size={14} />
                          Train local surrogate
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Panel>
            <div className="grid min-h-0 grid-cols-[1.1fr_.9fr] gap-3">
              <Panel title="Run evidence" className="min-h-0">
                <div className="p-3">
                  {detail ? (
                    <div className="rounded-[3px] border border-lab-red/40 bg-[#201111] p-3">
                      <div className="flex gap-2 text-lab-red">
                        <Icon name="warning" size={16} />
                        <span className="text-[11px] font-medium">
                          {shortError(detail)}
                        </span>
                      </div>
                      <details className="mt-2 text-[10px] text-lab-muted">
                        <summary className="cursor-pointer text-[#a8c4ff]">
                          Technical details
                        </summary>
                        <pre className="mt-2 max-h-20 overflow-auto whitespace-pre-wrap font-data text-[9px]">
                          {detail}
                        </pre>
                      </details>
                    </div>
                  ) : stageOutput ? (
                    <div className="rounded-[3px] border border-lab-green/30 bg-[#0c1710] p-3">
                      <div className="flex gap-2 text-lab-green">
                        <Icon name="check" size={16} />
                        <span className="text-[11px] font-medium">
                          {execution
                            ? "Published to the local project"
                            : "Latest local evidence restored"}
                        </span>
                      </div>
                      <p className="mt-2 text-[10px] leading-4 text-lab-muted">
                        {stageOutput.artifacts.length} real artifact
                        {stageOutput.artifacts.length === 1
                          ? ""
                          : "s"}{" "}
                        recorded for this stage.
                      </p>
                      {stageOutput.artifacts.length > 0 && (
                        <details className="mt-2 text-[10px] text-lab-muted">
                          <summary className="cursor-pointer text-[#a8c4ff]">
                            Inspect or export project evidence
                          </summary>
                          <div className="mt-2 grid gap-1.5">
                            {stageOutput.artifacts.map((artifact) => (
                              <div
                                key={artifact.artifact_id}
                                className="flex items-center gap-2 rounded-[3px] border border-lab-line bg-[#0a0c0e] px-2 py-1.5"
                              >
                                <span className="min-w-0 flex-1 truncate font-data text-[9px] text-lab-muted">
                                  {artifact.name}
                                </span>
                                {artifact.readable && (
                                  <button
                                    onClick={() => void viewArtifact(artifact)}
                                    disabled={artifactBusy === artifact.artifact_id}
                                    className="text-[9px] text-[#a8c4ff] hover:text-lab-ink disabled:opacity-50"
                                  >
                                    View
                                  </button>
                                )}
                                <button
                                  onClick={() => void exportArtifact(artifact)}
                                  disabled={artifactBusy === artifact.artifact_id}
                                  className="text-[9px] text-lab-muted hover:text-lab-ink disabled:opacity-50"
                                >
                                  Export
                                </button>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                      {artifactNotice && (
                        <p className="mt-2 text-[10px] text-lab-green">
                          {artifactNotice}
                        </p>
                      )}
                      {artifactContent && (
                        <details open className="mt-2 text-[10px] text-lab-muted">
                          <summary className="cursor-pointer text-[#a8c4ff]">
                            {artifactContent.artifact.name}
                          </summary>
                          <pre className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap font-data text-[9px]">
                            {artifactContent.encoding === "utf-8"
                              ? artifactContent.content
                              : "Binary preview loaded in the tunnel workspace."}
                          </pre>
                        </details>
                      )}
                    </div>
                  ) : (
                    <p className="text-[11px] leading-5 text-lab-muted">
                      This panel will show the exact local outcome, validation
                      evidence, or failure details for the selected action.
                    </p>
                  )}
                </div>
              </Panel>
              <Panel title="Project state" className="min-h-0">
                <dl className="grid gap-2 p-3 text-[10px]">
                  <div className="flex justify-between gap-3">
                    <dt className="text-lab-muted">Project</dt>
                    <dd className="max-w-[180px] truncate font-data text-lab-ink">
                      {projectId}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-lab-muted">Configured stages</dt>
                    <dd className="font-data text-lab-ink">
                      {snapshot?.stages.filter(
                        (item) => item.status === "configured",
                      ).length ?? 0}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-lab-muted">Recorded jobs</dt>
                    <dd className="font-data text-lab-ink">
                      {snapshot?.jobs.length ?? 0}
                    </dd>
                  </div>
                </dl>
              </Panel>
            </div>
          </div>
          <Maverick
            open={maverickOpen}
            onClose={() => setMaverickOpen(false)}
            step={step}
            execution={execution}
            engines={engines}
          />
        </div>
      </div>
    </section>
  );
}

function Projects({
  projectId,
  projects,
  onProjectOpen,
  onProjectsChanged,
}: {
  projectId: string;
  projects: LocalProject[];
  onProjectOpen: (projectId: string, snapshot: WorkflowSnapshot) => void;
  onProjectsChanged: () => Promise<void>;
}) {
  const [candidate, setCandidate] = useState("");
  const [query, setQuery] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState(projectId);
  const [renameValue, setRenameValue] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [busyAction, setBusyAction] = useState("");
  const [actionError, setActionError] = useState("");

  useEffect(() => {
    setSelectedProjectId(projectId);
    setRenaming(false);
  }, [projectId]);

  const normalize = (value: string) =>
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "");

  const selected =
    projects.find((project) => project.project_id === selectedProjectId) ??
    projects.find((project) => project.project_id === projectId);
  const visibleProjects = projects.filter(
    (project) =>
      !query || project.project_id.toLowerCase().includes(query.toLowerCase()),
  );
  const fail = (error: unknown) => {
    const detail = error instanceof Error ? error.message : String(error);
    setActionError(
      /reading ['"]invoke|__TAURI|tauri/i.test(detail)
        ? "This action is available only inside HX CFD desktop. Browser previews do not create or change local projects."
        : detail,
    );
  };

  const openProject = async (id: string) => {
    setBusyAction(`open:${id}`);
    setActionError("");
    try {
      const nextSnapshot = await openLocalProject(id);
      onProjectOpen(id, nextSnapshot);
      await onProjectsChanged();
    } catch (error) {
      fail(error);
    } finally {
      setBusyAction("");
    }
  };

  const createProject = async () => {
    const normalized = normalize(candidate);
    if (!normalized) return;
    setBusyAction("create");
    setActionError("");
    try {
      const created = await createLocalProject(normalized);
      setCandidate("");
      const nextSnapshot = await openLocalProject(created.project_id);
      onProjectOpen(created.project_id, nextSnapshot);
      await onProjectsChanged();
    } catch (error) {
      fail(error);
    } finally {
      setBusyAction("");
    }
  };

  const saveRename = async () => {
    if (!selected) return;
    const normalized = normalize(renameValue);
    if (!normalized || normalized === selected.project_id) {
      setRenaming(false);
      return;
    }
    setBusyAction(`rename:${selected.project_id}`);
    setActionError("");
    try {
      const renamed = await renameLocalProject(selected.project_id, normalized);
      setRenaming(false);
      setSelectedProjectId(renamed.project_id);
      await onProjectsChanged();
      if (selected.project_id === projectId) {
        const nextSnapshot = await openLocalProject(renamed.project_id);
        onProjectOpen(renamed.project_id, nextSnapshot);
      }
    } catch (error) {
      fail(error);
    } finally {
      setBusyAction("");
    }
  };

  const archiveProject = async () => {
    if (!selected) return;
    if (selected.project_id === projectId) {
      setActionError(
        "Open a different project before archiving the active one.",
      );
      return;
    }
    setBusyAction(`archive:${selected.project_id}`);
    setActionError("");
    try {
      await archiveLocalProject(selected.project_id);
      setSelectedProjectId(projectId);
      await onProjectsChanged();
    } catch (error) {
      fail(error);
    } finally {
      setBusyAction("");
    }
  };

  const removeProject = async () => {
    if (!selected) return;
    if (selected.project_id === projectId) {
      setActionError(
        "Open a different project before deleting the active one.",
      );
      return;
    }
    if (
      !window.confirm(
        `Permanently delete local project “${selected.project_id}” and all of its artifacts?`,
      )
    )
      return;
    setBusyAction(`delete:${selected.project_id}`);
    setActionError("");
    try {
      await deleteLocalProject(selected.project_id);
      setSelectedProjectId(projectId);
      await onProjectsChanged();
    } catch (error) {
      fail(error);
    } finally {
      setBusyAction("");
    }
  };

  return (
    <section className="min-h-0 flex-1 overflow-auto bg-lab-canvas p-5">
      <div className="mx-auto max-w-[1040px]">
        <div className="flex items-end justify-between">
          <div>
            <span className="text-[10px] uppercase tracking-[.1em] text-lab-dim">
              Local project storage
            </span>
            <h1 className="mt-1 text-[24px] font-medium tracking-[-.025em] text-lab-ink">
              Projects
            </h1>
            <p className="mt-2 text-[12px] text-lab-muted">
              Create or open the local engineering record that owns geometry,
              mesh, solver, and report artifacts.
            </p>
          </div>
        </div>
        <div className="mt-6 grid grid-cols-[minmax(0,1fr)_320px] gap-3">
          <Panel
            title="Local projects"
            action={
              <span className="font-data text-[10px] text-lab-dim">
                {projects.length} total
              </span>
            }
          >
            <div className="border-b border-lab-line p-3">
              <div className="flex h-8 items-center gap-2 rounded-[3px] border border-lab-line bg-lab-raised px-2">
                <Icon name="search" size={15} />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search local projects"
                  className="min-w-0 flex-1 bg-transparent text-[11px] text-lab-ink outline-none placeholder:text-lab-dim"
                />
              </div>
            </div>
            <div className="grid gap-2 p-3">
              {visibleProjects.length ? (
                visibleProjects.map((project) => {
                  const isActive = project.project_id === projectId;
                  const isSelected =
                    project.project_id === selected?.project_id;
                  return (
                    <button
                      key={project.project_id}
                      onClick={() => {
                        setSelectedProjectId(project.project_id);
                        setRenaming(false);
                        setActionError("");
                      }}
                      className={`flex w-full items-center gap-3 rounded-[3px] border p-3 text-left transition-colors ${isSelected ? "border-lab-blue/60 bg-[#101924]" : "border-lab-line bg-[#0a0c0e] hover:border-lab-strongLine hover:bg-lab-hover"}`}
                    >
                      <span
                        className={`grid h-9 w-9 place-items-center rounded-[3px] border ${isSelected ? "border-lab-blue/60 bg-[#12315f] text-[#b7d0ff]" : "border-lab-line bg-lab-raised text-lab-muted"}`}
                      >
                        <Icon name="folder" size={18} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <b className="block truncate text-[12px] font-medium text-lab-ink">
                          {project.project_id}
                        </b>
                        <small className="mt-1 block truncate font-data text-[9px] text-lab-dim">
                          Stored locally by HX CFD
                        </small>
                      </span>
                      {isActive && (
                        <span className="rounded-full border border-lab-green/30 px-2 py-1 text-[9px] text-lab-green">
                          Active
                        </span>
                      )}
                    </button>
                  );
                })
              ) : (
                <p className="py-8 text-center text-[11px] text-lab-muted">
                  No local project matches this search.
                </p>
              )}
            </div>
          </Panel>
          <Panel title="Project actions">
            <div className="grid gap-3 p-3">
              {selected ? (
                <>
                  <div className="rounded-[3px] border border-lab-line bg-[#0a0c0e] p-3">
                    <span className="text-[9px] uppercase tracking-[.09em] text-lab-dim">
                      Selected project
                    </span>
                    <b className="mt-1 block truncate text-[12px] font-medium text-lab-ink">
                      {selected.project_id}
                    </b>
                    <span className="mt-1 block truncate font-data text-[9px] text-lab-dim">
                      Stored locally by HX CFD
                    </span>
                  </div>
                  <button
                    onClick={() => void openProject(selected.project_id)}
                    disabled={busyAction.length > 0}
                    className="flex h-8 items-center justify-center gap-2 rounded-[3px] border border-lab-blue bg-lab-blue text-[10px] font-medium text-white transition-colors hover:bg-lab-blueHover disabled:opacity-50"
                  >
                    <Icon name="tunnel" size={14} />
                    {busyAction === `open:${selected.project_id}`
                      ? "Opening…"
                      : "Open in Wind Tunnel"}
                  </button>
                  {renaming ? (
                    <div className="grid gap-2 border-t border-lab-line pt-3">
                      <label className="grid gap-1.5 text-[11px] text-lab-muted">
                        New project name
                        <input
                          value={renameValue}
                          onChange={(event) =>
                            setRenameValue(event.target.value)
                          }
                          className="h-8 rounded-[3px] border border-lab-line bg-lab-raised px-2 text-[11px] text-lab-ink outline-none"
                        />
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => void saveRename()}
                          disabled={
                            busyAction.length > 0 || !normalize(renameValue)
                          }
                          className="h-8 rounded-[3px] border border-lab-line bg-lab-raised text-[10px] text-lab-ink hover:border-lab-strongLine disabled:opacity-50"
                        >
                          Save name
                        </button>
                        <button
                          onClick={() => setRenaming(false)}
                          disabled={busyAction.length > 0}
                          className="h-8 rounded-[3px] border border-lab-line text-[10px] text-lab-muted hover:bg-lab-hover disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setRenameValue(selected.project_id);
                        setRenaming(true);
                      }}
                      disabled={busyAction.length > 0}
                      className="flex h-8 items-center justify-center gap-2 rounded-[3px] border border-lab-line bg-lab-raised text-[10px] text-lab-muted hover:border-lab-strongLine hover:bg-lab-hover hover:text-lab-ink disabled:opacity-50"
                    >
                      <Icon name="gear" size={14} />
                      Rename project
                    </button>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => void archiveProject()}
                      disabled={
                        busyAction.length > 0 ||
                        selected.project_id === projectId
                      }
                      title={
                        selected.project_id === projectId
                          ? "Open another project before archiving this one."
                          : undefined
                      }
                      className="flex h-8 items-center justify-center gap-1.5 rounded-[3px] border border-lab-line text-[10px] text-lab-muted hover:border-lab-strongLine hover:bg-lab-hover disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Icon name="archive" size={14} />
                      Archive
                    </button>
                    <button
                      onClick={() => void removeProject()}
                      disabled={
                        busyAction.length > 0 ||
                        selected.project_id === projectId
                      }
                      title={
                        selected.project_id === projectId
                          ? "Open another project before deleting this one."
                          : undefined
                      }
                      className="flex h-8 items-center justify-center gap-1.5 rounded-[3px] border border-lab-red/40 text-[10px] text-[#e99891] hover:bg-[#211212] disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Icon name="trash" size={14} />
                      Delete
                    </button>
                  </div>
                </>
              ) : (
                <p className="text-[11px] leading-5 text-lab-muted">
                  Create a local project to start a durable engineering record.
                </p>
              )}
              <div className="border-t border-lab-line pt-3">
                <span className="text-[9px] uppercase tracking-[.09em] text-lab-dim">
                  New local project
                </span>
              </div>
              <label className="grid gap-1.5 text-[11px] text-lab-muted">
                Project name
                <input
                  value={candidate}
                  onChange={(event) => setCandidate(event.target.value)}
                  placeholder="e.g. rear-wing-aero-study"
                  className="h-8 rounded-[3px] border border-lab-line bg-lab-raised px-2 text-[11px] text-lab-ink outline-none placeholder:text-lab-dim"
                />
              </label>
              <button
                onClick={() => void createProject()}
                disabled={!normalize(candidate) || busyAction.length > 0}
                className="flex h-8 items-center justify-center gap-2 rounded-[3px] border border-lab-blue bg-lab-blue text-[10px] font-medium text-white transition-colors hover:bg-lab-blueHover disabled:opacity-50"
              >
                <Icon name="plus" size={14} />
                {busyAction === "create" ? "Creating…" : "Create and open"}
              </button>
              {actionError && (
                <div className="rounded-[3px] border border-lab-red/40 bg-[#201111] p-2 text-[10px] leading-4 text-[#e99891]">
                  {actionError}
                </div>
              )}
            </div>
          </Panel>
        </div>
      </div>
    </section>
  );
}

function Profile({
  engines,
  error,
}: {
  engines: EngineCapability[];
  error: string;
}) {
  const ready = engines.filter(
    (engine) => engine.status === "ready" || engine.status === "bundled",
  ).length;
  return (
    <section className="min-h-0 flex-1 overflow-auto bg-lab-canvas p-5">
      <div className="mx-auto max-w-[1040px]">
        <span className="text-[10px] uppercase tracking-[.1em] text-lab-dim">
          Desktop profile
        </span>
        <h1 className="mt-1 text-[24px] font-medium tracking-[-.025em] text-lab-ink">
          Profile and local environment
        </h1>
        <p className="mt-2 text-[12px] text-lab-muted">
          Control what runs on this workstation. Engineering engine names live
          here, not in the Wind Tunnel navigation.
        </p>
        <div className="mt-6 grid grid-cols-[300px_minmax(0,1fr)] gap-3">
          <Panel title="Workspace">
            <dl className="grid gap-3 p-3 text-[11px]">
              <div>
                <dt className="text-lab-muted">AI providers</dt>
                <dd className="mt-1 text-lab-ink">No provider configured</dd>
                <p className="mt-1 text-[10px] leading-4 text-lab-dim">
                  Maverick remains evidence-only until a provider is added.
                </p>
              </div>
              <div className="border-t border-lab-line pt-3">
                <dt className="text-lab-muted">Compute profile</dt>
                <dd className="mt-1 flex items-center gap-2 text-lab-ink">
                  <Icon name="cpu" size={15} />
                  Local workstation
                </dd>
              </div>
              <div className="border-t border-lab-line pt-3">
                <dt className="text-lab-muted">Desktop theme</dt>
                <dd className="mt-1 text-lab-ink">Titanium dark</dd>
              </div>
            </dl>
          </Panel>
          <Panel
            title="Installed engineering engines"
            action={
              <span className="font-data text-[10px] text-lab-muted">
                {ready} / {engines.length} ready
              </span>
            }
          >
            <div className="divide-y divide-lab-line">
              {error ? (
                <p className="p-3 text-[11px] text-lab-amber">{error}</p>
              ) : (
                engines.map((engine) => (
                  <div
                    key={engine.id}
                    className="flex items-center gap-3 px-3 py-2.5"
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${engine.status === "ready" || engine.status === "bundled" ? "bg-lab-green" : "bg-lab-amber"}`}
                    />
                    <div className="min-w-0 flex-1">
                      <b className="block text-[11px] font-medium text-lab-ink">
                        {engine.display_name}
                      </b>
                      <small className="block truncate text-[9px] text-lab-dim">
                        {engine.detail ?? engine.runtime}
                      </small>
                    </div>
                    <span
                      className={`rounded-full border px-2 py-1 text-[9px] ${engine.status === "ready" || engine.status === "bundled" ? "border-lab-green/30 text-lab-green" : "border-lab-amber/30 text-lab-amber"}`}
                    >
                      {engine.status === "unavailable"
                        ? "Needs setup"
                        : engine.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </Panel>
        </div>
      </div>
    </section>
  );
}

function Documentation() {
  const [selectedDocument, setSelectedDocument] = useState<string | null>(
    null,
  );
  const documents = [
    {
      title: "Getting started",
      description:
        "Import a CAD model, prepare geometry, generate a mesh, then run a local CFD case.",
      guidance:
        "Create or open a local project first. In Wind Tunnel, select a STEP, IGES, or BREP solid, then complete each stage in order. HX CFD records every accepted configuration and generated artifact in that project.",
    },
    {
      title: "Tunnel workflow",
      description:
        "How HX CFD creates revisioned geometry, mesh, physics, solver, result, and report evidence.",
      guidance:
        "Geometry must be prepared before meshing; meshing must be configured before physics; meshing and physics must both be configured before a solver run. Results and reports use only artifacts published by their preceding stage.",
    },
    {
      title: "Engineering concepts",
      description:
        "Mesh quality, boundary-layer decisions, convergence, and post-processing evidence.",
      guidance:
        "Use the mesh intent to set a sensible starting resolution, then inspect the published quality evidence before configuring physics. Solver and results stages only publish evidence that their local engines produced and validated.",
    },
    {
      title: "Desktop operations",
      description:
        "Keyboard shortcuts, local-project storage, diagnostics, and offline operation.",
      guidance:
        "HX CFD starts its managed local backend when the desktop app launches and keeps project data on the workstation. Use Ctrl + K to move between workspaces; Profile reports local engine availability and diagnostics.",
    },
    {
      title: "Open-source notices",
      description:
        "Third-party licenses, attributions, and engineering engine provenance.",
      guidance:
        "HX CFD orchestrates local engineering engines behind one workflow. Profile shows the locally detected engine inventory; an unavailable engine is never represented as a completed engineering action.",
    },
  ];
  return (
    <section className="min-h-0 flex-1 overflow-auto bg-lab-canvas p-5">
      <div className="mx-auto max-w-[900px]">
        <span className="text-[10px] uppercase tracking-[.1em] text-lab-dim">
          HX CFD documentation
        </span>
        <h1 className="mt-1 text-[24px] font-medium tracking-[-.025em] text-lab-ink">
          Use the tunnel with confidence
        </h1>
        <p className="mt-2 text-[12px] text-lab-muted">
          Short operational guidance for a local-first engineering workspace.
        </p>
        <div className="mt-6 divide-y divide-lab-line rounded-[4px] border border-lab-line bg-lab-surface">
          {documents.map(({ title, description, guidance }, index) => {
            const isSelected = selectedDocument === title;
            return (
              <div key={title}>
                <button
                  onClick={() =>
                    setSelectedDocument((current) =>
                      current === title ? null : title,
                    )
                  }
                  aria-expanded={isSelected}
                  className={`flex w-full items-center gap-4 px-4 py-4 text-left transition-colors hover:bg-lab-hover ${isSelected ? "bg-lab-hover" : ""}`}
                >
                  <span className="grid h-7 w-7 place-items-center rounded-[3px] border border-lab-line font-data text-[10px] text-lab-muted">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="min-w-0 flex-1">
                    <b className="block text-[12px] font-medium text-lab-ink">
                      {title}
                    </b>
                    <small className="mt-1 block text-[11px] leading-5 text-lab-muted">
                      {description}
                    </small>
                  </span>
                  <Icon name="chevron" size={15} />
                </button>
                {isSelected && (
                  <div className="border-t border-lab-line bg-[#0a0c0e] px-4 py-3 pl-[68px] text-[11px] leading-5 text-lab-muted">
                    {guidance}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [screen, setScreen] = useState<AppScreen>("wind-tunnel");
  const [projectId, setProjectId] = useState(activeProjectDefault);
  const [snapshot, setSnapshot] = useState<WorkflowSnapshot | null>(null);
  const [engines, setEngines] = useState<EngineCapability[]>([]);
  const [projects, setProjects] = useState<LocalProject[]>([]);
  const [bridgeNotice, setBridgeNotice] = useState("");
  const [backendReadiness, setBackendReadiness] =
    useState<BackendReadiness>("checking");
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");

  const refreshBackendHealth = async () => {
    if (!("__TAURI_INTERNALS__" in window)) {
      setBackendReadiness("offline");
      return;
    }

    try {
      const status = await getBackendStatus();
      const lifecycle =
        typeof status.status === "string" ? status.status : "offline";
      if (lifecycle === "stopped" || lifecycle === "offline") {
        setBackendReadiness("starting");
        await startBackend();
      } else {
        setBackendReadiness(lifecycle === "running" ? "checking" : "starting");
      }

      const healthy = await checkBackendHealth();
      setBackendReadiness(healthy ? "ready" : "starting");
    } catch {
      setBackendReadiness("offline");
    }
  };

  const refreshProjectList = async () => {
    const localProjects = await listLocalProjects();
    setProjects(localProjects);
  };

  const refresh = async (id = projectId) => {
    try {
      const [nextSnapshot, inventory, localProjects] = await Promise.all([
        getWorkflowSnapshot(id),
        getEngineInventory(),
        listLocalProjects(),
      ]);
      setSnapshot(nextSnapshot);
      setEngines(inventory);
      setProjects(localProjects);
      setBridgeNotice("");
    } catch (error) {
      setBridgeNotice(
        "The engineering bridge is available only inside HX CFD desktop. This browser preview never fabricates a local workflow.",
      );
    }
  };

  useEffect(() => {
    void refresh();
  }, [projectId]);
  useEffect(() => {
    void refreshBackendHealth();
    const interval = window.setInterval(
      () => void refreshBackendHealth(),
      5000,
    );
    return () => window.clearInterval(interval);
  }, []);
  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
      if (event.key === "Escape") setCommandOpen(false);
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);
  const activeLabel = useMemo(
    () => nav.find((item) => item.id === screen)?.label ?? "HX CFD",
    [screen],
  );
  const backendLabel =
    backendReadiness === "ready"
      ? "LOCAL READY"
      : backendReadiness === "starting" || backendReadiness === "checking"
        ? "LOCAL STARTING"
        : "LOCAL OFFLINE";
  const backendDot =
    backendReadiness === "ready"
      ? "bg-lab-green"
      : backendReadiness === "offline"
        ? "bg-lab-red"
        : "bg-lab-amber";
  const commandResults = nav.filter((item) =>
    item.label.toLowerCase().includes(commandQuery.trim().toLowerCase()),
  );
  const projectOpened = (id: string, nextSnapshot: WorkflowSnapshot) => {
    setProjectId(id);
    setSnapshot(nextSnapshot);
    setScreen("wind-tunnel");
  };

  return (
    <main className="relative flex h-[100dvh] min-h-0 min-w-[1024px] overflow-hidden bg-lab-black text-lab-ink">
      <aside className="flex w-[132px] shrink-0 flex-col border-r border-lab-line bg-lab-rail">
        <div className="flex h-[58px] items-center border-b border-lab-line px-4">
          <span className="text-[28px] font-semibold tracking-[-.11em] text-lab-ink">
            HX
          </span>
          <span className="ml-1 text-[11px] font-medium tracking-[-.04em] text-lab-ink">
            CFD
          </span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-2 py-3">
          {nav.map((item) => (
            <button
              key={item.id}
              onClick={() => setScreen(item.id)}
              className={`relative flex h-11 items-center gap-2 rounded-[3px] px-2 text-left text-[10px] transition-colors duration-100 ease-instrument ${screen === item.id ? "bg-[#141a22] text-lab-ink" : "text-lab-muted hover:bg-lab-hover hover:text-lab-ink"}`}
            >
              <Icon name={item.icon} size={18} />
              <span>{item.label}</span>
              {screen === item.id && (
                <i className="absolute inset-y-1 left-0 w-0.5 bg-lab-blue" />
              )}
            </button>
          ))}
        </nav>
        <div className="border-t border-lab-line p-3">
          <div className="flex items-center gap-2 text-[9px] text-lab-dim">
            <span className={`h-1.5 w-1.5 rounded-full ${backendDot}`} />
            {backendLabel.toLowerCase()}
          </div>
          <span className="mt-1 block font-data text-[9px] text-lab-dim">
            HX CFD v1.0.0
          </span>
        </div>
      </aside>
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[58px] shrink-0 items-center gap-4 border-b border-lab-line bg-[#050607] px-4">
          <div className="min-w-[180px]">
            <span className="block text-[9px] uppercase tracking-[.1em] text-lab-dim">
              Project
            </span>
            <span className="block truncate text-[11px] text-lab-ink">
              {projectId}
            </span>
          </div>
          <div className="h-7 w-px bg-lab-line" />
          <div className="min-w-[110px]">
            <span className="block text-[9px] uppercase tracking-[.1em] text-lab-dim">
              Workspace
            </span>
            <span className="block text-[11px] text-lab-ink">
              {activeLabel}
            </span>
          </div>
          <button
            onClick={() => setCommandOpen(true)}
            className="ml-2 flex h-8 min-w-[260px] max-w-[440px] flex-1 items-center gap-2 rounded-[3px] border border-[#171c21] bg-[#07090b] px-3 text-left text-[10px] text-lab-dim transition-colors hover:border-lab-line hover:bg-lab-surface"
          >
            <Icon name="search" size={15} />
            Search / Command Palette{" "}
            <span className="ml-auto font-data text-[9px]">Ctrl + K</span>
          </button>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden items-center gap-1.5 font-data text-[10px] text-lab-muted xl:flex">
              <i className={`h-1.5 w-1.5 rounded-full ${backendDot}`} />
              {backendLabel}
            </span>
            <button
              onClick={() => setScreen("profile")}
              className="grid h-7 w-7 place-items-center rounded-full border border-lab-strongLine bg-lab-raised text-[10px] text-lab-ink"
              aria-label="Open profile"
            >
              M
            </button>
          </div>
        </header>
        {bridgeNotice && (
          <div className="flex shrink-0 items-center gap-2 border-b border-lab-amber/30 bg-[#241b0c] px-4 py-2 text-[10px] text-[#f2c970]">
            <Icon name="warning" size={14} />
            {bridgeNotice}
          </div>
        )}
        {screen === "wind-tunnel" && (
          <WindTunnel
            projectId={projectId}
            snapshot={snapshot}
            engines={engines}
            onSnapshot={setSnapshot}
          />
        )}{" "}
        {screen === "projects" && (
          <Projects
            projectId={projectId}
            projects={projects}
            onProjectOpen={projectOpened}
            onProjectsChanged={refreshProjectList}
          />
        )}{" "}
        {screen === "profile" && (
          <Profile engines={engines} error={bridgeNotice} />
        )}{" "}
        {screen === "documentation" && <Documentation />}
      </section>
      {commandOpen && (
        <div className="absolute inset-0 z-40 grid place-items-start bg-black/70 pt-[86px]">
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            className="w-[480px] overflow-hidden rounded-[4px] border border-lab-strongLine bg-lab-surface shadow-floating"
          >
            <header className="flex items-center gap-2 border-b border-lab-line px-3 py-2.5">
              <Icon name="search" size={16} />
              <input
                autoFocus
                value={commandQuery}
                onChange={(event) => setCommandQuery(event.target.value)}
                placeholder="Go to a workspace"
                className="min-w-0 flex-1 bg-transparent text-[12px] text-lab-ink outline-none placeholder:text-lab-dim"
              />
              <button
                onClick={() => setCommandOpen(false)}
                className="grid h-6 w-6 place-items-center rounded-[3px] text-lab-muted hover:bg-lab-hover hover:text-lab-ink"
                aria-label="Close command palette"
              >
                <Icon name="close" size={15} />
              </button>
            </header>
            <div className="p-2">
              <span className="px-2 text-[9px] uppercase tracking-[.09em] text-lab-dim">
                Navigate
              </span>
              <div className="mt-1 grid gap-1">
                {commandResults.length ? (
                  commandResults.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        setScreen(item.id);
                        setCommandOpen(false);
                        setCommandQuery("");
                      }}
                      className="flex h-9 items-center gap-3 rounded-[3px] px-2 text-left text-[11px] text-lab-muted transition-colors hover:bg-lab-hover hover:text-lab-ink"
                    >
                      <Icon name={item.icon} size={16} />
                      <span className="flex-1">{item.label}</span>
                      {item.id === screen && (
                        <span className="font-data text-[9px] text-lab-blue">
                          CURRENT
                        </span>
                      )}
                    </button>
                  ))
                ) : (
                  <p className="px-2 py-5 text-center text-[11px] text-lab-muted">
                    No workspace matches that command.
                  </p>
                )}
              </div>
            </div>
            <footer className="flex justify-between border-t border-lab-line px-3 py-2 font-data text-[9px] text-lab-dim">
              <span>HX CFD desktop</span>
              <span>ESC to close</span>
            </footer>
          </section>
        </div>
      )}
    </main>
  );
}
