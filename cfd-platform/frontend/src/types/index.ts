export interface User {
  id: string
  email: string
  username: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  name: string
  description?: string
  status: 'active' | 'archived' | 'completed'
  owner_id: string
  created_at: string
  updated_at: string
}

export interface Mesh {
  id: string
  name: string
  project_id: string
  mesh_type: 'unstructured' | 'structured' | 'hybrid'
  status: 'pending' | 'generating' | 'completed' | 'failed'
  num_cells?: number
  num_points?: number
  num_boundaries?: number
  bounding_box?: BoundingBox
  file_path?: string
  created_at: string
  updated_at: string
}

export interface BoundingBox {
  min: [number, number, number]
  max: [number, number, number]
}

export interface Simulation {
  id: string
  name: string
  project_id: string
  mesh_id?: string
  solver: SolverType
  status: SimulationStatus
  progress?: number
  current_time?: number
  num_iterations?: number
  results_path?: string
  created_at: string
  updated_at: string
}

export type SolverType = 'simpleFoam' | 'icoFoam' | 'pisoFoam' | 'pimpleFoam' | 'buoyantSimpleFoam' | 'chtMultiRegionSimpleFoam'
export type SimulationStatus = 'draft' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface Visualization {
  id: string
  name: string
  project_id: string
  simulation_id?: string
  visualization_type: VisualizationType
  created_at: string
  updated_at: string
}

export type VisualizationType = 'contour' | 'vector' | 'streamline' | 'iso-surface' | 'slice'

export interface Optimization {
  id: string
  name: string
  project_id: string
  simulation_id?: string
  algorithm: OptimizationAlgorithm
  status: OptimizationStatus
  progress?: number
  best_objective?: number
  results_path?: string
  created_at: string
  updated_at: string
}

export type OptimizationAlgorithm = 'Nelder-Mead' | 'COBYLA' | 'Powell' | 'DE' | 'CMA-ES' | 'NSGA-II'
export type OptimizationStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface MeshConfig {
  element_size?: number
  growth_rate?: number
  num_boundary_layers?: number
  min_cells_x?: number
  min_cells_y?: number
  min_cells_z?: number
}

export interface SolverConfig {
  start_time?: number
  end_time?: number
  delta_t?: number
  write_interval?: number
  residual_control?: boolean
  residual_tolerance?: number
  max_iterations?: number
}

export interface OptimizationConfig {
  num_iterations?: number
  population_size?: number
  objective_function?: string
  constraints?: Record<string, number>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiError {
  detail: string
  code?: string
  errors?: Array<{
    loc: string[]
    msg: string
    type: string
  }>
}