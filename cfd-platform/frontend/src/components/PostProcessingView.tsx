import { useState, useEffect } from 'react'

interface PostProcessingCase {
  id: string
  name: string
  simulationId: string
  simulationName: string
  projectName: string
  status: string
  variables: string[]
  timeSteps: number[]
  createdAt: string
  updatedAt: string
}

interface Visualization {
  id: string
  name: string
  type: string
  caseId: string
  config: Record<string, any>
  createdAt: string
}

export function PostProcessingView() {
  const [cases, setCases] = useState<PostProcessingCase[]>([])
  const [visualizations, setVisualizations] = useState<Visualization[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'cases' | 'visualizations' | 'compare' | 'overview' | 'variables'>('cases')
  const [selectedCase, setSelectedCase] = useState<PostProcessingCase | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [showCreateVizModal, setShowCreateVizModal] = useState(false)

  const [newVisualization, setNewVisualization] = useState({
    name: '',
    type: 'contour',
    variable: 'U',
    component: 'magnitude',
    timeStep: 0,
    colormap: 'viridis',
    opacity: 1.0,
    showMesh: false,
    clipPlane: false,
    clipOrigin: [0, 0, 0],
    clipNormal: [0, 0, 1],
  })

  useEffect(() => {
    const mockCases: PostProcessingCase[] = [
      {
        id: '1',
        name: 'Airfoil AoA 5deg - Results',
        simulationId: '1',
        simulationName: 'Airfoil AoA 5deg',
        projectName: 'Airfoil Analysis',
        status: 'ready',
        variables: ['U', 'p', 'k', 'omega', 'nut', 'wallShearStress'],
        timeSteps: [0, 100, 200, 300, 400, 500, 600, 650],
        createdAt: '2024-01-15',
        updatedAt: '2024-01-15',
      },
      {
        id: '2',
        name: 'Pipe Flow Re=50000 - Results',
        simulationId: '2',
        simulationName: 'Pipe Flow Re=50000',
        projectName: 'Pipe Flow',
        status: 'processing',
        variables: ['U', 'p', 'k', 'epsilon', 'nut'],
        timeSteps: [0, 50, 100, 150, 200, 250, 300, 350, 400, 420],
        createdAt: '2024-01-14',
        updatedAt: '2024-01-14',
      },
      {
        id: '3',
        name: 'Heat Exchanger - Design 1 Results',
        simulationId: '4',
        simulationName: 'Heat Exchanger - Design 1',
        projectName: 'Heat Exchanger',
        status: 'ready',
        variables: ['U', 'p', 'T', 'k', 'omega', 'nut', 'wallHeatFlux'],
        timeSteps: [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        createdAt: '2024-01-10',
        updatedAt: '2024-01-10',
      },
      {
        id: '4',
        name: 'Turbine Blade - Cooling Results',
        simulationId: '5',
        simulationName: 'Turbine Blade - Cooling',
        projectName: 'Turbine Blade',
        status: 'failed',
        variables: ['U', 'p', 'T', 'k', 'omega'],
        timeSteps: [0, 100, 200, 300, 400, 500, 600, 700, 780],
        createdAt: '2024-01-08',
        updatedAt: '2024-01-08',
      },
    ]

    const mockVisualizations: Visualization[] = [
      {
        id: '1',
        name: 'Velocity Magnitude Contour',
        type: 'contour',
        caseId: '1',
        config: { variable: 'U', component: 'magnitude', timeStep: 650, colormap: 'viridis', opacity: 1.0 },
        createdAt: '2024-01-15',
      },
      {
        id: '2',
        name: 'Pressure Coefficient on Surface',
        type: 'surface',
        caseId: '1',
        config: { variable: 'p', component: 'coefficient', timeStep: 650, colormap: 'RdBu', opacity: 1.0 },
        createdAt: '2024-01-15',
      },
      {
        id: '3',
        name: 'Streamlines Around Airfoil',
        type: 'streamlines',
        caseId: '1',
        config: { variable: 'U', seedType: 'line', seedPoints: 50, timeStep: 650, colormap: 'plasma' },
        createdAt: '2024-01-15',
      },
      {
        id: '4',
        name: 'Temperature Distribution',
        type: 'contour',
        caseId: '3',
        config: { variable: 'T', component: 'magnitude', timeStep: 1000, colormap: 'hot', opacity: 0.9 },
        createdAt: '2024-01-10',
      },
      {
        id: '5',
        name: 'Velocity Vectors - Mid Plane',
        type: 'vectors',
        caseId: '2',
        config: { variable: 'U', component: 'vector', timeStep: 420, scale: 0.01, colormap: 'viridis' },
        createdAt: '2024-01-14',
      },
      {
        id: '6',
        name: 'Turbulent Kinetic Energy Iso-surface',
        type: 'isosurface',
        caseId: '1',
        config: { variable: 'k', value: 0.5, timeStep: 650, colormap: 'plasma', opacity: 0.7 },
        createdAt: '2024-01-15',
      },
    ]

    setTimeout(() => {
      setCases(mockCases)
      setVisualizations(mockVisualizations)
      setLoading(false)
    }, 300)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'status-success'
      case 'processing': return 'status-warning'
      case 'failed': return 'status-error'
      default: return 'status-default'
    }
  }

  const getStatusLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'contour': return '🎨'
      case 'surface': return '📐'
      case 'streamlines': return '🌊'
      case 'vectors': return '➡️'
      case 'isosurface': return '🔮'
      case 'slice': return '🔪'
      case 'probe': return '📍'
      default: return '📊'
    }
  }

  const handleCreateVisualization = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCase) return

    const viz: Visualization = {
      id: Date.now().toString(),
      name: newVisualization.name,
      type: newVisualization.type,
      caseId: selectedCase.id,
      config: { ...newVisualization },
      createdAt: new Date().toISOString().split('T')[0],
    }

    setVisualizations([viz, ...visualizations])
    setShowCreateVizModal(false)
    setNewVisualization({
      name: '',
      type: 'contour',
      variable: 'U',
      component: 'magnitude',
      timeStep: 0,
      colormap: 'viridis',
      opacity: 1.0,
      showMesh: false,
      clipPlane: false,
      clipOrigin: [0, 0, 0],
      clipNormal: [0, 0, 1],
    })
  }

  const handleDeleteVisualization = (id: string) => {
    if (window.confirm('Delete this visualization?')) {
      setVisualizations(prev => prev.filter(v => v.id !== id))
    }
  }

  const handleExportImage = (viz: Visualization) => {
    alert(`Exporting ${viz.name} as PNG...`)
  }

  const handleExportAnimation = (caseId: string) => {
    alert(`Exporting animation for case ${caseId}...`)
  }

  if (loading) {
    return <div className="post-processing-view loading">Loading post-processing data...</div>
  }

  const caseVisualizations = selectedCase ? visualizations.filter(v => v.caseId === selectedCase.id) : []

  return (
    <div className="post-processing-view">
      <div className="view-header">
        <h2>Post-Processing</h2>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => setActiveTab('cases')}>Cases</button>
          <button className="btn btn-secondary" onClick={() => setActiveTab('visualizations')}>Visualizations</button>
          <button className="btn btn-secondary" onClick={() => setActiveTab('compare')}>Compare</button>
        </div>
      </div>

      {activeTab === 'cases' && (
        <div className="cases-grid">
          {cases.map((caseItem) => (
            <div key={caseItem.id} className="case-card" onClick={() => { setSelectedCase(caseItem); setShowDetailModal(true); }}>
              <div className="case-card-header">
                <h3>{caseItem.name}</h3>
                <span className={`status-badge ${getStatusColor(caseItem.status)}`}>{getStatusLabel(caseItem.status)}</span>
              </div>
              <div className="case-meta">
                <div className="meta-item">
                  <span className="meta-label">Simulation</span>
                  <span className="meta-value">{caseItem.simulationName}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Project</span>
                  <span className="meta-value">{caseItem.projectName}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Variables</span>
                  <span className="meta-value">{caseItem.variables.length}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Time Steps</span>
                  <span className="meta-value">{caseItem.timeSteps.length}</span>
                </div>
              </div>
              <div className="case-variables">
                {caseItem.variables.slice(0, 5).map(v => (
                  <span key={v} className="variable-tag">{v}</span>
                ))}
                {caseItem.variables.length > 5 && (
                  <span className="variable-tag more">+{caseItem.variables.length - 5} more</span>
                )}
              </div>
              <div className="case-actions">
                <button className="btn btn-sm btn-secondary" onClick={(e) => { e.stopPropagation(); handleExportAnimation(caseItem.id); }}>
                  🎬 Export Animation
                </button>
                <button className="btn btn-sm btn-primary" onClick={(e) => { e.stopPropagation(); setSelectedCase(caseItem); setShowCreateVizModal(true); }}>
                  + New Visualization
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'visualizations' && (
        <div className="visualizations-grid">
          {visualizations.map((viz) => {
            const caseItem = cases.find(c => c.id === viz.caseId)
            return (
              <div key={viz.id} className="viz-card">
                <div className="viz-preview">
                  <div className="viz-type-icon">{getTypeIcon(viz.type)}</div>
                  <div className="viz-type-badge">{viz.type}</div>
                </div>
                <div className="viz-info">
                  <h4>{viz.name}</h4>
                  <div className="viz-meta">
                    <span className="viz-case">{caseItem?.name || 'Unknown Case'}</span>
                    <span className="viz-config">{viz.type} • {viz.config.variable} • t={viz.config.timeStep}</span>
                  </div>
                </div>
                <div className="viz-actions">
                  <button className="btn btn-sm btn-secondary" onClick={(e) => { e.stopPropagation(); handleExportImage(viz); }}>
                    📷 Export
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleDeleteVisualization(viz.id); }}>
                    🗑️
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {activeTab === 'compare' && (
        <div className="compare-view">
          <h3>Case Comparison</h3>
          <div className="compare-controls">
            <div className="compare-selector">
              <label>Case A</label>
              <select>
                <option value="">Select case...</option>
                {cases.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="compare-selector">
              <label>Case B</label>
              <select>
                <option value="">Select case...</option>
                {cases.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="compare-selector">
              <label>Variable</label>
              <select>
                <option value="U">Velocity (U)</option>
                <option value="p">Pressure (p)</option>
                <option value="k">Turbulent Kinetic Energy (k)</option>
                <option value="T">Temperature (T)</option>
              </select>
            </div>
          </div>
          <div className="compare-placeholder">
            <p>Select two cases and a variable to compare results side-by-side</p>
            <div className="compare-preview">
              <div className="compare-pane">
                <h4>Case A</h4>
                <div className="empty-pane">No case selected</div>
              </div>
              <div className="compare-pane">
                <h4>Case B</h4>
                <div className="empty-pane">No case selected</div>
              </div>
              <div className="compare-pane">
                <h4>Difference</h4>
                <div className="empty-pane">Select cases to compute difference</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {showDetailModal && selectedCase && (
        <div className="modal-overlay" onClick={() => setShowDetailModal(false)}>
          <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedCase.name}</h3>
              <button className="modal-close" onClick={() => setShowDetailModal(false)}>×</button>
            </div>
            <div className="modal-content">
              <div className="detail-tabs">
                <button className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Overview</button>
                <button className={`tab-btn ${activeTab === 'variables' ? 'active' : ''}`} onClick={() => setActiveTab('variables')}>Variables</button>
                <button className={`tab-btn ${activeTab === 'visualizations' ? 'active' : ''}`} onClick={() => setActiveTab('visualizations')}>Visualizations ({caseVisualizations.length})</button>
              </div>

              {activeTab === 'overview' && (
                <div className="detail-grid">
                  <div className="detail-section">
                    <h4>Case Information</h4>
                    <div className="detail-grid-inner">
                      <div className="detail-item"><label>Simulation</label><span>{selectedCase.simulationName}</span></div>
                      <div className="detail-item"><label>Project</label><span>{selectedCase.projectName}</span></div>
                      <div className="detail-item"><label>Status</label><span className={`status-badge ${getStatusColor(selectedCase.status)}`}>{getStatusLabel(selectedCase.status)}</span></div>
                      <div className="detail-item"><label>Created</label><span>{selectedCase.createdAt}</span></div>
                      <div className="detail-item"><label>Updated</label><span>{selectedCase.updatedAt}</span></div>
                    </div>
                  </div>
                  <div className="detail-section">
                    <h4>Available Data</h4>
                    <div className="detail-grid-inner">
                      <div className="detail-item"><label>Variables</label><span>{selectedCase.variables.length}</span></div>
                      <div className="detail-item"><label>Time Steps</label><span>{selectedCase.timeSteps.length}</span></div>
                      <div className="detail-item"><label>Time Range</label><span>{selectedCase.timeSteps[0]} - {selectedCase.timeSteps[selectedCase.timeSteps.length - 1]}</span></div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'variables' && (
                <div className="variables-list">
                  <h4>Available Variables</h4>
                  <div className="variables-grid">
                    {selectedCase.variables.map(v => (
                      <div key={v} className="variable-card">
                        <span className="variable-name">{v}</span>
                        <span className="variable-type">{getVariableType(v)}</span>
                        <button className="btn btn-sm btn-secondary">Plot</button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'visualizations' && (
                <div className="case-visualizations">
                  {caseVisualizations.length === 0 ? (
                    <p className="empty-state">No visualizations created yet. Click "New Visualization" to create one.</p>
                  ) : (
                    caseVisualizations.map(viz => (
                      <div key={viz.id} className="viz-list-item">
                        <div className="viz-list-info">
                          <span className="viz-type-icon">{getTypeIcon(viz.type)}</span>
                          <div>
                            <strong>{viz.name}</strong>
                            <div className="viz-config">{viz.type} • {viz.config.variable} • t={viz.config.timeStep}</div>
                          </div>
                        </div>
                        <div className="viz-list-actions">
                          <button className="btn btn-sm btn-secondary" onClick={(e) => { e.stopPropagation(); handleExportImage(viz); }}>📷</button>
                          <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleDeleteVisualization(viz.id); }}>🗑️</button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              <div className="modal-actions">
                <button className="btn btn-primary" onClick={() => { setShowCreateVizModal(true); setShowDetailModal(false); }}>
                  + Create Visualization
                </button>
                <button className="btn btn-secondary" onClick={() => handleExportAnimation(selectedCase.id)}>
                  🎬 Export Animation
                </button>
                <button className="btn btn-secondary">📊 Generate Report</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showCreateVizModal && selectedCase && (
        <div className="modal-overlay" onClick={() => setShowCreateVizModal(false)}>
          <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create Visualization</h3>
              <button className="modal-close" onClick={() => setShowCreateVizModal(false)}>×</button>
            </div>
            <form onSubmit={handleCreateVisualization} className="modal-form">
              <div className="form-group">
                <label>Visualization Name</label>
                <input
                  type="text"
                  value={newVisualization.name}
                  onChange={(e) => setNewVisualization({ ...newVisualization, name: e.target.value })}
                  required
                  placeholder="e.g., Velocity Contour at Mid-span"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Type</label>
                  <select
                    value={newVisualization.type}
                    onChange={(e) => setNewVisualization({ ...newVisualization, type: e.target.value })}
                  >
                    <option value="contour">Contour Plot</option>
                    <option value="surface">Surface Plot</option>
                    <option value="streamlines">Streamlines</option>
                    <option value="vectors">Vector Field</option>
                    <option value="isosurface">Iso-surface</option>
                    <option value="slice">Slice Plane</option>
                    <option value="probe">Probe Points</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Variable</label>
                  <select
                    value={newVisualization.variable}
                    onChange={(e) => setNewVisualization({ ...newVisualization, variable: e.target.value })}
                  >
                    {selectedCase.variables.map(v => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Component</label>
                  <select
                    value={newVisualization.component}
                    onChange={(e) => setNewVisualization({ ...newVisualization, component: e.target.value })}
                  >
                    <option value="magnitude">Magnitude</option>
                    <option value="x">X Component</option>
                    <option value="y">Y Component</option>
                    <option value="z">Z Component</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Time Step</label>
                  <select
                    value={newVisualization.timeStep}
                    onChange={(e) => setNewVisualization({ ...newVisualization, timeStep: parseInt(e.target.value) })}
                  >
                    {selectedCase.timeSteps.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Colormap</label>
                  <select
                    value={newVisualization.colormap}
                    onChange={(e) => setNewVisualization({ ...newVisualization, colormap: e.target.value })}
                  >
                    <option value="viridis">Viridis</option>
                    <option value="plasma">Plasma</option>
                    <option value="inferno">Inferno</option>
                    <option value="magma">Magma</option>
                    <option value="RdBu">RdBu (Diverging)</option>
                    <option value="hot">Hot</option>
                    <option value="cool">Cool</option>
                    <option value="jet">Jet</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Opacity</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={newVisualization.opacity}
                    onChange={(e) => setNewVisualization({ ...newVisualization, opacity: parseFloat(e.target.value) })}
                  />
                  <span>{newVisualization.opacity}</span>
                </div>
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={newVisualization.showMesh}
                    onChange={(e) => setNewVisualization({ ...newVisualization, showMesh: e.target.checked })}
                  />
                  Show Mesh Overlay
                </label>
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={newVisualization.clipPlane}
                    onChange={(e) => setNewVisualization({ ...newVisualization, clipPlane: e.target.checked })}
                  />
                  Enable Clip Plane
                </label>
              </div>
              {newVisualization.clipPlane && (
                <div className="form-row">
                  <div className="form-group">
                    <label>Clip Origin (x, y, z)</label>
                    <input
                      type="text"
                      value={newVisualization.clipOrigin.join(', ')}
                      onChange={(e) => setNewVisualization({ ...newVisualization, clipOrigin: e.target.value.split(',').map(v => parseFloat(v.trim())) })}
                      placeholder="0, 0, 0"
                    />
                  </div>
                  <div className="form-group">
                    <label>Clip Normal (x, y, z)</label>
                    <input
                      type="text"
                      value={newVisualization.clipNormal.join(', ')}
                      onChange={(e) => setNewVisualization({ ...newVisualization, clipNormal: e.target.value.split(',').map(v => parseFloat(v.trim())) })}
                      placeholder="0, 0, 1"
                    />
                  </div>
                </div>
              )}
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateVizModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Visualization</button>
              </div>
            </form>
          </div>
        </div>
      )}    </div>
  )
}

function getVariableType(variable: string): string {
  const types: Record<string, string> = {
    'U': 'Vector',
    'p': 'Scalar',
    'k': 'Scalar',
    'epsilon': 'Scalar',
    'omega': 'Scalar',
    'nut': 'Scalar',
    'T': 'Scalar',
    'wallShearStress': 'Vector',
    'wallHeatFlux': 'Scalar',
  }
  return types[variable] || 'Scalar'
}