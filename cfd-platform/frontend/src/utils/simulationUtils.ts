import { SimulationStatus, SolverType } from '../types'

export function getSolverLabel(solver: SolverType): string {
  const labels: Record<SolverType, string> = {
    simpleFoam: 'SimpleFOAM (Steady-state)',
    icoFoam: 'icoFoam (Transient)',
    pisoFoam: 'pisoFoam (PISO algorithm)',
    pimpleFoam: 'pimpleFoam (PIMPLE algorithm)',
    buoyantSimpleFoam: 'BuoyantSimpleFoam (Buoyancy)',
    chtMultiRegionSimpleFoam: 'CHT Multi-Region'
  }
  return labels[solver] || solver
}

export function getSimulationStatusLabel(status: SimulationStatus): string {
  const labels: Record<SimulationStatus, string> = {
    draft: 'Draft',
    queued: 'Queued',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    cancelled: 'Cancelled'
  }
  return labels[status] || status
}

export function getSimulationStatusColor(status: SimulationStatus): string {
  const colors: Record<SimulationStatus, string> = {
    draft: 'text-gray-500',
    queued: 'text-blue-500',
    running: 'text-yellow-500',
    completed: 'text-green-500',
    failed: 'text-red-500',
    cancelled: 'text-gray-400'
  }
  return colors[status] || 'text-gray-500'
}

export function formatProgress(progress?: number): string {
  if (progress === undefined) return 'N/A'
  return `${(progress * 100).toFixed(1)}%`
}

export function formatTime(time?: number): string {
  if (time === undefined) return 'N/A'
  return time.toFixed(4)
}

export function formatIterations(iterations?: number): string {
  if (iterations === undefined) return 'N/A'
  return iterations.toLocaleString()
}