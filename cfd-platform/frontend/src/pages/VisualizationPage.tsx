import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useVisualization } from '../hooks/useVisualization'
import { VisualizationType } from '../types'
import { getColormapOptions, getDefaultFieldOptions } from '../utils/visualizationUtils'

export default function VisualizationPage() {
  const { simulationId } = useParams<{ simulationId: string }>()
  const { meshData, getScalarField, getVectorField, residuals, forces } = useVisualization(simulationId)

  const [selectedField, setSelectedField] = useState('p')
  const [selectedType, setSelectedType] = useState<VisualizationType>('contour')
  const [selectedTimeStep, setSelectedTimeStep] = useState(0)
  const [colormap, setColormap] = useState('viridis')

  const scalarQuery = getScalarField(selectedField, selectedTimeStep)
  const vectorQuery = getVectorField('U', selectedTimeStep)

  const fieldOptions = getDefaultFieldOptions()
  const colormapOptions = getColormapOptions()

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Visualization</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-white rounded-lg shadow p-6">
          <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
            {meshData ? (
              <div className="text-gray-500">
                3D Visualization Canvas
                <p className="text-sm mt-2">Points: {meshData.points?.length || 0}</p>
              </div>
            ) : (
              <div className="text-gray-400">No mesh data available</div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-4">Visualization Type</h3>
            <div className="space-y-2">
              {(['contour', 'vector', 'streamline', 'iso-surface', 'slice'] as VisualizationType[]).map((type) => (
                <label key={type} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="vizType"
                    checked={selectedType === type}
                    onChange={() => setSelectedType(type)}
                    className="text-blue-600"
                  />
                  <span className="capitalize">{type.replace('-', ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-4">Field Selection</h3>
            <select
              value={selectedField}
              onChange={(e) => setSelectedField(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4"
            >
              {fieldOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            <label className="block text-sm font-medium text-gray-700 mb-1">Time Step</label>
            <input
              type="number"
              value={selectedTimeStep}
              onChange={(e) => setSelectedTimeStep(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              min="0"
            />
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-4">Colormap</h3>
            <select
              value={colormap}
              onChange={(e) => setColormap(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              {colormapOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold mb-4">Scalar Field Data</h3>
          {scalarQuery.isLoading ? (
            <div className="animate-pulse">Loading...</div>
          ) : scalarQuery.data ? (
            <div className="space-y-2 text-sm">
              <p>Field: {scalarQuery.data.field_name}</p>
              <p>Min: {scalarQuery.data.min_value?.toFixed(4)}</p>
              <p>Max: {scalarQuery.data.max_value?.toFixed(4)}</p>
              <p>Points: {scalarQuery.data.points?.length || 0}</p>
            </div>
          ) : (
            <p className="text-gray-500">No data available</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold mb-4">Vector Field Data</h3>
          {vectorQuery.isLoading ? (
            <div className="animate-pulse">Loading...</div>
          ) : vectorQuery.data ? (
            <div className="space-y-2 text-sm">
              <p>Field: {vectorQuery.data.field_name}</p>
              <p>Scale: {vectorQuery.data.scale}</p>
              <p>Points: {vectorQuery.data.points?.length || 0}</p>
            </div>
          ) : (
            <p className="text-gray-500">No data available</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold mb-4">Solver Residuals</h3>
          {residuals ? (
            <div className="space-y-1 text-sm font-mono">
              {(residuals as any).residaries?.slice(-10).map((r: any, i: number) => (
                <div key={i} className="flex justify-between">
                  <span>{Object.keys(r)[0]}</span>
                  <span>{Object.values(r)[0]}</span>
                </div>
              )) || <p className="text-gray-500">No residuals data</p>}
            </div>
          ) : (
            <p className="text-gray-500">No residuals available</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold mb-4">Force Coefficients</h3>
          {forces ? (
            <div className="space-y-2 text-sm">
              {(forces as any).forces?.map((f: any, i: number) => (
                <div key={i} className="flex justify-between">
                  <span>{f.name || `Force ${i + 1}`}</span>
                  <span>{f.value?.toFixed(4)}</span>
                </div>
              )) || <p className="text-gray-500">No force data</p>}
            </div>
          ) : (
            <p className="text-gray-500">No force data available</p>
          )}
        </div>
      </div>
    </div>
  )
}