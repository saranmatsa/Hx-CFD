import { useQuery } from '@tanstack/react-query'
import { visualizationService } from '../services/visualizationService'

export function useVisualization(simulationId?: string) {
  const meshDataQuery = useQuery({
    queryKey: ['visualization', 'mesh', simulationId],
    queryFn: () => visualizationService.getMeshData(simulationId!),
    enabled: !!simulationId
  })

  const getScalarField = (fieldName: string, timeStep?: number) =>
    useQuery({
      queryKey: ['visualization', 'scalar', simulationId, fieldName, timeStep],
      queryFn: () => visualizationService.getScalarField(simulationId!, fieldName, timeStep),
      enabled: !!simulationId
    })

  const getVectorField = (fieldName: string, timeStep?: number) =>
    useQuery({
      queryKey: ['visualization', 'vector', simulationId, fieldName, timeStep],
      queryFn: () => visualizationService.getVectorField(simulationId!, fieldName, timeStep),
      enabled: !!simulationId
    })

  const residualsQuery = useQuery({
    queryKey: ['visualization', 'residuals', simulationId],
    queryFn: () => visualizationService.getResiduals(simulationId!),
    enabled: !!simulationId
  })

  const forcesQuery = useQuery({
    queryKey: ['visualization', 'forces', simulationId],
    queryFn: () => visualizationService.getForces(simulationId!),
    enabled: !!simulationId
  })

  return {
    meshData: meshDataQuery.data,
    isLoadingMesh: meshDataQuery.isLoading,
    getScalarField,
    getVectorField,
    residuals: residualsQuery.data,
    isLoadingResiduals: residualsQuery.isLoading,
    forces: forcesQuery.data,
    isLoadingForces: forcesQuery.isLoading
  }
}