import { useState, useEffect } from 'react'

interface Mesh {
  id: string
  name: string
  projectId: string
  projectName: string
  format: string
  status: string
  elementCount: number
  nodeCount: number
  quality: {
    minQuality: number
    maxAspectRatio: number
    skewedElements: number
  }
  bounds: {
    min: [number, number, number]
    max: [number, number, number]
  }
  createdAt: string
  updatedAt: string
}

interface Project {
  id: string
  name: string
}

interface MeshGenerationParams {
  projectId: string
  name: string
  algorithm: string
  elementSize: number
  boundaryLayers: number
  growthRate: number
}

export function MeshesView() {
  const [meshes, setMeshes] = useState<Mesh[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedMesh, setSelectedMesh] = useState<Mesh | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [, setShowGenerateModal] = useState(false)
  const [activeTab, setActiveTab] = useState<'list' | 'generate'>('list')

  const [generationParams, setGenerationParams] = useState<MeshGenerationParams>({
    projectId: '',
    name: '',
    algorithm: 'delaunay3d',
    elementSize: 0.01,
    boundaryLayers: 5,
    growthRate: 1.2,
  })

  const [generationProgress, setGenerationProgress] = useState(0)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    const mockProjects: Project[] = [
      { id: '1', name: 'Airfoil Analysis' },
      { id: '2', name: 'Pipe Flow' },
      { id: '3', name: 'Heat Exchanger' },
      { id: '4', name: 'Car Aerodynamics' },
      { id: '5', name: 'Turbine Blade' },
    ]

    const mockMeshes: Mesh[] = [
      {
        id: '1',
        name: 'Airfoil Mesh - Fine',
        projectId: '1',
        projectName: 'Airfoil Analysis',
        format: 'GMSH',
        status: 'completed',
        elementCount: 245000,
        nodeCount: 48500,
        quality: { minQuality: 0.72, maxAspectRatio: 12.5, skewedElements: 3 },
        bounds: { min: [-1, -0.5, -0.1], max: [2, 0.5, 0.1] },
        createdAt: '2024-01-15',
        updatedAt: '2024-01-15',
      },
      {
        id: '2',
        name: 'Airfoil Mesh - Coarse',
        projectId: '1',
        projectName: 'Airfoil Analysis',
        format: 'GMSH',
        status: 'completed',
        elementCount: 85000,
        nodeCount: 17200,
        quality: { minQuality: 0.68, maxAspectRatio: 18.2, skewedElements: 12 },
        bounds: { min: [-1, -0.5, -0.1], max: [2, 0.5, 0.1] },
        createdAt: '2024-01-14',
        updatedAt: '2024-01-14',
      },
      {
        id: '3',
        name: 'Pipe Bend Mesh',
        projectId: '2',
        projectName: 'Pipe Flow',
        format: 'GMSH',
        status: 'completed',
        elementCount: 180000,
        nodeCount: 35000,
        quality: { minQuality: 0.75, maxAspectRatio: 10.8, skewedElements: 1 },
        bounds: { min: [0, 0, 0], max: [0.5, 0.5, 0.5] },
        createdAt: '2024-01-14',
        updatedAt: '2024-01-14',
      },
      {
        id: '4',
        name: 'Heat Exchanger Mesh',
        projectId: '3',
        projectName: 'Heat Exchanger',
        format: 'GMSH',
        status: 'completed',
        elementCount: 320000,
        nodeCount: 62000,
        quality: { minQuality: 0.71, maxAspectRatio: 14.3, skewedElements: 5 },
        bounds: { min: [0, 0, 0], max: [1, 0.5, 0.3] },
        createdAt: '2024-01-10',
        updatedAt: '2024-01-10',
      },
      {
        id: '5',
        name: 'Car Body Mesh',
        projectId: '4',
        projectName: 'Car Aerodynamics',
        format: 'GMSH',
        status: 'generating',
        elementCount: 0,
        nodeCount: 0,
        quality: { minQuality: 0, maxAspectRatio: 0, skewedElements: 0 },
        bounds: { min: [0, 0, 0], max: [0, 0, 0] },
        createdAt: '2024-01-12',
        updatedAt: '2024-01-12',
      },
      {
        id: '6',
        name: 'Turbine Blade Mesh',
        projectId: '5',
        projectName: 'Turbine Blade',
        format: 'GMSH',
        status: 'completed',
        elementCount: 150000,
        nodeCount: 28000,
        quality: { minQuality: 0.78, maxAspectRatio: 9.2, skewedElements: 0 },
        bounds: { min: [0, 0, 0], max: [0.15, 0.05, 0.02] },
        createdAt: '2024-01-08',
        updatedAt: '2024-01-08',
      },
    ]

    setTimeout(() => {
      setProjects(mockProjects)
      setMeshes(mockMeshes)
      setLoading(false)
    }, 300)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'status-success'
      case 'generating': return 'status-warning'
      case 'failed': return 'status-error'
      case 'pending': return 'status-info'
      default: return 'status-default'
    }
  }

  const getStatusLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  const handleGenerateMesh = (e: React.FormEvent) => {
    e.preventDefault()
    setGenerating(true)
    setGenerationProgress(0)

    // Simulate mesh generation progress
    const interval = setInterval(() => {
      setGenerationProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval)
          return 90
        }
        return prev + Math.random() * 15
      })
    }, 500)

    // Simulate completion
    setTimeout(() => {
      clearInterval(interval)
      setGenerationProgress(100)
      setGenerating(false)

      const newMesh: Mesh = {
        id: String(Date.now()),
        name: generationParams.name,
        projectId: generationParams.projectId,
        projectName: projects.find(p => p.id === generationParams.projectId)?.name || '',
        format: 'GMSH',
        status: 'completed',
        elementCount: Math.floor(Math.random() * 200000) + 100000,
        nodeCount: Math.floor(Math.random() * 40000) + 20000,
        quality: {
          minQuality: 0.7 + Math.random() * 0.15,
          maxAspectRatio: 8 + Math.random() * 10,
          skewedElements: Math.floor(Math.random() * 10),
        },
        bounds: {
          min: [0, 0, 0],
          max: [1, 1, 1],
        },
        createdAt: new Date().toISOString().split('T')[0],
        updatedAt: new Date().toISOString().split('T')[0],
      }

      setMeshes([newMesh, ...meshes])
      setShowGenerateModal(false)
      setGenerationParams({ projectId: '', name: '', algorithm: 'delaunay3d', elementSize: 0.01, boundaryLayers: 5, growthRate: 1.2 })
      setGenerationProgress(0)
    }, 5000)
  }

  if (loading) {
    return <div className="meshes-view loading">Loading meshes...</div>
  }

  return (
    <div className="meshes-view">
      <div className="view-header">
        <h2>Meshes</h2>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => { setActiveTab('generate'); setShowGenerateModal(true); }}>
            + Generate Mesh
          </button>
          <button className="btn btn-secondary" onClick={() => setActiveTab('list')}>
            Mesh List
          </button>
        </div>
      </div>

      {activeTab === 'generate' && (
        <div className="generate-panel">
          <h3>Generate New Mesh</h3>
          <form onSubmit={handleGenerateMesh} className="generate-form">
            <div className="form-row">
              <div className="form-group">
                <label>Project</label>
                <select
                  value={generationParams.projectId}
                  onChange={(e) => setGenerationParams({ ...generationParams, projectId: e.target.value })}
                  required
                >
                  <option value="">Select project...</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Mesh Name</label>
                <input
                  type="text"
                  value={generationParams.name}
                  onChange={(e) => setGenerationParams({ ...generationParams, name: e.target.value })}
                  required
                  placeholder="e.g., Airfoil Mesh - Fine"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Algorithm</label>
                <select
                  value={generationParams.algorithm}
                  onChange={(e) => setGenerationParams({ ...generationParams, algorithm: e.target.value })}
                >
                  <option value="delaunay3d">Delaunay 3D (Gmsh)</option>
                  <option value="hxt">HXT (Hex-dominant)</option>
                  <option value="netgen">Netgen</option>
                  <option value="mmg">MMG (Remeshing)</option>
                  <option value="boundary_layer">Boundary Layer</option>
                </select>
              </div>
              <div className="form-group">
                <label>Element Size</label>
                <input
                  type="number"
                  step="0.001"
                  min="0.0001"
                  max="1"
                  value={generationParams.elementSize}
                  onChange={(e) => setGenerationParams({ ...generationParams, elementSize: parseFloat(e.target.value) })}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Boundary Layers</label>
                <input
                  type="number"
                  min="0"
                  max="20"
                  value={generationParams.boundaryLayers}
                  onChange={(e) => setGenerationParams({ ...generationParams, boundaryLayers: parseInt(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label>Growth Rate</label>
                <input
                  type="number"
                  step="0.1"
                  min="1.0"
                  max="2.0"
                  value={generationParams.growthRate}
                  onChange={(e) => setGenerationParams({ ...generationParams, growthRate: parseFloat(e.target.value) })}
                />
              </div>
            </div>

            {generating && (
              <div className="generation-progress">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${generationProgress}%` }}></div>
                </div>
                <span>Generating mesh... {Math.round(generationProgress)}%</span>
              </div>
            )}

            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={() => { setActiveTab('list'); setShowGenerateModal(false); }}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={generating}>
                {generating ? 'Generating...' : 'Generate Mesh'}
              </button>
            </div>
          </form>
        </div>
      )}

      {activeTab === 'list' && (
        <div className="meshes-grid">
          {meshes.map((mesh) => (
            <div key={mesh.id} className="mesh-card" onClick={() => { setSelectedMesh(mesh); setShowDetailModal(true); }}>
              <div className="mesh-card-header">
                <h3>{mesh.name}</h3>
                <span className={`status-badge ${getStatusColor(mesh.status)}`}>{getStatusLabel(mesh.status)}</span>
              </div>
              <div className="mesh-project">{mesh.projectName}</div>
              <div className="mesh-meta">
                <div className="meta-item">
                  <span className="meta-label">Format</span>
                  <span className="meta-value format-badge">{mesh.format}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Elements</span>
                  <span className="meta-value">{mesh.elementCount.toLocaleString()}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Nodes</span>
                  <span className="meta-value">{mesh.nodeCount.toLocaleString()}</span>
                </div>
              </div>
              {mesh.status === 'completed' && (
                <div className="mesh-quality">
                  <div className="quality-item">
                    <span className="quality-label">Min Quality</span>
                    <span className="quality-value">{mesh.quality.minQuality.toFixed(2)}</span>
                  </div>
                  <div className="quality-item">
                    <span className="quality-label">Max Aspect Ratio</span>
                    <span className="quality-value">{mesh.quality.maxAspectRatio.toFixed(1)}</span>
                  </div>
                  <div className="quality-item">
                    <span className="quality-label">Skewed Elements</span>
                    <span className="quality-value">{mesh.quality.skewedElements}</span>
                  </div>
                </div>
              )}
              <div className="mesh-date">Updated: {mesh.updatedAt}</div>
            </div>
          ))}
        </div>
      )}

      {showDetailModal && selectedMesh && (
        <div className="modal-overlay" onClick={() => setShowDetailModal(false)}>
          <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedMesh.name}</h3>
              <button className="modal-close" onClick={() => setShowDetailModal(false)}>×</button>
            </div>
            <div className="modal-content">
              <div className="detail-grid">
                <div className="detail-section">
                  <h4>Basic Information</h4>
                  <div className="detail-grid-inner">
                    <div className="detail-item"><label>Project</label><span>{selectedMesh.projectName}</span></div>
                    <div className="detail-item"><label>Format</label><span className="format-badge">{selectedMesh.format}</span></div>
                    <div className="detail-item"><label>Status</label><span className={`status-badge ${getStatusColor(selectedMesh.status)}`}>{getStatusLabel(selectedMesh.status)}</span></div>
                    <div className="detail-item"><label>Created</label><span>{selectedMesh.createdAt}</span></div>
                    <div className="detail-item"><label>Updated</label><span>{selectedMesh.updatedAt}</span></div>
                  </div>
                </div>
                <div className="detail-section">
                  <h4>Mesh Statistics</h4>
                  <div className="detail-grid-inner">
                    <div className="detail-item"><label>Elements</label><span>{selectedMesh.elementCount.toLocaleString()}</span></div>
                    <div className="detail-item"><label>Nodes</label><span>{selectedMesh.nodeCount.toLocaleString()}</span></div>
                    <div className="detail-item"><label>Min Quality</label><span>{selectedMesh.quality.minQuality.toFixed(3)}</span></div>
                    <div className="detail-item"><label>Max Aspect Ratio</label><span>{selectedMesh.quality.maxAspectRatio.toFixed(1)}</span></div>
                    <div className="detail-item"><label>Skewed Elements</label><span>{selectedMesh.quality.skewedElements}</span></div>
                  </div>
                </div>
                <div className="detail-section">
                  <h4>Bounding Box</h4>
                  <div className="detail-grid-inner">
                    <div className="detail-item"><label>Min X</label><span>{selectedMesh.bounds.min[0].toFixed(3)}</span></div>
                    <div className="detail-item"><label>Min Y</label><span>{selectedMesh.bounds.min[1].toFixed(3)}</span></div>
                    <div className="detail-item"><label>Min Z</label><span>{selectedMesh.bounds.min[2].toFixed(3)}</span></div>
                    <div className="detail-item"><label>Max X</label><span>{selectedMesh.bounds.max[0].toFixed(3)}</span></div>
                    <div className="detail-item"><label>Max Y</label><span>{selectedMesh.bounds.max[1].toFixed(3)}</span></div>
                    <div className="detail-item"><label>Max Z</label><span>{selectedMesh.bounds.max[2].toFixed(3)}</span></div>
                  </div>
                </div>
              </div>
              <div className="modal-actions">
                <button className="btn btn-secondary">Export Mesh</button>
                <button className="btn btn-secondary">Quality Report</button>
                <button className="btn btn-primary">Use in Simulation</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
