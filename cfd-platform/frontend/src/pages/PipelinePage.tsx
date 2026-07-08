import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { pipelineService } from '../services/pipelineService'
import { SimulationControlsCompact } from '../components/SimulationControls'

export default function PipelinePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: pipelines, isLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => pipelineService.list(),
  })

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => pipelineService.cancel(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pipelines'] }),
  })

  const restartMutation = useMutation({
    mutationFn: (jobId: string) => pipelineService.restart(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pipelines'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => pipelineService.delete(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pipelines'] }),
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'cancelled':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStageName = (stageId: string) => {
    const stages: Record<string, string> = {
      geometry: 'Geometry Import',
      meshing: 'Mesh Generation',
      simulation: 'Simulation',
      visualization: 'Visualization',
    }
    return stages[stageId] || stageId
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading pipelines...</div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Pipeline Jobs</h1>
        <button
          onClick={() => navigate('/upload')}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          New Pipeline
        </button>
      </div>

      {(!pipelines || pipelines.length === 0) ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-gray-500 mb-4">No pipeline jobs yet</p>
          <button
            onClick={() => navigate('/upload')}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Start Your First Pipeline
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {pipelines.map((pipeline) => (
            <div key={pipeline.job_id} className="bg-white rounded-lg shadow">
              <div className="p-4 border-b flex justify-between items-center">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold">Pipeline {pipeline.job_id.slice(0, 8)}</h3>
                    <span className={`px-2 py-1 text-xs rounded ${getStatusColor(pipeline.status)}`}>
                      {pipeline.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    Project: {pipeline.project_id}
                  </div>
                </div>
                <div className="flex gap-2">
                  {pipeline.status === 'running' && (
                    <SimulationControlsCompact
                      simulationId={pipeline.job_id}
                      status={pipeline.status}
                    />
                  )}
                  {pipeline.status === 'running' && (
                    <button
                      onClick={() => cancelMutation.mutate(pipeline.job_id)}
                      className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  )}
                  {(pipeline.status === 'failed' || pipeline.status === 'cancelled') && (
                    <button
                      onClick={() => restartMutation.mutate(pipeline.job_id)}
                      className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
                    >
                      Restart
                    </button>
                  )}
                  <button
                    onClick={() => deleteMutation.mutate(pipeline.job_id)}
                    className="px-3 py-1 text-sm text-red-600 border border-red-300 rounded hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {/* Progress */}
              {pipeline.status === 'running' && pipeline.progress !== undefined && (
                <div className="px-4 py-3 bg-gray-50">
                  <div className="flex justify-between text-sm mb-1">
                    <span>Progress</span>
                    <span>{Math.round(pipeline.progress * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${pipeline.progress * 100}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Stages */}
              {pipeline.stages && pipeline.stages.length > 0 && (
                <div className="px-4 py-3">
                  <div className="text-sm font-medium mb-2">Stages</div>
                  <div className="flex gap-2 flex-wrap">
                    {pipeline.stages.map((stage, idx) => (
                      <div
                        key={idx}
                        className={`px-3 py-1 rounded text-sm ${
                          stage.status === 'completed' ? 'bg-green-100 text-green-800' :
                          stage.status === 'running' ? 'bg-blue-100 text-blue-800' :
                          stage.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {getStageName(stage.stage_id)}
                        {stage.status === 'running' && stage.progress !== undefined && (
                          <span className="ml-1">({Math.round(stage.progress * 100)}%)</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Error message */}
              {pipeline.status === 'failed' && pipeline.error && (
                <div className="px-4 py-3 bg-red-50 text-red-700 text-sm">
                  Error: {pipeline.error}
                </div>
              )}

              {/* Actions for completed pipelines */}
              {pipeline.status === 'completed' && (
                <div className="px-4 py-3 flex gap-2">
                  <button
                    onClick={() => navigate(`/results/${pipeline.job_id}`)}
                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    View Results
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}