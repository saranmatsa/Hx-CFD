import { VisualizationType } from '../types'

export function getVisualizationTypeLabel(type: VisualizationType): string {
  const labels: Record<VisualizationType, string> = {
    contour: 'Contour Plot',
    vector: 'Vector Plot',
    streamline: 'Streamlines',
    'iso-surface': 'Iso-Surface',
    slice: 'Slice View'
  }
  return labels[type] || type
}

export function getVisualizationTypeIcon(type: VisualizationType): string {
  const icons: Record<VisualizationType, string> = {
    contour: '📊',
    vector: '➡️',
    streamline: '🌊',
    'iso-surface': '🎯',
    slice: '📐'
  }
  return icons[type] || '📈'
}

export function formatFieldData(data: { min_value?: number; max_value?: number }): string {
  if (data.min_value === undefined || data.max_value === undefined) {
    return 'No data range available'
  }
  return `Range: [${data.min_value.toFixed(4)}, ${data.max_value.toFixed(4)}]`
}

export function getColormapOptions(): Array<{ value: string; label: string }> {
  return [
    { value: 'viridis', label: 'Viridis' },
    { value: 'plasma', label: 'Plasma' },
    { value: 'inferno', label: 'Inferno' },
    { value: 'coolwarm', label: 'Cool-Warm' },
    { value: 'rainbow', label: 'Rainbow' },
    { value: 'grayscale', label: 'Grayscale' }
  ]
}

export function getDefaultFieldOptions(): Array<{ value: string; label: string }> {
  return [
    { value: 'p', label: 'Pressure (p)' },
    { value: 'U', label: 'Velocity (U)' },
    { value: 'T', label: 'Temperature (T)' },
    { value: 'k', label: 'Turbulent Kinetic Energy (k)' },
    { value: 'epsilon', label: 'Turbulent Dissipation (ε)' }
  ]
}