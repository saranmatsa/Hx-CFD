import { useState } from 'react'
import { useOptimization } from '../hooks/useOptimization'

interface OptimizationPanelProps {
  optimizationId?: string
  className?: string
}

export default function OptimizationPanel({ optimizationId, className = '' }: OptimizationPanelProps) {
  const { optimizations, startOptimization, deleteOptimization } = useOptimization()
  const optimization = optimizations.find(o => o.id === optimizationId)

  const [selectedIteration, setSelectedIteration] = useState(0)

  if (!optimization) {
    return (
      <div className={`bg-gray-100 rounded-lg p-4 ${className}`}>
        <p className="text-gray-500">Select an optimization to view details</p>
      </div>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-500'
      case 'running': return 'text-yellow-500'
      case 'failed': return 'text-red-500'
      default: return 'text-gray-500'
    }
  }

  return (
    <div className={`bg-white rounded-lg shadow p-4 ${className}`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-semibold text-lg">{optimization.name}</h3>
          <p className="text-sm text-gray-500">{optimization.algorithm}</p>
        </div>
        <span className={`px-2 py-1 rounded text-sm ${getStatusColor(optimization.status)}`}>
          {optimization.status}
        </span>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Progress</label>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${(optimization.progress || 0) * 100}%` }}
            />
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {optimization.progress ? `${(optimization.progress * 100).toFixed(1)}%` : '0%'}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Best Objective</label>
            <p className="text-lg font-mono">
              {optimization.best_objective?.toFixed(6) || 'N/A'}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Iteration</label>
            <p className="text-lg">{selectedIteration}</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Iteration Slider</label>
          <input
            type="range"
            min="0"
            max={100}
            value={selectedIteration}
            onChange={(e) => setSelectedIteration(parseInt(e.target.value))}
            className="w-full"
          />
        </div>

        <div className="flex gap-2">
          {optimization.status === 'pending' && (
            <button
              onClick={() => startOptimization(optimization.id)}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Start
            </button>
          )}
          <button
            onClick={() => deleteOptimization(optimization.id)}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}