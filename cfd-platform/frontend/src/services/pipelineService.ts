import { api } from './api'

export interface PipelineJob {
  id: string
  project_id: string
  status: PipelineStatus
  current_stage: PipelineStage | null
  progress: number
  input_file?: string
  output_mesh?: string
  output_visualization?: string
  error_message?: string
  created_at: string
  updated_at: string
}

export type PipelineStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type PipelineStage = 
  | 'cad_import'
  | 'geometry_repair'
  | 'mesh_generation'
  | 'case_setup'
  | 'simulation'
  | 'post_processing'
  | 'visualization'

export interface PipelineConfig {
  element_size?: number
  growth_rate?: number
  num_boundary_layers?: number
  solver?: string
  start_time?: number
  end_time?: number
  visualization_fields?: string[]
}

export interface PipelineResult {
  mesh_stats?: {
    num_cells: number
    num_points: number
    num_boundaries: number
  }
  simulation_results?: {
    final_time: number
    num_iterations: number
    residuals: Record<string, number[]>
  }
  visualization_data?: {
    fields: string[]
    time_steps: number[]
  }
}

export const pipelineService = {
  start: (projectId: string, file: File, config?: PipelineConfig) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('project_id', projectId)
    if (config) {
      formData.append('config', JSON.stringify(config))
    }
    
    return fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/pipeline/start`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: formData,
    }).then(res => {
      if (!res.ok) throw new Error('Failed to start pipeline')
      return res.json()
    })
  },

  status: (jobId: string) =>
    api.get<PipelineJob>(`/pipeline/status/${jobId}`),

  result: (jobId: string) =>
    api.get<PipelineResult>(`/pipeline/result/${jobId}`),

  visualization: (jobId: string) =>
    api.get<{ url: string }>(`/pipeline/visualization/${jobId}`),

  mesh: (jobId: string) =>
    api.get<{ url: string }>(`/pipeline/mesh/${jobId}`),

  cancel: (jobId: string) =>
    api.post(`/pipeline/cancel/${jobId}`),

  delete: (jobId: string) =>
    api.delete(`/pipeline/${jobId}`),

  list: () =>
    api.get<{ jobs: PipelineJob[] }>('/pipeline/jobs'),

  stages: () =>
    api.get<{ stages: { id: PipelineStage; name: string; description: string }[] }>('/pipeline/stages'),
}

export const PIPELINE_STAGES: Record<PipelineStage, { name: string; description: string }> = {
  cad_import: { name: 'CAD Import', description: 'Importing STEP/IGES file' },
  geometry_repair: { name: 'Geometry Repair', description: 'Fixing CAD geometry' },
  mesh_generation: { name: 'Mesh Generation', description: 'Creating computational mesh' },
  case_setup: { name: 'Case Setup', description: 'Configuring OpenFOAM case' },
  simulation: { name: 'Simulation', description: 'Running CFD solver' },
  post_processing: { name: 'Post Processing', description: 'Processing results' },
  visualization: { name: 'Visualization', description: 'Generating visualizations' },
}