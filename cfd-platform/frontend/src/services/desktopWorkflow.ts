import { invoke } from '@tauri-apps/api/core'

export type EngineStatus = 'ready' | 'unavailable' | 'bundled'

export type EngineCapability = {
  id: string
  display_name: string
  workflow: string[]
  runtime: string
  optional: boolean
  adapter: string
  status: EngineStatus
  version?: string
  executable?: string
  detail?: string
}

export type WorkflowStageState = {
  id: string
  label: string
  status: 'blocked' | 'required' | 'configured'
  blocked_by: string[]
  configuration: Record<string, unknown>
  updated_at?: string
}

export type WorkflowOutput = {
  engines: string[]
  artifacts: WorkflowArtifact[]
  log_artifact_id: string | null
  [key: string]: unknown
}

/** A project-owned file addressed without disclosing its local source path. */
export type WorkflowArtifact = {
  artifact_id: string
  name: string
  label: string
  stage_id: string
  job_id: string | null
  kind: 'artifact' | 'log' | 'report'
  mime_type: string
  size_bytes: number
  created_at: string
  readable: boolean
  previewable: boolean
}

export type WorkflowArtifactContent = {
  artifact: WorkflowArtifact
  encoding: 'utf-8' | 'base64'
  content: string
}

export type WorkflowArtifactExport = {
  artifact_id: string
  name: string
  size_bytes: number
  exported: true
}

export type WorkflowSnapshot = {
  project_id: string
  stages: WorkflowStageState[]
  jobs: Array<Record<string, unknown>>
  latest_outputs: Record<string, WorkflowOutput>
  engines: EngineCapability[]
}

export type LocalProject = {
  id: string
  project_id: string
  created_at?: string
  updated_at: string
  archived: boolean
  warning?: string
}

export type DeletedLocalProject = {
  id: string
  project_id: string
  archived: boolean
  deleted: true
}

export const ACTIVE_PROJECT_ID = 'aero-turbine-study'

export type WorkflowExecution = {
  job: Record<string, unknown>
  output: WorkflowOutput
}

export type BackendLifecycleState =
  | 'stopped'
  | 'starting'
  | 'running'
  | 'stopping'
  | { error: string }

export type BackendStatus = {
  status: BackendLifecycleState
  uptime_seconds?: number | null
  pid?: number | null
}

/** Read the state of HX CFD's managed local backend process. */
export async function getBackendStatus(): Promise<BackendStatus> {
  return invoke<BackendStatus>('get_backend_status')
}

/** Start the managed backend only when its lifecycle reports it is stopped. */
export async function startBackend(): Promise<void> {
  return invoke<void>('start_backend')
}

/** Check the private loopback health endpoint owned by the Tauri shell. */
export async function checkBackendHealth(): Promise<boolean> {
  return invoke<boolean>('check_backend_health')
}

export async function getEngineInventory(): Promise<EngineCapability[]> {
  return invoke<EngineCapability[]>('get_engine_inventory')
}

/** Read active projects from the Tauri-owned local project store. */
export async function listLocalProjects(): Promise<LocalProject[]> {
  return invoke<LocalProject[]>('list_local_projects')
}

/** Create an initialized local project rather than a client-side placeholder. */
export async function createLocalProject(projectId: string): Promise<LocalProject> {
  return invoke<LocalProject>('create_local_project', { projectId })
}

/** Open an existing local project and return its durable workflow snapshot. */
export async function openLocalProject(projectId: string): Promise<WorkflowSnapshot> {
  return invoke<WorkflowSnapshot>('open_local_project', { projectId })
}

/** Rename a local project folder and its manifest through the backend bridge. */
export async function renameLocalProject(
  projectId: string,
  newProjectId: string,
): Promise<LocalProject> {
  return invoke<LocalProject>('rename_local_project', { projectId, newProjectId })
}

/** Archive a project while retaining all local engineering artifacts. */
export async function archiveLocalProject(projectId: string): Promise<LocalProject> {
  return invoke<LocalProject>('archive_local_project', { projectId })
}

/** Permanently delete a validated project directory from local project storage. */
export async function deleteLocalProject(projectId: string): Promise<DeletedLocalProject> {
  return invoke<DeletedLocalProject>('delete_local_project', { projectId })
}

export async function getWorkflowSnapshot(projectId = ACTIVE_PROJECT_ID): Promise<WorkflowSnapshot> {
  return invoke<WorkflowSnapshot>('get_workflow_snapshot', { projectId })
}

/** List only opaque descriptors for project evidence, reports, and local logs. */
export async function listWorkflowArtifacts(
  projectId = ACTIVE_PROJECT_ID,
  stageId?: string,
): Promise<WorkflowArtifact[]> {
  return invoke<WorkflowArtifact[]>('list_workflow_artifacts', { projectId, stageId })
}

/** Read bounded content from a project-owned artifact by its opaque ID. */
export async function readWorkflowArtifact(
  artifactId: string,
  projectId = ACTIVE_PROJECT_ID,
): Promise<WorkflowArtifactContent> {
  return invoke<WorkflowArtifactContent>('read_workflow_artifact', { projectId, artifactId })
}

/** Export one project artifact after a native save dialog supplies a destination. */
export async function exportWorkflowArtifact(
  artifactId: string,
  destination: string,
  projectId = ACTIVE_PROJECT_ID,
): Promise<WorkflowArtifactExport> {
  return invoke<WorkflowArtifactExport>('export_workflow_artifact', {
    projectId,
    artifactId,
    destination,
  })
}

export async function configureWorkflowStage(
  stageId: string,
  configuration: Record<string, unknown>,
  projectId = ACTIVE_PROJECT_ID,
): Promise<WorkflowSnapshot> {
  return invoke<WorkflowSnapshot>('configure_workflow_stage', {
    projectId,
    stageId,
    configuration,
  })
}

export async function executeWorkflowStage(
  stageId: string,
  recipe?: Record<string, unknown>,
  projectId = ACTIVE_PROJECT_ID,
): Promise<WorkflowExecution> {
  return invoke<WorkflowExecution>('execute_workflow_stage', {
    projectId,
    stageId,
    recipe,
  })
}
