import { useState, useEffect } from 'react'

interface Simulation {
  id: string
  name: string
  projectId: string
  projectName: string
  meshId: string
  meshName: string
  solverType: string
  turbulenceModel: string
  status: string
  progress: number
  currentIteration: number
  maxIterations: number
  timeStep: number
  endTime: number
  cpuHours: number
  createdAt: string
  updatedAt: string
  startedAt?: string
  completedAt?: string
  residuals?: {
    Ux: number
    Uy: number
    Uz: number
    p: number
    k: number
    epsilon: number
  }
}

interface Project {
  id: string
  name: string
}

interface Mesh {
  id: string
  name: string
  projectId: string
}

export function SimulationsView() {
  const [simulations, setSimulations] = useState<Simulation[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [meshes, setMeshes] = useState<Mesh[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'list' | 'create'>('list')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedSimulation, setSelectedSimulation] = useState<Simulation | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [detailTab, setDetailTab] = useState<'overview' | 'residuals' | 'settings' | 'post'>('overview')

  const [newSimulation, setNewSimulation] = useState({
    name: '',
    projectId: '',
    meshId: '',
    solverType: 'openfoam',
    turbulenceModel: 'kOmegaSST',
    timeStep: 0.001,
    endTime: 1000,
    maxIterations: 1000,
  })

  useEffect(() => {
    // Mock data
    const mockProjects: Project[] = [
      { id: '1', name: 'Airfoil Analysis' },
      { id: '2', name: 'Pipe Flow' },
      { id: '3', name: 'Heat Exchanger' },
      { id: '4', name: 'Car Aerodynamics' },
      { id: '5', name: 'Turbine Blade' },
    ]

    const mockMeshes: Mesh[] = [
      { id: '1', name: 'Airfoil Mesh - Fine', projectId: '1' },
      { id: '2', name: 'Pipe Bend Mesh', projectId: '2' },
      { id: '3', name: 'Heat Exchanger Mesh', projectId: '3' },
      { id: '4', name: 'Car Body Mesh', projectId: '4' },
      { id: '5', name: 'Turbine Blade Mesh', projectId: '5' },
    ]

    const mockSimulations: Simulation[] = [
      {
        id: '1',
        name: 'Airfoil AoA 5deg',
        projectId: '1',
        projectName: 'Airfoil Analysis',
        meshId: '1',
        meshName: 'Airfoil Mesh - Fine',
        solverType: 'OpenFOAM',
        turbulenceModel: 'k-ω SST',
        status: 'running',
        progress: 65,
        currentIteration: 650,
        maxIterations: 1000,
        timeStep: 0.001,
        endTime: 1000,
        cpuHours: 12.5,
        createdAt: '2024-01-15',
        updatedAt: '2024-01-15',
        startedAt: '2024-01-15 10:30',
        residuals: { Ux: 1.2e-4, Uy: 8.5e-5, Uz: 9.1e-5, p: 2.3e-4, k: 1.8e-4, epsilon: 2.1e-4 },
      },
      {
        id: '2',
        name: 'Pipe Flow Re=50000',
        projectId: '2',
        projectName: 'Pipe Flow',
        meshId: '2',
        meshName: 'Pipe Bend Mesh',
        solverType: 'OpenFOAM',
        turbulenceModel: 'k-ε',
        status: 'running',
        progress: 42,
        currentIteration: 420,
        maxIterations: 1000,
        timeStep: 0.005,
        endTime: 500,
        cpuHours: 8.2,
        createdAt: '2024-01-14',
        updatedAt: '2024-01-14',
        startedAt: '2024-01-14 14:20',
        residuals: { Ux: 3.4e-3, Uy: 2.8e-3, Uz: 3.1e-3, p: 5.2e-3, k: 4.1e-3, epsilon: 3.8e-3 },
      },
      {
        id: '3',
        name: 'Car Aerodynamics - 60mph',
        projectId: '4',
        projectName: 'Car Aerodynamics',
        meshId: '4',
        meshName: 'Car Body Mesh',
        solverType: 'OpenFOAM',
        turbulenceModel: 'k-ω SST',
        status: 'pending',
        progress: 0,
        currentIteration: 0,
        maxIterations: 2000,
        timeStep: 0.001,
        endTime: 2000,
        cpuHours: 0,
        createdAt: '2024-01-12',
        updatedAt: '2024-01-12',
        residuals: { Ux: 0, Uy: 0, Uz: 0, p: 0, k: 0, epsilon: 0 },
      },
      {
        id: '4',
        name: 'Heat Exchanger - Design 1',
        projectId: '3',
        projectName: 'Heat Exchanger',
        meshId: '3',
        meshName: 'Heat Exchanger Mesh',
        solverType: 'OpenFOAM',
        turbulenceModel: 'k-ω SST',
        status: 'completed',
        progress: 100,
        currentIteration: 1000,
        maxIterations: 1000,
        timeStep: 0.01,
        endTime: 1000,
        cpuHours: 45.7,
        createdAt: '2024-01-10',
        updatedAt: '2024-01-10',
        startedAt: '2024-01-10 09:00',
        completedAt: '2024-01-10 18:30',
        residuals: { Ux: 8.2e-6, Uy: 6.1e-6, Uz: 7.3e-6, p: 1.2e-5, k: 9.4e-6, epsilon: 1.1e-5 },
      },
      {
        id: '5',
        name: 'Turbine Blade - Cooling',
        projectId: '5',
        projectName: 'Turbine Blade',
        meshId: '5',
        meshName: 'Turbine Blade Mesh',
        solverType: 'OpenFOAM',
        turbulenceModel: 'k-ω SST',
        status: 'failed',
        progress: 78,
        currentIteration: 780,
        maxIterations: 1000,
        timeStep: 0.001,
        endTime: 1000,
        cpuHours: 22.3,
        createdAt: '2024-01-08',
        updatedAt: '2024-01-08',
        startedAt: '2024-01-08 11:00',
        residuals: { Ux: 0.12, Uy: 0.08, Uz: 0.11, p: 0.15, k: 0.09, epsilon: 0.13 },
      },
    ]

    setProjects(mockProjects)
    setMeshes(mockMeshes)
    setSimulations(mockSimulations)
    setLoading(false)

    // Simulate running simulations
    const interval = setInterval(() => {
      setSimulations(prev => prev.map(sim => {
        if (sim.status === 'running' && sim.progress < 100) {
          const newProgress = Math.min(100, sim.progress + Math.random() * 2)
          const newIteration = Math.min(sim.maxIterations, sim.currentIteration + Math.floor(Math.random() * 5))
          return {
            ...sim,
            progress: newProgress,
            currentIteration: newIteration,
            updatedAt: new Date().toISOString().split('T')[0],
            residuals: sim.residuals ? {
              Ux: sim.residuals.Ux * 0.99,
              Uy: sim.residuals.Uy * 0.99,
              Uz: sim.residuals.Uz * 0.99,
              p: sim.residuals.p * 0.99,
              k: sim.residuals.k * 0.99,
              epsilon: sim.residuals.epsilon * 0.99,
            } : undefined,
          }
        }
        return sim
      }))
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'status-success'
      case 'completed': return 'status-success'
      case 'pending': return 'status-warning'
      case 'failed': return 'status-error'
      default: return 'status-default'
    }
  }

  const getStatusLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  const handleCreateSimulation = (e: React.FormEvent) => {
    e.preventDefault()
    const project = projects.find(p => p.id === newSimulation.projectId)
    const mesh = meshes.find(m => m.id === newSimulation.meshId)

    const simulation: Simulation = {
      id: Date.now().toString(),
      name: newSimulation.name,
      projectId: newSimulation.projectId,
      projectName: project?.name || '',
      meshId: newSimulation.meshId,
      meshName: mesh?.name || '',
      solverType: newSimulation.solverType === 'openfoam' ? 'OpenFOAM' : 'SU2',
      turbulenceModel: newSimulation.turbulenceModel === 'kOmegaSST' ? 'k-ω SST' :
        newSimulation.turbulenceModel === 'kEpsilon' ? 'k-ε' : 'Spalart-Allmaras',
      status: 'pending',
      progress: 0,
      currentIteration: 0,
      maxIterations: newSimulation.maxIterations,
      timeStep: newSimulation.timeStep,
      endTime: newSimulation.endTime,
      cpuHours: 0,
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0],
      residuals: { Ux: 0, Uy: 0, Uz: 0, p: 0, k: 0, epsilon: 0 },
    }

    setSimulations([simulation, ...simulations])
    setShowCreateModal(false)
    setNewSimulation({ name: '', projectId: '', meshId: '', solverType: 'openfoam', turbulenceModel: 'kOmegaSST', timeStep: 0.001, endTime: 1000, maxIterations: 1000 })
  }

  const handleStartSimulation = (id: string) => {
    setSimulations(prev => prev.map(sim =>
      sim.id === id ? { ...sim, status: 'running', startedAt: new Date().toISOString(), updatedAt: new Date().toISOString().split('T')[0] } : sim
    ))
  }

  const handleStopSimulation = (id: string) => {
    setSimulations(prev => prev.map(sim =>
      sim.id === id ? { ...sim, status: 'pending', updatedAt: new Date().toISOString().split('T')[0] } : sim
    ))
  }

  const handleDeleteSimulation = (id: string) => {
    if (window.confirm('Are you sure you want to delete this simulation?')) {
      setSimulations(prev => prev.filter(sim => sim.id !== id))
    }
  }

  if (loading) {
    return <div className="simulations-view loading">Loading simulations...</div>
  }

  return (
    <div className="simulations-view">
      <div className="view-header">
        <h2>Simulations</h2>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          + New Simulation
        </button>
      </div>

      <div className="simulations-grid">
        {simulations.map((sim) => (
          <div key={sim.id} className="simulation-card" onClick={() => { setSelectedSimulation(sim); setShowDetailModal(true); }}>
            <div className="simulation-header">
              <h3>{sim.name}</h3>
              <span className={`status-badge ${getStatusColor(sim.status)}`}>{getStatusLabel(sim.status)}</span>
            </div>
            <div className="simulation-meta">
              <div className="meta-item">
                <span className="meta-label">Project</span>
                <span className="meta-value">{sim.projectName}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Mesh</span>
                <span className="meta-value">{sim.meshName}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Solver</span>
                <span className="meta-value solver-badge">{sim.solverType}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Turbulence</span>
                <span className="meta-value">{sim.turbulenceModel}</span>
              </div>
            </div>

            {sim.status === 'running' && (
              <div className="simulation-progress">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${sim.progress}%` }}></div>
                </div>
                <div className="progress-info">
                  <span>Iteration: {sim.currentIteration} / {sim.maxIterations}</span>
                  <span>{sim.progress.toFixed(1)}%</span>
                </div>
              </div>
            )}

            {sim.status === 'completed' && (
              <div className="simulation-results">
                <span className="result-item">CPU Hours: {sim.cpuHours.toFixed(1)}</span>
                <span className="result-item">Residuals: {sim.residuals ? sim.residuals.Ux.toExponential(1) : 'N/A'}</span>
              </div>
            )}

            {sim.status === 'failed' && (
              <div className="simulation-error">
                <span>⚠️ Simulation failed at iteration {sim.currentIteration}</span>
                <span>Residuals diverged</span>
              </div>
            )}

            <div className="simulation-actions">
              {sim.status === 'pending' && (
                <button className="btn btn-sm btn-primary" onClick={(e) => { e.stopPropagation(); handleStartSimulation(sim.id); }}>
                  ▶️ Start
                </button>
              )}
              {sim.status === 'running' && (
                <button className="btn btn-sm btn-warning" onClick={(e) => { e.stopPropagation(); handleStopSimulation(sim.id); }}>
                  ⏸️ Stop
                </button>
              )}
              {sim.status === 'completed' && (
                <button className="btn btn-sm btn-secondary" onClick={(e) => { e.stopPropagation(); setSelectedSimulation(sim); setShowDetailModal(true); }}>
                  📈 Results
                </button>
              )}
              {sim.status === 'failed' && (
                <button className="btn btn-sm btn-secondary" onClick={(e) => { e.stopPropagation(); handleStartSimulation(sim.id); }}>
                  🔄 Restart
                </button>
              )}
              <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleDeleteSimulation(sim.id); }}>
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Simulation</h3>
              <button className="modal-close" onClick={() => setShowCreateModal(false)}>×</button>
            </div>
            <form onSubmit={handleCreateSimulation} className="modal-form">
              <div className="form-group">
                <label>Simulation Name</label>
                <input
                  type="text"
                  value={newSimulation.name}
                  onChange={(e) => setNewSimulation({ ...newSimulation, name: e.target.value })}
                  required
                  placeholder="e.g., Airfoil AoA 10deg"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Project</label>
                  <select
                    value={newSimulation.projectId}
                    onChange={(e) => setNewSimulation({ ...newSimulation, projectId: e.target.value, meshId: '' })}
                    required
                  >
                    <option value="">Select project...</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Mesh</label>
                  <select
                    value={newSimulation.meshId}
                    onChange={(e) => setNewSimulation({ ...newSimulation, meshId: e.target.value })}
                    required
                    disabled={!newSimulation.projectId}
                  >
                    <option value="">Select mesh...</option>
                    {meshes.filter(m => m.projectId === newSimulation.projectId).map((m) => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Solver</label>
                  <select
                    value={newSimulation.solverType}
                    onChange={(e) => setNewSimulation({ ...newSimulation, solverType: e.target.value })}
                  >
                    <option value="openfoam">OpenFOAM</option>
                    <option value="su2">SU2</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Turbulence Model</label>
                  <select
                    value={newSimulation.turbulenceModel}
                    onChange={(e) => setNewSimulation({ ...newSimulation, turbulenceModel: e.target.value })}
                  >
                    <option value="kOmegaSST">k-ω SST</option>
                    <option value="kEpsilon">k-ε</option>
                    <option value="spalartAllmaras">Spalart-Allmaras</option>
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Time Step</label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0.00001"
                    max="1"
                    value={newSimulation.timeStep}
                    onChange={(e) => setNewSimulation({ ...newSimulation, timeStep: parseFloat(e.target.value) })}
                  />
                </div>
                <div className="form-group">
                  <label>End Time</label>
                  <input
                    type="number"
                    step="1"
                    min="1"
                    max="100000"
                    value={newSimulation.endTime}
                    onChange={(e) => setNewSimulation({ ...newSimulation, endTime: parseFloat(e.target.value) })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Max Iterations</label>
                <input
                  type="number"
                  min="100"
                  max="100000"
                  value={newSimulation.maxIterations}
                  onChange={(e) => setNewSimulation({ ...newSimulation, maxIterations: parseInt(e.target.value) })}
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Simulation</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showDetailModal && selectedSimulation && (
        <div className="modal-overlay" onClick={() => setShowDetailModal(false)}>
          <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedSimulation.name}</h3>
              <button className="modal-close" onClick={() => setShowDetailModal(false)}>×</button>
            </div>
            <div className="modal-content">
              <div className="detail-tabs">
                <button className={`tab-btn ${detailTab === 'overview' ? 'active' : ''}`} onClick={() => setDetailTab('overview')}>Overview</button>
                <button className={`tab-btn ${detailTab === 'residuals' ? 'active' : ''}`} onClick={() => setDetailTab('residuals')}>Residuals</button>
                <button className={`tab-btn ${detailTab === 'settings' ? 'active' : ''}`} onClick={() => setDetailTab('settings')}>Settings</button>
              </div>

              {detailTab === 'overview' && (
                <div className="detail-grid">
                  <div className="detail-section">
                    <h4>Basic Information</h4>
                    <div className="detail-grid-inner">
                      <div className="detail-item"><label>Project</label><span>{selectedSimulation.projectName}</span></div>
                      <div className="detail-item"><label>Mesh</label><span>{selectedSimulation.meshName}</span></div>
                      <div className="detail-item"><label>Solver</label><span className="solver-badge">{selectedSimulation.solverType}</span></div>
                      <div className="detail-item"><label>Turbulence Model</label><span>{selectedSimulation.turbulenceModel}</span></div>
                      <div className="detail-item"><label>Status</label><span className={`status-badge ${getStatusColor(selectedSimulation.status)}`}>{getStatusLabel(selectedSimulation.status)}</span></div>
                      <div className="detail-item"><label>Created</label><span>{selectedSimulation.createdAt}</span></div>
                      <div className="detail-item"><label>Started</label><span>{selectedSimulation.startedAt || 'Not started'}</span></div>
                      <div className="detail-item"><label>Completed</label><span>{selectedSimulation.completedAt || 'Not completed'}</span></div>
                    </div>
                  </div>
                  <div className="detail-section">
                    <h4>Solver Settings</h4>
                    <div className="detail-grid-inner">
                      <div className="detail-item"><label>Time Step</label><span>{selectedSimulation.timeStep}</span></div>
                      <div className="detail-item"><label>End Time</label><span>{selectedSimulation.endTime}</span></div>
                      <div className="detail-item"><label>Max Iterations</label><span>{selectedSimulation.maxIterations}</span></div>
                      <div className="detail-item"><label>Current Iteration</label><span>{selectedSimulation.currentIteration}</span></div>
                      <div className="detail-item"><label>Progress</label><span>{selectedSimulation.progress.toFixed(1)}%</span></div>
                      <div className="detail-item"><label>CPU Hours</label><span>{selectedSimulation.cpuHours.toFixed(1)}</span></div>
                    </div>
                  </div>
                  <div className="detail-section">
                    <h4>Current Residuals</h4>
                    <div className="detail-grid-inner">
                      {selectedSimulation.residuals && (
                        <>
                          <div className="detail-item"><label>Ux</label><span>{selectedSimulation.residuals.Ux.toExponential(2)}</span></div>
                          <div className="detail-item"><label>Uy</label><span>{selectedSimulation.residuals.Uy.toExponential(2)}</span></div>
                          <div className="detail-item"><label>Uz</label><span>{selectedSimulation.residuals.Uz.toExponential(2)}</span></div>
                          <div className="detail-item"><label>p</label><span>{selectedSimulation.residuals.p.toExponential(2)}</span></div>
                          <div className="detail-item"><label>k</label><span>{selectedSimulation.residuals.k.toExponential(2)}</span></div>
                          <div className="detail-item"><label>ε</label><span>{selectedSimulation.residuals.epsilon.toExponential(2)}</span></div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {detailTab === 'residuals' && (
                <div className="residuals-chart">
                  <h4>Residual History</h4>
                  <div className="chart-placeholder">
                    <p>Residual convergence plot would be displayed here</p>
                    <p className="chart-note">(Real-time updates during simulation)</p>
                  </div>
                </div>
              )}

              {detailTab === 'settings' && (
                <div className="detail-section">
                  <h4>Solver Configuration</h4>
                  <pre className="config-preview">{
`/* OpenFOAM controlDict */
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         ${selectedSimulation.endTime};
deltaT          ${selectedSimulation.timeStep};
writeControl    timeStep;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

/* fvSchemes */
ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
    grad(p)         Gauss linear;
    grad(U)         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss upwind;
    div(phi,k)      Gauss upwind;
    div(phi,epsilon) Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

/* fvSolution */
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-06;
        relTol          0.1;
        smoother        GaussSeidel;
    }
    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-06;
        relTol          0.1;
    }
    k
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-06;
        relTol          0.1;
    }
    epsilon
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-06;
        relTol          0.1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent      yes;
    pRefCell        0;
    pRefValue       0;
}

relaxationFactors
{
    equations
    {
        U               0.7;
        k               0.7;
        epsilon         0.7;
    }
    fields
    {
        p               0.3;
    }
}`
                  }</pre>
                </div>
              )}

              <div className="modal-actions">
                {selectedSimulation.status === 'pending' && (
                  <button className="btn btn-primary" onClick={() => { handleStartSimulation(selectedSimulation.id); setShowDetailModal(false); }}>
                    ▶️ Start Simulation
                  </button>
                )}
                {selectedSimulation.status === 'running' && (
                  <button className="btn btn-warning" onClick={() => { handleStopSimulation(selectedSimulation.id); setShowDetailModal(false); }}>
                    ⏸️ Stop Simulation
                  </button>
                )}
                {selectedSimulation.status === 'completed' && (
                  <button className="btn btn-primary" onClick={() => { setShowDetailModal(false); setActiveTab('post'); }}>
                    📈 Post-Processing
                  </button>
                )}
                {selectedSimulation.status === 'failed' && (
                  <button className="btn btn-primary" onClick={() => { handleStartSimulation(selectedSimulation.id); setShowDetailModal(false); }}>
                    🔄 Restart
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}