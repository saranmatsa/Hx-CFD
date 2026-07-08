import { BoundingBox } from '../types'

export function formatBoundingBox(box: BoundingBox): string {
  const [minX, minY, minZ] = box.min
  const [maxX, maxY, maxZ] = box.max
  return `X: [${minX.toFixed(3)}, ${maxX.toFixed(3)}], Y: [${minY.toFixed(3)}, ${maxY.toFixed(3)}], Z: [${minZ.toFixed(3)}, ${maxZ.toFixed(3)}]`
}

export function getBoundingBoxCenter(box: BoundingBox): [number, number, number] {
  return [
    (box.min[0] + box.max[0]) / 2,
    (box.min[1] + box.max[1]) / 2,
    (box.min[2] + box.max[2]) / 2
  ]
}

export function getBoundingBoxSize(box: BoundingBox): [number, number, number] {
  return [
    box.max[0] - box.min[0],
    box.max[1] - box.min[1],
    box.max[2] - box.min[2]
  ]
}

export function formatMeshStats(mesh: { num_cells?: number; num_points?: number; num_boundaries?: number }): string {
  const parts = []
  if (mesh.num_cells) parts.push(`${mesh.num_cells.toLocaleString()} cells`)
  if (mesh.num_points) parts.push(`${mesh.num_points.toLocaleString()} points`)
  if (mesh.num_boundaries) parts.push(`${mesh.num_boundaries} boundaries`)
  return parts.join(', ') || 'No statistics available'
}

export function getMeshTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    unstructured: 'Unstructured',
    structured: 'Structured',
    hybrid: 'Hybrid'
  }
  return labels[type] || type
}

export function getMeshStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'text-gray-500',
    generating: 'text-yellow-500',
    completed: 'text-green-500',
    failed: 'text-red-500'
  }
  return colors[status] || 'text-gray-500'
}