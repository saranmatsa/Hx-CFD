import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { simulationService } from '../services/simulationService'
import { SolverConfig, SolverType } from '../types'

export function useSimulation() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { projectId } = useParams<{ projectId: string }>()

  const [config, setConfig] = useState<SolverConfig>({
    start_time: 0,
    end_time: 100,
    delta_t: 0.1,
    write_interval: 1,
    residual_control: true,
    residual_tolerance: 0.001,
    max_iterations: 1000
  })

  const simulationsQuery = useQuery({
    queryKey: ['simulations', projectId],
    queryFn: () => simulationService.getSimulations(projectId!),
    enabled: !!projectId
  })

  const createSimulationMutation = useMutation({
    mutationFn: (data: { name: string; solver: SolverType; mesh_id?: string }) =>
      simulationService.createSimulation(projectId!, { ...data, config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulations', projectId] })
    }
  })

  const startSimulationMutation = useMutation({
    mutationFn: (simulationId: string) => simulationService.startSimulation(simulationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulations', projectId] })
    }
  })

  const stopSimulationMutation = useMutation({
    mutationFn: (simulationId: string) => simulationService.stopSimulation(simulationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulations', projectId] })
    }
  })

  const deleteSimulationMutation = useMutation({
    mutationFn: (simulationId: string) => simulationService.deleteSimulation(simulationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulations', projectId] })
    }
  })

  return {
    simulations: simulationsQuery.data?.items || [],
    isLoading: simulationsQuery.isLoading,
    error: simulationsQuery.error,
    config,
    setConfig,
    createSimulation: createSimulationMutation.mutate,
    isCreating: createSimulationMutation.isPending,
    startSimulation: startSimulationMutation.mutate,
    stopSimulation: stopSimulationMutation.mutate,
    deleteSimulation: deleteSimulationMutation.mutate
  }
}