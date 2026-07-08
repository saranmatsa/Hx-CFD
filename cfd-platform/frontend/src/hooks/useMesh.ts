import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { meshService } from '../services/meshService'
import { MeshConfig } from '../types'

export function useMesh() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { projectId } = useParams<{ projectId: string }>()

  const [config, setConfig] = useState<MeshConfig>({
    element_size: 0.1,
    growth_rate: 0.3,
    num_boundary_layers: 3
  })

  const meshesQuery = useQuery({
    queryKey: ['meshes', projectId],
    queryFn: () => meshService.getMeshes(projectId!),
    enabled: !!projectId
  })

  const generateMeshMutation = useMutation({
    mutationFn: (data: { name: string; config?: MeshConfig }) =>
      meshService.generateMesh(projectId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meshes', projectId] })
    }
  })

  const deleteMeshMutation = useMutation({
    mutationFn: (meshId: string) => meshService.deleteMesh(meshId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meshes', projectId] })
    }
  })

  const importMeshMutation = useMutation({
    mutationFn: (file: File) => meshService.importMesh(projectId!, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meshes', projectId] })
    }
  })

  const exportMeshMutation = useMutation({
    mutationFn: ({ meshId, format }: { meshId: string; format: string }) =>
      meshService.exportMesh(meshId, format)
  })

  return {
    meshes: meshesQuery.data?.items || [],
    isLoading: meshesQuery.isLoading,
    error: meshesQuery.error,
    config,
    setConfig,
    generateMesh: generateMeshMutation.mutate,
    isGenerating: generateMeshMutation.isPending,
    deleteMesh: deleteMeshMutation.mutate,
    importMesh: importMeshMutation.mutate,
    exportMesh: exportMeshMutation.mutate,
    isExporting: exportMeshMutation.isPending
  }
}