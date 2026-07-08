import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectService } from '../services/projectService'
import { meshService, Mesh } from '../services/meshService'
import { simulationService, Simulation } from '../services/simulationService'
import { pipelineService, PipelineConfig } from '../services/pipelineService'
import { useState } from 'react'

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'meshes' | 'simulations'>('meshes')
  const [showMeshModal, setShowMeshModal] = useState(false)
  const [showSimModal, setShowSimModal] = useState(false)
  const [meshConfig, setMeshConfig] = useState<PipelineConfig['mesh']>({
    element_size: 0.01,
    growth_rate: 1.2,
    num_boundary_layers: 3,
  })
  const [simConfig, setSimConfig] = useState<PipelineConfig['solver']>({
    end_time: 1.0,
    write_interval: 0.05,
    residual_print: true,
  })

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectService.get(projectId!),
    enabled: !!projectId,
  })

  const { data: meshes } = useQuery({
    queryKey: ['meshes', projectId],
    queryFn: () => meshService.list(projectId!),
    enabled: !!projectId && activeTab === 'meshes',
  })

  const { data: simulations } = useQuery({
    queryKey: ['simulations', projectId],
    queryFn: () => simulationService.list(projectId!),
    enabled: !!projectId && activeTab === 'simulations',
  })

  const createMeshMutation = useMutation({
    mutationFn: () => {
      const config: PipelineConfig = {
        project_id: projectId!,
        geometry_file: project?.geometry_file || '',
        mesh: meshConfig,
        solver: simConfig,
        visualization: { fields: ['velocity', 'pressure'] },
      }
      return pipelineService.start(config)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      setShowMeshModal(false)
      navigate('/pipeline')
    },
  })

  const createSimMutation = useMutation({
    mutationFn: () => {
      const config: PipelineConfig = {
        project_id: projectId!,
        geometry_file: project?.geometry_file || '',
        mesh: meshConfig,
        solver: simConfig,
        visualization: { fields: ['velocity', 'pressure'] },
      }
      return pipelineService.start(config)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      setShowSimModal(false)
      navigate('/pipeline')
    },
  })

  if (projectLoading) return <div>Loading...</div>
  if (!project) return <div>Project not found</div>

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/projects')} className="text-gray-500 hover:text-gray-700">
          ← Back
        </button>
        <h1 className="text-2xl font-bold">{project.name}</h1>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <p className="text-gray-600">{project.description || 'No description'}</p>
        <div className="mt-2 text-sm text-gray-500">
          Created: {new Date(project.created_at).toLocaleDateString()}
        </div>
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => navigate(`/upload?project=${projectId}`)}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 text-sm"
          >
            Upload Geometry
          </button>
          <button
            onClick={() => setShowMeshModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
          >
            Create Mesh
          </button>
          <button
            onClick={() => setShowSimModal(true)}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
          >
            Run Simulation
          </button>
        </div>
      </div>

      <div className="flex gap-4 mb-4">
        <button
          onClick={() => setActiveTab('meshes')}
          className={`px-4 py-2 rounded ${activeTab === 'meshes' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Meshes ({meshes?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('simulations')}
          className={`px-4 py-2 rounded ${activeTab === 'simulations' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Simulations ({simulations?.length || 0})
        </button>
      </div>

      {activeTab === 'meshes' && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b flex justify-between items-center">
            <h2 className="font-semibold">Meshes</h2>
          </div>
          <div className="divide-y">
            {meshes?.map((mesh) => (
              <div key={mesh.id} className="p-4 flex justify-between items-center">
                <div>
                  <div className="font-medium">{mesh.name}</div>
                  <div className="text-sm text-gray-500">
                    {mesh.num_cells || 0} cells, {mesh.num_points || 0} points
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs rounded ${
                  mesh.status === 'completed' ? 'bg-green-100 text-green-800' :
                  mesh.status === 'generating' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {mesh.status}
                </span>
              </div>
            ))}
            {(!meshes || meshes.length === 0) && (
              <div className="p-4 text-gray-500 text-center">No meshes yet</div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'simulations' && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b flex justify-between items-center">
            <h2 className="font-semibold">Simulations</h2>
          </div>
          <div className="divide-y">
            {simulations?.map((sim) => (
              <div
                key={sim.id}
                className="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50"
                onClick={() => navigate(`/simulations/${sim.id}`)}
              >
                <div>
                  <div className="font-medium">{sim.name}</div>
                  <div className="text-sm text-gray-500">{sim.solver}</div>
                </div>
                <span className={`px-2 py-1 text-xs rounded ${
                  sim.status === 'completed' ? 'bg-green-100 text-green-800' :
                  sim.status === 'running' ? 'bg-blue-100 text-blue-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {sim.status}
                </span>
              </div>
            ))}
            {(!simulations || simulations.length === 0) && (
              <div className="p-4 text-gray-500 text-center">No simulations yet</div>
            )}
          </div>
        </div>
      )}

      {/* Mesh Configuration Modal */}
      {showMeshModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-[500px]">
            <h2 className="text-xl font-bold mb-4">Create Mesh</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Element Size</label>
                <input
                  type="number"
                  value={meshConfig.element_size}
                  onChange={(e) => setMeshConfig({ ...meshConfig, element_size: parseFloat(e.target.value) })}
                  step="0.001"
                  min="0.001"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Growth Rate</label>
                <input
                  type="number"
                  value={meshConfig.growth_rate}
                  onChange={(e) => setMeshConfig({ ...meshConfig, growth_rate: parseFloat(e.target.value) })}
                  step="0.1"
                  min="1.0"
                  max="2.0"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Boundary Layers</label>
                <input
                  type="number"
                  value={meshConfig.num_boundary_layers}
                  onChange={(e) => setMeshConfig({ ...meshConfig, num_boundary_layers: parseInt(e.target.value) })}
                  min="0"
                  max="10"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowMeshModal(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
              >
                Cancel
              </button>
              <button
                onClick={() => createMeshMutation.mutate()}
                disabled={createMeshMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {createMeshMutation.isPending ? 'Creating...' : 'Create Mesh'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Simulation Configuration Modal */}
      {showSimModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-[500px]">
            <h2 className="text-xl font-bold mb-4">Run Simulation</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">End Time</label>
                <input
                  type="number"
                  value={simConfig.end_time}
                  onChange={(e) => setSimConfig({ ...simConfig, end_time: parseFloat(e.target.value) })}
                  step="0.1"
                  min="0.1"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Write Interval</label>
                <input
                  type="number"
                  value={simConfig.write_interval}
                  onChange={(e) => setSimConfig({ ...simConfig, write_interval: parseFloat(e.target.value) })}
                  step="0.01"
                  min="0.01"
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="residual_print"
                  checked={simConfig.residual_print}
                  onChange={(e) => setSimConfig({ ...simConfig, residual_print: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="residual_print" className="text-sm font-medium">Print Residuals</label>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowSimModal(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
              >
                Cancel
              </button>
              <button
                onClick={() => createSimMutation.mutate()}
                disabled={createSimMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              >
                {createSimMutation.isPending ? 'Starting...' : 'Run Simulation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}