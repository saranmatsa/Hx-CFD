import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMesh } from '../hooks/useMesh'
import { MeshConfig } from '../types'

export default function MeshPage() {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const {
    meshes,
    isLoading,
    config,
    setConfig,
    generateMesh,
    isGenerating,
    deleteMesh,
    importMesh
  } = useMesh()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newMeshName, setNewMeshName] = useState('')

  const handleCreateMesh = () => {
    if (!newMeshName.trim()) return
    generateMesh({ name: newMeshName, config })
    setNewMeshName('')
    setShowCreateModal(false)
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      importMesh(file)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Mesh Generation</h1>
        <div className="flex gap-3">
          <label className="px-4 py-2 bg-green-600 text-white rounded-lg cursor-pointer hover:bg-green-700">
            Import Mesh
            <input type="file" className="hidden" accept=".stl,.obj,.msh" onChange={handleFileUpload} />
          </label>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Generate Mesh
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Mesh Parameters</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Element Size</label>
            <input
              type="number"
              value={config.element_size || ''}
              onChange={(e) => setConfig({ ...config, element_size: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              step="0.01"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Growth Rate</label>
            <input
              type="number"
              value={config.growth_rate || ''}
              onChange={(e) => setConfig({ ...config, growth_rate: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              step="0.05"
              min="0"
              max="1"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Boundary Layers</label>
            <input
              type="number"
              value={config.num_boundary_layers || ''}
              onChange={(e) => setConfig({ ...config, num_boundary_layers: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              min="0"
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cells</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {meshes.map((mesh) => (
              <tr key={mesh.id}>
                <td className="px-6 py-4 whitespace-nowrap">{mesh.name}</td>
                <td className="px-6 py-4 whitespace-nowrap capitalize">{mesh.mesh_type}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    mesh.status === 'completed' ? 'bg-green-100 text-green-800' :
                    mesh.status === 'generating' ? 'bg-yellow-100 text-yellow-800' :
                    mesh.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {mesh.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">{mesh.num_cells?.toLocaleString() || '-'}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <button
                    onClick={() => navigate(`/projects/${projectId}/mesh/${mesh.id}`)}
                    className="text-blue-600 hover:text-blue-800 mr-3"
                  >
                    View
                  </button>
                  <button
                    onClick={() => deleteMesh(mesh.id)}
                    className="text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {meshes.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No meshes found. Generate or import a mesh to get started.
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Generate New Mesh</h2>
            <input
              type="text"
              placeholder="Mesh name"
              value={newMeshName}
              onChange={(e) => setNewMeshName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateMesh}
                disabled={isGenerating || !newMeshName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isGenerating ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}