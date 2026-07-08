import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { pipelineService } from '../services/pipelineService'
import Viewer3D from '../components/Viewer3D'

interface ChartData {
  time: number
  value: number
}

export default function ResultsPage() {
  const { projectId, simulationId } = useParams<{ projectId: string; simulationId: string }>()
  const navigate = useNavigate()
  const [selectedField, setSelectedField] = useState('p')
  const [activeTab, setActiveTab] = useState<'visualization' | 'residuals' | 'statistics'>('visualization')

  // Fetch simulation results
  const { data: result, isLoading } = useQuery({
    queryKey: ['pipeline-result', simulationId],
    queryFn: () => pipelineService.result(simulationId!),
    enabled: !!simulationId,
    refetchInterval: 5000,
  })

  // Fetch visualization data
  const { data: vizData } = useQuery({
    queryKey: ['pipeline-viz', simulationId, selectedField],
    queryFn: () => pipelineService.visualization(simulationId!, selectedField),
    enabled: !!simulationId,
  })

  // Mock residual data for demonstration
  const residualData: ChartData[] = [
    { time: 0, value: 1.0 },
    { time: 100, value: 0.5 },
    { time: 200, value: 0.2 },
    { time: 300, value: 0.1 },
    { time: 400, value: 0.05 },
    { time: 500, value: 0.02 },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <svg className="animate-spin h-8 w-8 mx-auto mb-4 text-blue-600" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-gray-600">Loading results...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(`/projects/${projectId}`)}
          className="text-gray-500 hover:text-gray-700 flex items-center gap-2 mb-4"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Project
        </button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Simulation Results</h1>
            <p className="text-gray-600">Simulation ID: {simulationId}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => window.print()}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Status Banner */}
      {result?.status === 'completed' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 flex items-center gap-3">
          <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="font-medium text-green-800">Simulation Completed Successfully</p>
            <p className="text-sm text-green-600">
              Completed at: {result.completed_at ? new Date(result.completed_at).toLocaleString() : 'N/A'}
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-6">
          {(['visualization', 'residuals', 'statistics'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'visualization' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 3D Viewer */}
          <div className="lg:col-span-3">
            <Viewer3D
              vtkData={vizData}
              showControls={true}
              onFieldSelect={setSelectedField}
              className="h-[600px]"
            />
          </div>

          {/* Field Selection Sidebar */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-4">Visualization Fields</h3>
            <div className="space-y-2">
              {['p', 'U', 'T', 'k', 'epsilon'].map((field) => (
                <button
                  key={field}
                  onClick={() => setSelectedField(field)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selectedField === field
                      ? 'bg-blue-100 text-blue-700'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <span className="font-medium">{field}</span>
                  <span className="ml-2 text-xs text-gray-500">
                    {field === 'p' ? 'Pressure' : field === 'U' ? 'Velocity' : field === 'T' ? 'Temperature' : 'Turbulence'}
                  </span>
                </button>
              ))}
            </div>

            <div className="mt-6 pt-4 border-t">
              <h4 className="font-medium text-sm mb-2">Display Options</h4>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" className="rounded" defaultChecked />
                Show Mesh
              </label>
              <label className="flex items-center gap-2 text-sm mt-2">
                <input type="checkbox" className="rounded" defaultChecked />
                Show Legend
              </label>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'residuals' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Residual Plot */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold mb-4">Convergence History</h3>
            <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg">
              <div className="text-center text-gray-500">
                <svg className="w-12 h-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                </svg>
                <p>Residual Plot</p>
                <p className="text-sm">Iteration vs Residual Value</p>
              </div>
            </div>
          </div>

          {/* Residual Values */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold mb-4">Current Residuals</h3>
            <div className="space-y-3">
              {[
                { name: 'p', value: 1.2e-5, label: 'Pressure' },
                { name: 'U', value: 8.5e-6, label: 'Velocity' },
                { name: 'k', value: 2.1e-5, label: 'Turbulent Kinetic Energy' },
                { name: 'epsilon', value: 3.4e-5, label: 'Dissipation Rate' },
              ].map((residual) => (
                <div key={residual.name} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <span className="font-medium">{residual.name}</span>
                    <span className="text-gray-500 text-sm ml-2">({residual.label})</span>
                  </div>
                  <span className="font-mono text-sm">{residual.value.toExponential(2)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'statistics' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Summary Cards */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold mb-4">Simulation Summary</h3>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-500">Total Cells</p>
                <p className="text-2xl font-bold">{result?.mesh?.num_cells?.toLocaleString() || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Points</p>
                <p className="text-2xl font-bold">{result?.mesh?.num_points?.toLocaleString() || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Solver</p>
                <p className="text-lg">{result?.config?.solver || 'N/A'}</p>
              </div>
            </div>
          </div>

          {/* Field Statistics */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold mb-4">Pressure Statistics</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-500">Min</span>
                <span className="font-mono">-245.32 Pa</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Max</span>
                <span className="font-mono">123.45 Pa</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Mean</span>
                <span className="font-mono">0.00 Pa</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Std Dev</span>
                <span className="font-mono">45.23 Pa</span>
              </div>
            </div>
          </div>

          {/* Velocity Statistics */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold mb-4">Velocity Statistics</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-500">Min</span>
                <span className="font-mono">0.00 m/s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Max</span>
                <span className="font-mono">15.67 m/s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Mean</span>
                <span className="font-mono">5.23 m/s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Std Dev</span>
                <span className="font-mono">2.45 m/s</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}