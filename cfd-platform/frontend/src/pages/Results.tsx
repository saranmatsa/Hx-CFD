import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Viewport3D } from '../components/viewport/Viewport3D'
import {
  ACTIVE_PROJECT_ID,
  configureWorkflowStage,
  executeWorkflowStage,
  getEngineInventory,
  getWorkflowSnapshot,
  type EngineCapability,
  type WorkflowExecution,
  type WorkflowSnapshot,
} from '../services/desktopWorkflow'
import './Results.css'

type IconName = 'home' | 'prepare' | 'mesh' | 'setup' | 'simulate' | 'analyze' | 'optimize' | 'export' | 'menu' | 'search' | 'bell' | 'settings' | 'chevron' | 'play' | 'layers' | 'check' | 'warning'

const paths: Record<IconName, ReactNode> = {
  home: <><path d="m3 11 9-8 9 8v10H3z"/><path d="M9 21v-6h6v6"/></>,
  prepare: <><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Zm0 0v9m8-4.5-8 4.5-8-4.5"/><path d="m16 3 2 2"/></>,
  mesh: <path d="M4 5h16M4 12h16M4 19h16M7 3l3 18M17 3l-3 18"/>,
  setup: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.05 2.05-.06-.06A1.7 1.7 0 0 0 15.8 18.6a1.7 1.7 0 0 0-1 1.55v.1h-2.9v-.1a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.05-2.05.06-.06A1.7 1.7 0 0 0 7.3 15a1.7 1.7 0 0 0-1.55-1H5.6v-2.9h.15a1.7 1.7 0 0 0 1.55-1 1.7 1.7 0 0 0-.34-1.88l-.06-.06L8.95 6.1l.06.06A1.7 1.7 0 0 0 10.9 6.5a1.7 1.7 0 0 0 1-1.55v-.1h2.9v.1a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.05 2.05-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.55 1h.1V14h-.1a1.7 1.7 0 0 0-1.54 1Z"/></>,
  simulate: <><path d="M5 5h5v5H5zM14 14h5v5h-5zM7.5 10v2a2 2 0 0 0 2 2H14"/><path d="m12 17 2 2 2-2"/></>,
  analyze: <><path d="M4 20V4M4 20h17"/><path d="m7 15 4-4 3 2 5-7"/></>,
  optimize: <><path d="M4 19 9 13l3 3 7-10"/><path d="M15 6h4v4"/></>,
  export: <><path d="M6 3h9l3 3v15H6zM14 3v4h4"/><path d="M12 10v7m-3-3 3 3 3-3"/></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16"/>, search: <><circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/></>, bell: <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>, settings: <><circle cx="12" cy="12" r="3"/><path d="M4 12h2m12 0h2M12 4v2m0 12v2M6.3 6.3l1.4 1.4m8.6 8.6 1.4 1.4m0-11.4-1.4 1.4m-8.6 8.6-1.4 1.4"/></>, chevron: <path d="m8 10 4 4 4-4"/>, play: <path d="m9 5 10 7-10 7z"/>, layers: <path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>, check: <path d="m5 12 4 4L19 6"/>, warning: <><path d="M12 3 2.8 20h18.4L12 3Z"/><path d="M12 9v4m0 3h.01"/></>,
}

const Icon = ({ name, size = 16 }: { name: IconName; size?: number }) => <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
const IconButton = ({ icon, label }: { icon: IconName; label: string }) => <button className="icon-button" aria-label={label} title={label}><Icon name={icon}/></button>

type StageId = 'prepare' | 'mesh' | 'setup' | 'simulate' | 'analyze' | 'optimize' | 'export'
type Status = 'Not Started' | 'In Progress' | 'Needs Attention' | 'Done'
type Field = { label: string; value: string; options?: string[]; unit?: string; placeholder?: string }
type StageDefinition = { backend: string; label: string; icon: IconName; title: string; description: string; action: string; essentials: Field[]; advanced: Field[]; next: string }

const stages: Record<StageId, StageDefinition> = {
  prepare: { backend: 'geometry', label: 'Prepare', icon: 'prepare', title: 'Get your geometry ready', description: 'Import a CAD file and HX CFD will check it, repair what it can, and save a clean simulation-ready copy.', action: 'Prepare geometry', essentials: [{ label: 'Source', value: '', placeholder: 'Choose or paste a local CAD file path' }], advanced: [{ label: 'Units', value: 'Millimeters', options: ['Millimeters', 'Meters', 'Inches'] }, { label: 'Defeature tolerance', value: '0.10', unit: 'mm' }], next: 'Next: create your mesh' },
  mesh: { backend: 'meshing', label: 'Mesh', icon: 'mesh', title: 'Create your mesh', description: 'Choose an outcome and HX CFD builds and checks a computational mesh automatically.', action: 'Generate mesh', essentials: [{ label: 'Mesh quality', value: 'Balanced', options: ['Fast', 'Balanced', 'Fine'] }], advanced: [{ label: 'Base size', value: '1.20', unit: 'mm' }, { label: 'Boundary layers', value: '12', options: ['0', '6', '12', '18'] }, { label: 'Growth rate', value: '1.18' }], next: 'Next: review flow surfaces' },
  setup: { backend: 'physics', label: 'Setup', icon: 'setup', title: 'Review the flow setup', description: 'Confirm the physical model and flow surfaces before you run. HX CFD keeps the technical controls out of the way until you need them.', action: 'Confirm setup', essentials: [{ label: 'Fluid', value: 'Air (ideal gas)', options: ['Air (ideal gas)', 'Water (liquid)'] }, { label: 'Energy equation', value: 'Enabled', options: ['Enabled', 'Disabled'] }], advanced: [{ label: 'Turbulence model', value: 'k-ω SST', options: ['k-ε Realizable', 'k-ω SST'] }, { label: 'Reference pressure', value: '101325', unit: 'Pa' }], next: 'Next: run the simulation' },
  simulate: { backend: 'solver', label: 'Simulate', icon: 'simulate', title: 'Run your simulation', description: 'Start the local run. Progress, results, and any problems are recorded in this project.', action: 'Run simulation', essentials: [{ label: 'Run type', value: 'Steady flow', options: ['Steady flow', 'Transient flow'] }], advanced: [{ label: 'Maximum iterations', value: '5000' }, { label: 'Residual target', value: '1e-05' }], next: 'Next: review your results' },
  analyze: { backend: 'results', label: 'Analyze', icon: 'analyze', title: 'Understand the results', description: 'Generate an automatic result view from the completed simulation. Use the workbench only when you need a closer look.', action: 'View auto results', essentials: [], advanced: [], next: 'Next: explore design options' },
  optimize: { backend: 'optimization', label: 'Optimize', icon: 'optimize', title: 'Explore better designs', description: 'Run a parameter sweep or goal-seeking study against your project’s real evaluation function.', action: 'Create parameter sweep', essentials: [{ label: 'Evaluator module', value: '', placeholder: 'Project evaluator file path' }, { label: 'Design variable', value: 'scale' }], advanced: [{ label: 'Lower bound', value: '0.8' }, { label: 'Upper bound', value: '1.2' }, { label: 'Budget', value: '20' }], next: 'Next: export your findings' },
  export: { backend: 'reports', label: 'Export', icon: 'export', title: 'Share your findings', description: 'Generate a report from the results currently published for this project.', action: 'Generate report', essentials: [{ label: 'Template', value: 'Engineering review', options: ['Engineering review', 'Performance summary'] }], advanced: [{ label: 'Format', value: 'HTML', options: ['HTML'] }], next: 'Project deliverable ready' },
}

const valuesFor = (definition: StageDefinition) => Object.fromEntries([...definition.essentials, ...definition.advanced].map(field => [field.label, field.value]))
const rawError = (error: unknown) => error instanceof Error ? error.message : String(error)
const friendlyError = (message: string) => {
  if (/unavailable|not available/i.test(message)) return 'A required local tool is not ready yet. Open Settings → Engines to finish its setup.'
  if (/configured|blocked|must be configured/i.test(message)) return 'This step needs information from an earlier stage. You can still return there and complete it at any time.'
  if (/source|cad file|geometry/i.test(message)) return 'We need a valid local CAD file before this step can continue. Check the file path and try again.'
  return 'This step could not finish. Review the details below, then adjust the affected stage and try again.'
}

function stageStatus(snapshot: WorkflowSnapshot | null, definition: StageDefinition): Status {
  const job = snapshot?.jobs.find(item => item.stage === definition.backend) as Record<string, unknown> | undefined
  if (job?.state === 'FAILED') return 'Needs Attention'
  if (job?.state === 'SUCCEEDED') return 'Done'
  if (snapshot?.stages.find(item => item.id === definition.backend)?.status === 'configured') return 'In Progress'
  return 'Not Started'
}

function Home({ openStage }: { openStage: (stage: StageId) => void }) {
  return <section className="home-screen"><div className="home-hero"><span className="eyebrow">HX CFD</span><h1>One place to prepare, simulate, and improve your design.</h1><p>Start with a project, then follow the highlighted next step — or open any stage whenever you need it.</p><div><button className="primary-action" onClick={() => openStage('prepare')}>Start new project</button><button className="quiet-action" onClick={() => openStage('prepare')}>Open a recent project</button></div></div><div className="home-library"><div className="library-heading"><div><span className="eyebrow">Your library</span><h2>Recent projects</h2></div><button className="quiet-action" onClick={() => openStage('prepare')}>Browse projects</button></div><button className="project-card" onClick={() => openStage('prepare')}><Icon name="home" size={22}/><span><b>{ACTIVE_PROJECT_ID.replace(/-/g, ' ')}</b><small>Open project workspace</small></span><Icon name="chevron"/></button><div className="sample-card"><Icon name="layers" size={22}/><span><b>Explore a sample project</b><small>A safe, read-only way to learn the workflow.</small></span></div></div></section>
}

type WorkbenchScreen = 'home' | 'settings' | StageId
type ModuleNavigation = { id: string; label: string; icon: IconName; screen?: WorkbenchScreen; dividerBefore?: boolean }

const moduleNavigation: ModuleNavigation[] = [
  { id: 'dashboard', label: 'Dashboard', icon: 'home', screen: 'home' },
  { id: 'geometry', label: 'Geometry', icon: 'prepare', screen: 'prepare' },
  { id: 'meshing', label: 'Meshing', icon: 'mesh', screen: 'mesh' },
  { id: 'physics', label: 'Physics', icon: 'setup', screen: 'setup' },
  { id: 'solver', label: 'Solver', icon: 'simulate', screen: 'simulate' },
  { id: 'results', label: 'Results', icon: 'analyze', screen: 'analyze' },
  { id: 'reports', label: 'Reports', icon: 'export', screen: 'export' },
  { id: 'copilot', label: 'AI Copilot', icon: 'optimize', screen: 'optimize', dividerBefore: true },
  { id: 'extensions', label: 'Extensions', icon: 'layers' },
  { id: 'settings', label: 'Settings', icon: 'settings', screen: 'settings', dividerBefore: true },
]

function StageRail({ current, navigate }: { current: WorkbenchScreen; navigate: (screen: WorkbenchScreen) => void }) {
  return <nav className="stage-rail" aria-label="HX CFD modules">{moduleNavigation.map(item => <div className={item.dividerBefore ? 'module-entry divided' : 'module-entry'} key={item.id}><button className={'stage-card ' + (current === item.screen ? 'active' : '')} disabled={!item.screen} title={item.screen ? item.label : 'Extensions are not configured for this local workspace.'} onClick={() => item.screen && navigate(item.screen)}><Icon name={item.icon}/><span className="stage-card-copy"><b>{item.label}</b></span></button></div>)}</nav>
}

function ArtifactPreview({ execution, module }: { execution?: WorkflowExecution; module: StageId }) {
  const mesh = execution?.output.mesh as Record<string, unknown> | undefined
  const results = execution?.output.results as Record<string, unknown> | undefined
  const preview = module === 'mesh' ? mesh?.preview : module === 'analyze' ? results?.preview : undefined
  return typeof preview === 'string' ? <div className="artifact-preview"><Viewport3D previewPath={preview}/></div> : null
}

function StageWorkspace({ stageId, snapshot, onSnapshot, onExecution }: { stageId: StageId; snapshot: WorkflowSnapshot | null; onSnapshot: (snapshot: WorkflowSnapshot) => void; onExecution: (execution: WorkflowExecution) => void }) {
  const stage = stages[stageId]
  const stored = snapshot?.stages.find(item => item.id === stage.backend)?.configuration.fields
  const [values, setValues] = useState<Record<string, string>>(() => valuesFor(stage))
  const [advanced, setAdvanced] = useState(false)
  const [state, setState] = useState<'idle' | 'running' | 'success' | 'error'>('idle')
  const [detail, setDetail] = useState('')
  const [execution, setExecution] = useState<WorkflowExecution>()

  useEffect(() => {
    const defaults = valuesFor(stage)
    const restored = stored && typeof stored === 'object' && !Array.isArray(stored)
      ? Object.fromEntries(Object.entries(stored).map(([key, value]) => [key, String(value)]))
      : {}
    setValues({ ...defaults, ...restored }); setAdvanced(false); setState('idle'); setDetail(''); setExecution(undefined)
  }, [stageId])

  const execute = async () => {
    setState('running'); setDetail('')
    const fields = { ...values }
    if (stageId === 'mesh') {
      const quality = values['Mesh quality']
      Object.assign(fields, quality === 'Fast' ? { 'Base size': '2.40', 'Boundary layers': '6', 'Growth rate': '1.22' } : quality === 'Fine' ? { 'Base size': '0.60', 'Boundary layers': '18', 'Growth rate': '1.12' } : { 'Base size': values['Base size'] || '1.20', 'Boundary layers': values['Boundary layers'] || '12', 'Growth rate': values['Growth rate'] || '1.18' })
    }
    if (stageId === 'simulate') fields['Solver type'] = values['Run type'] === 'Transient flow' ? 'Transient RANS' : 'Steady RANS'
    try {
      const updated = await configureWorkflowStage(stage.backend, { fields, source: 'hx-cfd-desktop' })
      onSnapshot(updated)
      const complete = await executeWorkflowStage(stage.backend)
      setExecution(complete); onExecution(complete); setState('success')
    } catch (error) { setDetail(rawError(error)); setState('error') }
  }

  const renderField = (field: Field) => <label className="workflow-field" key={field.label}><span>{field.label}</span>{field.options ? <select value={values[field.label] ?? ''} onChange={event => setValues(current => ({ ...current, [field.label]: event.target.value }))}>{field.options.map(option => <option key={option}>{option}</option>)}</select> : <div><input value={values[field.label] ?? ''} placeholder={field.placeholder} onChange={event => setValues(current => ({ ...current, [field.label]: event.target.value }))}/>{field.unit && <em>{field.unit}</em>}</div>}</label>
  const status = stageStatus(snapshot, stage)
  return <section className="cockpit-workspace"><div className="workspace-heading"><div><span className="eyebrow">{stage.label}</span><h1>{stage.title}</h1><p>{stage.description}</p></div><span className={'status-chip ' + status.toLowerCase().replace(/ /g, '-')}>{status}</span></div>{stageId === 'setup' && <div className="confirmation-banner">We’ll use your saved geometry and mesh to prepare the flow setup. Review the essentials, then confirm to continue.</div>}<div className="stage-layout"><main className="stage-main"><div className="panel action-panel"><div className="panel-header"><span>Essentials</span></div><div className="workflow-fields">{stage.essentials.length ? stage.essentials.map(renderField) : <div className="empty-state compact"><Icon name="analyze" size={24}/><p>Results will appear here once your simulation finishes.</p></div>}</div><button className="advanced-toggle" onClick={() => setAdvanced(value => !value)}>{advanced ? 'Hide advanced options' : 'Show advanced options'} <Icon name="chevron" size={13}/></button>{advanced && <div className="advanced-panel">{stage.advanced.length ? <><p>These controls are saved with this project. Leave them as-is for the recommended workflow.</p><div className="workflow-fields">{stage.advanced.map(renderField)}</div></> : <p>This stage already uses the full automatic workflow. More visual controls appear after a result is available.</p>}</div>}<div className="action-row"><button className="primary-action" disabled={state === 'running'} onClick={() => void execute()}><Icon name="play" size={14}/>{state === 'running' ? 'Working…' : stage.action}</button><span>{stage.next}</span></div></div><ArtifactPreview execution={execution} module={stageId}/></main><aside className="stage-aside"><div className="panel guidance-panel"><div className="panel-header"><span>{state === 'error' ? 'Needs attention' : state === 'success' ? 'Completed' : 'What happens next'}</span></div>{state === 'error' ? <div className="message-state error"><Icon name="warning" size={24}/><h2>{friendlyError(detail)}</h2><p>Nothing was invented or substituted. Adjust this stage, then try again.</p><details><summary>View technical details</summary><pre>{detail}</pre></details></div> : state === 'success' ? <div className="message-state success"><Icon name="check" size={24}/><h2>{stageId === 'mesh' ? 'Mesh quality: passed validation.' : 'Finished and saved to this project.'}</h2><p>{stageId === 'mesh' ? 'The mesh was generated and checked before being published to the project.' : 'Artifacts are ready for the next stage.'}</p>{execution && <details><summary>View execution details</summary><pre>{execution.output.artifacts.map(artifact => artifact.name).join('\n')}</pre></details>}</div> : <div className="message-state"><Icon name={stage.icon} size={24}/><h2>{stageId === 'mesh' ? 'Balanced is recommended.' : 'You can return to any stage at any time.'}</h2><p>{stageId === 'mesh' ? 'A balanced mesh is a good starting point for most design questions.' : 'HX CFD keeps the workflow flexible and saves every completed step locally.'}</p></div>}</div></aside></div></section>
}

function SettingsScreen({ returnHome, replayWalkthrough }: { returnHome: () => void; replayWalkthrough: () => void }) {
  const [tab, setTab] = useState<'preferences' | 'compute' | 'engines'>('preferences')
  const [engines, setEngines] = useState<EngineCapability[]>([])
  const [message, setMessage] = useState('')
  useEffect(() => {
    if (tab !== 'engines') return
    void getEngineInventory().then(setEngines).catch(() => setMessage('Engine information is available from the HX CFD desktop application.'))
  }, [tab])
  return <section className="settings-screen"><div className="workspace-heading"><div><span className="eyebrow">Settings</span><h1>Your HX CFD workspace</h1><p>Preferences and compute controls live here, outside the engineering workflow.</p></div><button className="quiet-action" onClick={returnHome}>Back to home</button></div><div className="settings-layout"><aside className="panel settings-tabs"><button className={tab === 'preferences' ? 'selected' : ''} onClick={() => setTab('preferences')}>Preferences</button><button className={tab === 'compute' ? 'selected' : ''} onClick={() => setTab('compute')}>Compute</button><button className={tab === 'engines' ? 'selected' : ''} onClick={() => setTab('engines')}>Engines</button></aside><main className="panel settings-content">{tab === 'preferences' && <><PanelLabel title="Preferences"/><p>Projects autosave locally. Use the project workspace to choose units for each engineering case.</p><div className="settings-actions"><button className="quiet-action" onClick={replayWalkthrough}>Replay workflow tour</button></div></>}{tab === 'compute' && <><PanelLabel title="Compute"/><p>HX CFD uses your local machine by default and continues working offline. Advanced compute policies appear only when a workload needs them.</p></>}{tab === 'engines' && <><PanelLabel title="Engines"/><p>These local implementation tools are managed by HX CFD and are intentionally not shown in the project workflow.</p>{message && <div className="settings-message">{message}</div>}<div className="engine-settings-list">{engines.map(engine => <div key={engine.id}><span>{engine.display_name}</span><b className={engine.status}>{engine.status === 'ready' || engine.status === 'bundled' ? 'Ready' : 'Needs setup'}</b></div>)}</div></>}</main></div></section>
}

const PanelLabel = ({ title }: { title: string }) => <div className="panel-header"><span>{title}</span></div>

type OnboardingStep = 0 | 1 | 2
type EngineeringFocus = 'Flow' | 'Heat' | 'Pressure'

function Onboarding({ step, setStep, complete }: { step: OnboardingStep; setStep: (step: OnboardingStep) => void; complete: (destination: 'home' | StageId) => void }) {
  const [focus, setFocus] = useState<EngineeringFocus>('Flow')
  const focusCopy: Record<EngineeringFocus, string> = {
    Flow: 'Trace how fluid moves through your design.',
    Heat: 'Understand how heat travels through your design.',
    Pressure: 'Find where pressure is gained or lost.',
  }
  const steps = ['Your goal', 'The workflow', 'Start a project']
  return <section className="onboarding-backdrop" role="dialog" aria-modal="true" aria-labelledby="onboarding-title"><div className="onboarding-card"><div className="onboarding-progress" aria-label={`Step ${step + 1} of 3`}>{steps.map((label, index) => <span className={index === step ? 'current' : index < step ? 'complete' : ''} key={label}><i>{index + 1}</i>{label}</span>)}</div>{step === 0 && <div className="onboarding-content"><span className="eyebrow">Welcome to HX CFD</span><h1 id="onboarding-title">What would you like to understand?</h1><p>Start with the engineering question. HX CFD will guide you through the workflow without asking you to choose a tool first.</p><div className="focus-options">{(Object.keys(focusCopy) as EngineeringFocus[]).map(option => <button key={option} className={focus === option ? 'selected' : ''} onClick={() => setFocus(option)}><Icon name={option === 'Flow' ? 'simulate' : option === 'Heat' ? 'analyze' : 'setup'} size={19}/><span><b>{option}</b><small>{focusCopy[option]}</small></span></button>)}</div><div className="onboarding-actions"><button className="primary-action" onClick={() => setStep(1)}>Continue</button></div></div>}{step === 1 && <div className="onboarding-content"><span className="eyebrow">One clear flow</span><h1 id="onboarding-title">HX CFD keeps the next step visible.</h1><p>Prepare your geometry, create a mesh, set up the physics, run, then review the result. You can move between stages whenever your work calls for it.</p><div className="onboarding-flow">{(['prepare', 'mesh', 'setup', 'simulate', 'analyze'] as StageId[]).map(stage => <div key={stage}><Icon name={stages[stage].icon}/><span>{stages[stage].label}</span></div>)}</div><div className="onboarding-actions"><button className="quiet-action" onClick={() => setStep(0)}>Back</button><button className="primary-action" onClick={() => setStep(2)}>Continue</button></div></div>}{step === 2 && <div className="onboarding-content"><span className="eyebrow">Ready when you are</span><h1 id="onboarding-title">Start with your geometry.</h1><p>Add a local CAD source and HX CFD will guide the rest of the engineering process. Advanced controls stay tucked away until you choose to use them.</p><div className="onboarding-summary"><Icon name="prepare" size={22}/><span><b>First step: prepare geometry</b><small>Your project stays local and autosaves as you work.</small></span></div><div className="onboarding-actions"><button className="quiet-action" onClick={() => complete('home')}>Explore home</button><button className="primary-action" onClick={() => complete('prepare')}>Start project</button></div></div>}</div></section>
}

export const Results = () => {
  // Results is the reference workbench on launch. The optional walkthrough is
  // still available in Settings, but it must never obscure the active local
  // project or replace the engineering console with a guided mock screen.
  const [screen, setScreen] = useState<'home' | 'settings' | StageId>('analyze')
  const [snapshot, setSnapshot] = useState<WorkflowSnapshot | null>(null)
  const [execution, setExecution] = useState<WorkflowExecution>()
  const [backendNotice, setBackendNotice] = useState('')
  const [onboardingStep, setOnboardingStep] = useState<OnboardingStep | null>(null)
  useEffect(() => { void getWorkflowSnapshot().then(setSnapshot).catch(() => setBackendNotice('Desktop services are available when HX CFD is launched as the desktop application.')) }, [])
  const title = screen === 'home' ? 'Home' : screen === 'settings' ? 'Settings' : stages[screen].label
  const openStage = (stage: StageId) => setScreen(stage)
  const completeOnboarding = (destination: 'home' | StageId) => {
    try { window.localStorage.setItem('hx-cfd-onboarding-complete', 'true') } catch { /* onboarding remains usable when storage is unavailable */ }
    setOnboardingStep(null); setScreen(destination)
  }
  const latestExecution = useMemo(() => execution, [execution])
  return <main className="hx-app ux-app"><aside className="nav-rail"><div className="hx-logo">HX <small>CFD</small></div><StageRail current={screen} navigate={setScreen}/><button className="collapse">‹ <span>Collapse</span></button></aside><div className="workspace ux-workspace"><header className="topbar"><IconButton icon="menu" label="Menu"/><div className="crumb"><small>Project</small>{ACTIVE_PROJECT_ID.replace(/-/g, ' ')} <Icon name="chevron" size={12}/></div><div className="crumb"><small>Module</small>{title}</div><button className="command"><Icon name="search" size={15}/> Search / Command Palette (Ctrl + K)</button><IconButton icon="bell" label="Notifications"/><button className="icon-button" aria-label="Settings" title="Settings" onClick={() => setScreen('settings')}><Icon name="settings"/></button><div className="avatar">M</div></header>{backendNotice && <div className="desktop-notice">{backendNotice}</div>}{screen === 'home' ? <Home openStage={openStage}/> : screen === 'settings' ? <SettingsScreen returnHome={() => setScreen('home')} replayWalkthrough={() => { setOnboardingStep(0); setScreen('home') }}/> : <StageWorkspace stageId={screen} snapshot={snapshot} onSnapshot={setSnapshot} onExecution={setExecution}/>}<footer className="statusbar"><span>HX CFD <i>v1.0.0</i></span><span className="ready">● Local workspace</span>{latestExecution && <span>Latest task saved</span>}<span className="directory">Managed project · {ACTIVE_PROJECT_ID}</span></footer>{onboardingStep !== null && <Onboarding step={onboardingStep} setStep={setOnboardingStep} complete={completeOnboarding}/>}</div></main>
}
