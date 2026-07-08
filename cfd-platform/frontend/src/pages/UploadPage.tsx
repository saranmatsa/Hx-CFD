import { useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { pipelineService, PipelineConfig } from '../services/pipelineService'

export default function UploadPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [config, setConfig] = useState<PipelineConfig>({
    element_size: 0.1,
    growth_rate: 1.2,
    num_boundary_layers: 3,
    solver: 'simpleFoam',
    start_time: 0,
    end_time: 100,
    visualization_fields: ['p', 'U'],
  })

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file || !projectId) throw new Error('Missing file or project')
      return pipelineService.start(projectId, file, config)
    },
    onSuccess: (data) => {
      navigate(`/projects/${projectId}/pipeline/${data.id}`)
    },
  })

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (isValidFile(droppedFile)) {
        setFile(droppedFile)
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const isValidFile = (file: File) => {
    const validExtensions = ['.step', '.stp', '.iges', '.igs']
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
    return validExtensions.includes(ext)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <button
          onClick={() => navigate(`/projects/${projectId}`)}
          className="text-gray-500 hover:text-gray-700 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Project
        </button>
      </div>

      <h1 className="text-2xl font-bold mb-6">Upload CAD File</h1>

      {/* File Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center mb-6 transition-colors ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : file
            ? 'border-green-500 bg-green-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        {file ? (
          <div className="flex items-center justify-center gap-4">
            <svg className="w-12 h-12 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="font-medium text-gray-900">{file.name}</p>
              <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <button
              onClick={() => setFile(null)}
              className="ml-4 text-gray-500 hover:text-red-500"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ) : (
          <>
            <svg className="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-gray-600 mb-2">Drag and drop your STEP or IGES file here</p>
            <p className="text-sm text-gray-500 mb-4">or</p>
            <label className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md cursor-pointer hover:bg-blue-700">
              <span>Browse Files</span>
              <input
                type="file"
                accept=".step,.stp,.iges,.igs"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
            <p className="text-xs text-gray-400 mt-4">Supported formats: STEP (.step, .stp), IGES (.iges, .igs)</p>
          </>
        )}
      </div>

      {/* Configuration Options */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Mesh Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Element Size
            </label>
            <input
              type="number"
              value={config.element_size}
              onChange={(e) => setConfig({ ...config, element_size: parseFloat(e.target.value) })}
              step="0.01"
              min="0.001"
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Growth Rate
            </label>
            <input
              type="number"
              value={config.growth_rate}
              onChange={(e) => setConfig({ ...config, growth_rate: parseFloat(e.target.value) })}
              step="0.1"
              min="1"
              max="2"
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Boundary Layers
            </label>
            <input
              type="number"
              value={config.num_boundary_layers}
              onChange={(e) => setConfig({ ...config, num_boundary_layers: parseInt(e.target.value) })}
              min="0"
              max="10"
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
        </div>
      </div>

      {/* Solver Configuration */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Solver Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Solver
            </label>
            <select
              value={config.solver}
              onChange={(e) => setConfig({ ...config, solver: e.target.value })}
              className="w-full px-3 py-2 border rounded-md"
            >
              <option value="simpleFoam">simpleFoam (Steady-state)</option>
              <option value="icoFoam">icoFoam (Transient, incompressible)</option>
              <option value="pisoFoam">pisoFoam (Transient, incompressible)</option>
              <option value="pimpleFoam">pimpleFoam (Transient, RANS/LES)</option>
              <option value="buoyantSimpleFoam">buoyantSimpleFoam (Buoyancy)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Time
            </label>
            <input
              type="number"
              value={config.end_time}
              onChange={(e) => setConfig({ ...config, end_time: parseFloat(e.target.value) })}
              min="0"
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
        </div>
      </div>

      {/* Visualization Fields */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Visualization Fields</h2>
        <div className="flex flex-wrap gap-2">
          {['p', 'U', 'T', 'k', 'epsilon', 'omega'].map((field) => (
            <label key={field} className="flex items-center gap-2 px-3 py-2 border rounded-md cursor-pointer hover:bg-gray-50">
              <input
                type="checkbox"
                checked={config.visualization_fields?.includes(field)}
                onChange={(e) => {
                  const fields = config.visualization_fields || []
                  if (e.target.checked) {
                    setConfig({ ...config, visualization_fields: [...fields, field] })
                  } else {
                    setConfig({ ...config, visualization_fields: fields.filter(f => f !== field) })
                  }
                }}
                className="rounded"
              />
              <span className="text-sm">{field === 'U' ? 'Velocity' : field === 'p' ? 'Pressure' : field}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Start Pipeline Button */}
      <div className="flex justify-end gap-4">
        <button
          onClick={() => navigate(`/projects/${projectId}`)}
          className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          onClick={() => uploadMutation.mutate()}
          disabled={!file || uploadMutation.isPending}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {uploadMutation.isPending ? (
            <>
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Starting Pipeline...
            </>
          ) : (
            'Start Pipeline'
          )}
        </button>
      </div>

      {/* Error Message */}
      {uploadMutation.isError && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          {uploadMutation.error instanceof Error ? uploadMutation.error.message : 'Failed to start pipeline'}
        </div>
      )}
    </div>
  )
}