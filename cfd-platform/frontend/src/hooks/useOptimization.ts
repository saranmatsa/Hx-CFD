import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { optimizationService } from '../services/optimizationService'
import { OptimizationConfig, OptimizationAlgorithm } from '../types'

export function useOptimization() {
  const queryClient = useQueryClient()
  const { projectId } = useParams<{ projectId: string }>()

  const [config, setConfig] = useState<OptimizationConfig>({
    num_iterations: 100,
    population_size: 20
  })

  const optimizationsQuery = useQuery({
    queryKey: ['optimizations', projectId],
    queryFn: () => optimizationService.getOptimizations(projectId!),
    enabled: !!projectId
  })

  const createOptimizationMutation = useMutation({
    mutationFn: (data: { name: string; algorithm: OptimizationAlgorithm; simulation_id?: string }) =>
      optimizationService.createOptimization(projectId!, { ...data, config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimizations', projectId] })
    }
  })

  const startOptimizationMutation = useMutation({
    mutationFn: (optimizationId: string) => optimizationService.startOptimization(optimizationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimizations', projectId] })
    }
  })

  const deleteOptimizationMutation = useMutation({
    mutationFn: (optimizationId: string) => optimizationService.deleteOptimization(optimizationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimizations', projectId] })
    }
  })

  return {
    optimizations: optimizationsQuery.data?.items || [],
    isLoading: optimizationsQuery.isLoading,
    error: optimizationsQuery.error,
    config,
    setConfig,
    createOptimization: createOptimizationMutation.mutate,
    isCreating: createOptimizationMutation.isPending,
    startOptimization: startOptimizationMutation.mutate,
    deleteOptimization: deleteOptimizationMutation.mutate
  }
}