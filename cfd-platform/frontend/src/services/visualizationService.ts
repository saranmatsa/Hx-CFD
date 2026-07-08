import { api } from './api'

export interface MeshData {
  points: number[][]
  connectivity: number[]
  bounding_box: { min: number[]; max: number[] }
}

export interface ScalarFieldData {
  field_name: string
  points: number[][]
  values: number[]
  min_value: number
  max_value: number
  time_step: number
}

export interface VectorFieldData {
  field_name: string
  points: number[][]
  vectors: number[][]
  scale: number
  time_step: number
}

export const visualizationService = {
  getMesh: (simulationId: string) =>
    api.get<MeshData>(`/visualization/mesh/${simulationId}`),
  
  getScalarField: (simulationId: string, fieldName: string, timeStep?: number) =>
    api.get<ScalarFieldData>(`/visualization/scalar/${simulationId}`, {
      params: { field_name: fieldName, time_step: timeStep },
    }),
  
  getVectorField: (simulationId: string, fieldName: string, timeStep?: number) =>
    api.get<VectorFieldData>(`/visualization/vector/${simulationId}`, {
      params: { field_name: fieldName, time_step: timeStep },
    }),
  
  getResiduals: (simulationId: string) =>
    api.get<{ residuals: Record<string, number>[] }>(`/visualization/residuals/${simulationId}`),
  
  getForces: (simulationId: string) =>
    api.get<{ forces: Record<string, number>[] }>(`/visualization/forces/${simulationId}`),
}