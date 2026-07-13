import { useState, useEffect } from 'react'

interface Project {
  id: string
  name: string
  description: string
  solver: string
  turbulenceModel: string
  fluidProperties: string
  status: string
  meshCount: number
  simulationCount: number
  createdAt: string
  updatedAt: string
}

interface Solver {
  id: string
  name: string
  version: string
  description: string
}

interface TurbulenceModel {
  id: string
  name: string
  description: string
}

export function ProjectsView() {
  const [projects, setProjects] = useState<Project[]>([])
  const [solvers, setSolvers] = useState<Solver[]>([])
  const [turbulenceModels, setTurbulenceModels] = useState<TurbulenceModel[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)

  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    solver: 'openfoam',
    turbulenceModel: 'kEpsilon',
    fluidProperties: 'air',
  })

  useEffect(() => {
    // Mock data
    const mockSolvers: Solver[] = [
      { id: 'openfoam', name: 'OpenFOAM', version: 'v11', description: 'Open-source CFD toolbox' },
      { id: 'su2', name: 'SU2', version: 'v7.5.1', description: 'Open-source CFD for aerodynamics' },
      { id: 'code_saturne', name: 'Code_Saturne', version: 'v7.0', description: 'EDF open-source CFD' },
    ]

    const mockTurbulenceModels: TurbulenceModel[] = [
      { id: 'kEpsilon', name: 'k-ε', description: 'Standard k-epsilon model' },
      { id: 'kOmega', name: 'k-ω', description: 'Standard k-omega model' },
      { id: 'kOmegaSST', name: 'k-ω SST', description: 'Shear Stress Transport model' },
      { id: 'spalartAllmaras', name: 'Spalart-Allmaras', description: 'One-equation turbulence model' },
      { id: 'LES', name: 'LES', description: 'Large Eddy Simulation' },
      { id: 'DNS', name: 'DNS', description: 'Direct Numerical Simulation' },
    ]

    const mockProjects: Project[] = [
      {
        id: '1',
        name: 'Airfoil Analysis',
        description: 'NACA 0012 airfoil at various angles of attack (0-15°) for validation against experimental data',
        solver: 'OpenFOAM',
        turbulenceModel: 'k-ω SST',
        fluidProperties: 'Air (ρ=1.225, μ=1.789e-5)',
        status: 'active',
        meshCount: 5,
        simulationCount: 12,
        createdAt: '2024-01-10',
        updatedAt: '2024-01-15',
      },
      {
        id: '2',
        name: 'Pipe Flow',
        description: 'Turbulent flow in a 90-degree pipe bend at Re=50,000 with heat transfer',
        solver: 'OpenFOAM',
        turbulenceModel: 'k-ε',
        fluidProperties: 'Water (ρ=998, μ=1.002e-3)',
        status: 'active',
        meshCount: 3,
        simulationCount: 8,
        createdAt: '2024-01-08',
        updatedAt: '2024-01-14',
      },
      {
        id: '3',
        name: 'Heat Exchanger',
        description: 'Shell and tube heat exchanger optimization for maximum heat transfer',
        solver: 'OpenFOAM',
        turbulenceModel: 'k-ω SST',
        fluidProperties: 'Air/Water',
        status: 'completed',
        meshCount: 4,
        simulationCount: 15,
        createdAt: '2024-01-05',
        updatedAt: '2024-01-10',
      },
      {
        id: '4',
        name: 'Car Aerodynamics',
        description: 'External aerodynamics of sedan vehicle at 60 mph with rotating wheels',
        solver: 'OpenFOAM',
        turbulenceModel: 'k-ω SST',
        fluidProperties: 'Air (ρ=1.225, μ=1.789e-5)',
        status: 'active',
        meshCount: 6,
        simulationCount: 22,
        createdAt: '2024-01-03',
        updatedAt: '2024-01-12',
      },
      {
        id: '5',
        name: 'Turbine Blade',
        description: 'Gas turbine blade internal cooling passage analysis',
        solver: 'OpenFOAM',
        turbulenceModel: 'k-ε',
        fluidProperties: 'Air (ρ=0.5, μ=3.5e-5)',
        status: 'draft',
        meshCount: 2,
        simulationCount: 5,
        createdAt: '2024-01-01',
        updatedAt: '2024-01-08',
      },
    ]

    setTimeout(() => {
      setSolvers(mockSolvers)
      setTurbulenceModels(mockTurbulenceModels)
      setProjects(mockProjects)
      setLoading(false)
    }, 300)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'status-success'
      case 'completed': return 'status-success'
      case 'draft': return 'status-info'
      case 'archived': return 'status-default'
      default: return 'status-default'
    }
  }

  const getStatusLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  const handleCreateProject = (e: React.FormEvent) => {
    e.preventDefault()
    const project: Project = {
      id: String(Date.now()),
      ...newProject,
      status: 'draft',
      meshCount: 0,
      simulationCount: 0,
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0],
    }
    setProjects([project, ...projects])
    setShowCreateModal(false)
    setNewProject({ name: '', description: '', solver: 'openfoam', turbulenceModel: 'kEpsilon', fluidProperties: 'air' })
  }

  if (loading) {
    return <div className="projects-view loading">Loading projects...</div>
  }

  return (
    <div className="projects-view">
      <div className="view-header">
        <h2>Projects</h2>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          + New Project
        </button>
      </div>

      <div className="projects-grid">
        {projects.map((project) => (
          <div key={project.id} className="project-card" onClick={() => { setSelectedProject(project); setShowDetailModal(true); }}>
            <div className="project-card-header">
              <h3>{project.name}</h3>
              <span className={`status-badge ${getStatusColor(project.status)}`}>{getStatusLabel(project.status)}</span>
            </div>
            <p className="project-description">{project.description}</p>
            <div className="project-meta">
              <div className="meta-item">
                <span className="meta-label">Solver</span>
                <span className="meta-value">{project.solver}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Turbulence</span>
                <span className="meta-value">{project.turbulenceModel}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Fluid</span>
                <span className="meta-value">{project.fluidProperties}</span>
              </div>
            </div>
            <div className="project-stats">
              <div className="stat">
                <span className="stat-value">{project.meshCount}</span>
                <span className="stat-label">Meshes</span>
              </div>
              <div className="stat">
                <span className="stat-value">{project.simulationCount}</span>
                <span className="stat-label">Simulations</span>
              </div>
              <div className="stat">
                <span className="stat-value">{project.updatedAt}</span>
                <span className="stat-label">Updated</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Project</h3>
              <button className="modal-close" onClick={() => setShowCreateModal(false)}>×</button>
            </div>
            <form onSubmit={handleCreateProject}>
              <div className="form-group">
                <label>Project Name</label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  required
                  placeholder="Enter project name"
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  rows={3}
                  placeholder="Describe your CFD project"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Solver</label>
                  <select
                    value={newProject.solver}
                    onChange={(e) => setNewProject({ ...newProject, solver: e.target.value })}
                  >
                    {solvers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name} ({s.version})</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Turbulence Model</label>
                  <select
                    value={newProject.turbulenceModel}
                    onChange={(e) => setNewProject({ ...newProject, turbulenceModel: e.target.value })}
                  >
                    {turbulenceModels.map((m) => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Fluid Properties</label>
                <select
                  value={newProject.fluidProperties}
                  onChange={(e) => setNewProject({ ...newProject, fluidProperties: e.target.value })}
                >
                  <option value="air">Air (ρ=1.225, μ=1.789e-5)</option>
                  <option value="water">Water (ρ=998, μ=1.002e-3)</option>
                  <option value="custom">Custom...</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Project</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showDetailModal && selectedProject && (
        <div className="modal-overlay" onClick={() => setShowDetailModal(false)}>
          <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedProject.name}</h3>
              <button className="modal-close" onClick={() => setShowDetailModal(false)}>×</button>
            </div>
            <div className="modal-content">
              <div className="detail-section">
                <h4>Description</h4>
                <p>{selectedProject.description}</p>
              </div>
              <div className="detail-grid">
                <div className="detail-item">
                  <label>Solver</label>
                  <span>{selectedProject.solver}</span>
                </div>
                <div className="detail-item">
                  <label>Turbulence Model</label>
                  <span>{selectedProject.turbulenceModel}</span>
                </div>
                <div className="detail-item">
                  <label>Fluid Properties</label>
                  <span>{selectedProject.fluidProperties}</span>
                </div>
                <div className="detail-item">
                  <label>Status</label>
                  <span className={`status-badge ${getStatusColor(selectedProject.status)}`}>{getStatusLabel(selectedProject.status)}</span>
                </div>
                <div className="detail-item">
                  <label>Created</label>
                  <span>{selectedProject.createdAt}</span>
                </div>
                <div className="detail-item">
                  <label>Updated</label>
                  <span>{selectedProject.updatedAt}</span>
                </div>
              </div>
              <div className="detail-section">
                <h4>Statistics</h4>
                <div className="detail-stats">
                  <div className="detail-stat">
                    <span className="detail-stat-value">{selectedProject.meshCount}</span>
                    <span className="detail-stat-label">Meshes</span>
                  </div>
                  <div className="detail-stat">
                    <span className="detail-stat-value">{selectedProject.simulationCount}</span>
                    <span className="detail-stat-label">Simulations</span>
                  </div>
                </div>
              </div>
              <div className="modal-actions">
                <button className="btn btn-secondary">Edit Project</button>
                <button className="btn btn-primary">Open Project</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}