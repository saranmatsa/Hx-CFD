import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { pipelineService } from '../services/pipelineService'

interface SimulationControlsProps {
  simulationId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  onStatusChange?: (status: string) => void
}

export default function SimulationControls({ simulationId, status, onStatusChange }: SimulationControlsProps) {
  const [showSettings, setShowSettings] = useState(false)
  const [settings, setSettings] = useState({
    endTime: 100,
    writeInterval: 10,
    residualPrint: true,
  })

  // Fetch current status
  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['pipeline-status', simulationId],
    queryFn: () => pipelineService.status(simulationId),
    refetchInterval: status === 'running' ? 2000 : false,
  })

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: () => pipelineService.cancel(simulationId),
    onSuccess: () => {
      onStatusChange?.('cancelled')
      refetchStatus()
    },
  })

  // Restart mutation
  const restartMutation = useMutation({
    mutationFn: () => pipelineService.restart(simulationId),
    onSuccess: () => {
      onStatusChange?.('running')
      refetchStatus()
    },
  })

  const currentStatus = statusData?.status || status
  const currentStage = statusData?.current_stage

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <h3 className="font-semibold">Simulation Controls</h3>
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
          currentStatus === 'running' ? 'bg-green-100 text-green-700' :
          currentStatus === 'completed' ? 'bg-blue-100 text-blue-700' :
          currentStatus === 'failed' ? 'bg-red-100 text-red-700' :
          'bg-gray-100 text-gray-700'
        }`}>
          {currentStatus.charAt(0).toUpperCase() + currentStatus.slice(1)}
        </span>
      </div>

      {/* Progress */}
      {currentStatus === 'running' && (
        <div className="px-4 py-3 border-b bg-gray-50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">
              {currentStage || 'Processing...'}
            </span>
            <span className="text-sm text-gray-500">
              {statusData?.progress || 0}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${statusData?.progress || 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="p-4 space-y-3">
        {currentStatus === 'running' && (
          <button
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400 flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
            {cancelMutation.isPending ? 'Cancelling...' : 'Cancel Simulation'}
          </button>
        )}

        {(currentStatus === 'completed' || currentStatus === 'failed') && (
          <button
            onClick={() => restartMutation.mutate()}
            disabled={restartMutation.isPending}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {restartMutation.isPending ? 'Restarting...' : 'Restart Simulation'}
          </button>
        )}

        <button
          onClick={() => setShowSettings(!showSettings)}
          className="w-full px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Advanced Settings
        </button>

        {/* Advanced Settings Panel */}
        {showSettings && (
          <div className="pt-3 border-t space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Time
              </label>
              <input
                type="number"
                value={settings.endTime}
                onChange={(e) => setSettings({ ...settings, endTime: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border rounded-md"
                disabled={currentStatus === 'running'}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Write Interval
              </label>
              <input
                type="number"
                value={settings.writeInterval}
                onChange={(e) => setSettings({ ...settings, writeInterval: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border rounded-md"
                disabled={currentStatus === 'running'}
              />
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.residualPrint}
                onChange={(e) => setSettings({ ...settings, residualPrint: e.target.checked })}
                className="rounded"
                disabled={currentStatus === 'running'}
              />
              <span className="text-sm">Print residuals to console</span>
            </label>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="px-4 py-3 bg-gray-50 border-t text-xs text-gray-500">
        <p>Simulation ID: {simulationId}</p>
        {statusData?.started_at && (
          <p>Started: {new Date(statusData.started_at).toLocaleString()}</p>
        )}
      </div>
    </div>
  )
}

// Compact version for sidebar
export function SimulationControlsCompact({ simulationId, status }: { simulationId: string; status: string }) {
  const { data: statusData } = useQuery({
    queryKey: ['pipeline-status', simulationId],
    queryFn: () => pipelineService.status(simulationId),
    refetchInterval: status === 'running' ? 2000 : false,
  })

  const cancelMutation = useMutation({
    mutationFn: () => pipelineService.cancel(simulationId),
  })

  const currentStatus = statusData?.status || status

  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${
        currentStatus === 'running' ? 'bg-green-500 animate-pulse' :
        currentStatus === 'completed' ? 'bg-blue-500' :
        currentStatus === 'failed' ? 'bg-red-500' :
        'bg-gray-400'
      }`} />
      <span className="text-sm text-gray-600 capitalize">{currentStatus}</span>
      {currentStatus === 'running' && (
        <button
          onClick={() => cancelMutation.mutate()}
          className="ml-2 text-red-600 hover:text-red-700"
          title="Cancel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  )
}