import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useOptimization } from '../hooks/useOptimization'
import { OptimizationAlgorithm } from '../types'

const ALGORITHM_OPTIONS: Array<{ value: OptimizationAlgorithm; label: string; description: string }> = [
  { value: 'Nelder-Mead', label: 'Nelder-Mead', description: 'Gradient-free simplex method' },
  { value: 'COBYLA', label: 'COBYLA', description: 'Constrained optimization by linear approximation' },
  { value: 'Powell', label: 'Powell', description: 'Derivative-free method' },
  { value: 'DE', label: 'Differential Evolution', description: 'Evolutionary algorithm for global optimization' },
  { value: 'CMA-ES', label: 'CMA-ES', description: 'Covariance matrix adaptation evolution strategy' },
  { value: 'NSGA-II', label: 'NSGA-II', description: 'Multi-objective genetic algorithm' }
]

export default function OptimizationPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const {
    optimizations,
    isLoading,
    config,
    setConfig,
    createOptimization,
    isCreating,
    startOptimization,
    deleteOptimization
  } = useOptimization()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newOptName, setNewOptName] = useState('')
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<OptimizationAlgorithm>('CMA-ES')

  const handleCreateOptimization = () => {
    if (!newOptName.trim()) return
    createOptimization({ name: newOptName, algorithm: selectedAlgorithm })
    setNewOptName('')
    setShowCreateModal(false)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'running': return 'bg-yellow-100 text-yellow-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Design Optimization</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          New Optimization
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Optimization Parameters</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Iterations</label>
            <input
              type="number"
              value={config.num_iterations || ''}
              onChange={(e) => setConfig({ ...config, num_iterations: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              min="1"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Population Size</label>
            <input
              type="number"
              value={config.population_size || ''}
              onChange={(e) => setConfig({ ...config, population_size: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              min="2"
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Algorithm</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Progress</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Best Objective</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {optimizations.map((opt) => (
              <tr key={opt.id}>
                <td className="px-6 py-4 whitespace-nowrap font-medium">{opt.name}</td>
                <td className="px-6 py-4 whitespace-nowrap">{opt.algorithm}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(opt.status)}`}>
                    {opt.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {opt.progress !== undefined ? `${(opt.progress * 100).toFixed(1)}%` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {opt.best_objective !== undefined ? opt.best_objective.toFixed(6) : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {opt.status === 'pending' && (
                    <button
                      onClick={() => startOptimization(opt.id)}
                      className="text-green-600 hover:text-green-800 mr-3"
                    >
                      Start
                    </button>
                  )}
                  <button
                    onClick={() => deleteOptimization(opt.id)}
                    className="text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {optimizations.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No optimizations found. Create one to get started.
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold mb-4">Create Optimization</h2>
            <input
              type="text"
              placeholder="Optimization name"
              value={newOptName}
              onChange={(e) => setNewOptName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4"
            />
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Algorithm</label>
              <div className="grid grid-cols-2 gap-2">
                {ALGORITHM_OPTIONS.map((opt) => (
                  <label
                    key={opt.value}
                    className={`p-3 border rounded-lg cursor-pointer ${
                      selectedAlgorithm === opt.value ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="algorithm"
                      value={opt.value}
                      checked={selectedAlgorithm === opt.value}
                      onChange={() => setSelectedAlgorithm(opt.value)}
                      className="sr-only"
                    />
                    <div className="font-medium">{opt.label}</div>
                    <div className="text-xs text-gray-500">{opt.description}</div>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateOptimization}
                disabled={isCreating || !newOptName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isCreating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}