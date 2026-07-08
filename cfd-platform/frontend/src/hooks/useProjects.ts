import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectService } from '../services/projectService'

export function useProjects() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)

  const projectsQuery = useQuery({
    queryKey: ['projects', page, pageSize],
    queryFn: () => projectService.getProjects(page, pageSize)
  })

  const createProjectMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      projectService.createProject(data),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      navigate(`/projects/${project.id}`)
    }
  })

  const updateProjectMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; description?: string } }) =>
      projectService.updateProject(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    }
  })

  const deleteProjectMutation = useMutation({
    mutationFn: (id: string) => projectService.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      navigate('/dashboard')
    }
  })

  return {
    projects: projectsQuery.data?.items || [],
    total: projectsQuery.data?.total || 0,
    totalPages: projectsQuery.data?.total_pages || 0,
    isLoading: projectsQuery.isLoading,
    error: projectsQuery.error,
    page,
    setPage,
    createProject: createProjectMutation.mutate,
    isCreating: createProjectMutation.isPending,
    updateProject: updateProjectMutation.mutate,
    deleteProject: deleteProjectMutation.mutate
  }
}