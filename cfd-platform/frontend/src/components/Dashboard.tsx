import { useState, useEffect } from 'react'

interface Project {
  id: string
  name: string
  description: string
  solver: string
  status: string
  meshCount: number
  simulationCount: number
  updatedAt: string
}

interface Mesh {
  id: string
  name: string
  projectId: string
  format: string
  status: string
  elementCount: number
  nodeCount: number
  createdAt: string
}

interface Simulation {
  id: string
  name: string
  projectId: string
  meshId: string
  solverType: string
  status: string
  progress: number
  currentIteration: number
  maxIterations: number
  createdAt: string
}

interface Stats {
  totalProjects: number
  totalMeshes: number
  totalSimulations: number
  runningSimulations: number
  completedSimulations: number
  failedSimulations: number
  totalCpuHours: number
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats>({
    totalProjects: 0,
    totalMeshes: 0,
    totalSimulations: 0,
    runningSimulations: 0,
    completedSimulations: 0,
    failedSimulations: 0,
    totalCpuHours: 0,
  })
  const [recentProjects, setRecentProjects] = useState<Project[]>([])
  const [recentMeshes, setRecentMeshes] = useState<Mesh[]>([])
  const [recentSimulations, setRecentSimulations] = useState<Simulation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Mock data for preview
    const mockStats: Stats = {
      totalProjects: 12,
      totalMeshes: 45,
      totalSimulations: 78,
      runningSimulations: 3,
      completedSimulations: 65,
      failedSimulations: 10,
      totalCpuHours: 1247.5,
    }

    const mockProjects: Project[] = [
      { id: '1', name: 'Airfoil Analysis', description: 'NACA 0012 airfoil at various angles of attack', solver: 'OpenFOAM', status: 'active', meshCount: 5, simulationCount: 12, updatedAt: '2024-01-15' },
      { id: '2', name: 'Pipe Flow', description: 'Turbulent flow in a 90-degree pipe bend', solver: 'OpenFOAM', status: 'active', meshCount: 3, simulationCount: 8, updatedAt: '2024-01-14' },
      { id: '3', name: 'Heat Exchanger', description: 'Shell and tube heat exchanger optimization', solver: 'OpenFOAM', status: 'completed', meshCount: 4, simulationCount: 15, updatedAt: '2024-01-10' },
      { id: '4', name: 'Car Aerodynamics', description: 'External aerodynamics of sedan vehicle', solver: 'OpenFOAM', status: 'active', meshCount: 6, simulationCount: 22, updatedAt: '2024-01-12' },
      { id: '5', name: 'Turbine Blade', description: 'Gas turbine blade cooling analysis', solver: 'OpenFOAM', status: 'draft', meshCount: 2, simulationCount: 5, updatedAt: '2024-01-08' },
    ]

    const mockMeshes: Mesh[] = [
      { id: '1', name: 'Airfoil Mesh - Fine', projectId: '1', format: 'GMSH', status: 'completed', elementCount: 245000, nodeCount: 48500, createdAt: '2024-01-15' },
      { id: '2', name: 'Pipe Bend Mesh', projectId: '2', format: 'GMSH', status: 'completed', elementCount: 180000, nodeCount: 35000, createdAt: '2024-01-14' },
      { id: '3', name: 'Heat Exchanger Mesh', projectId: '3', format: 'GMSH', status: 'completed', elementCount: 320000, nodeCount: 62000, createdAt: '2024-01-10' },
      { id: '4', name: 'Car Body Mesh', projectId: '4', format: 'GMSH', status: 'generating', elementCount: 0, nodeCount: 0, createdAt: '2024-01-12' },
      { id: '5', name: 'Turbine Blade Mesh', projectId: '5', format: 'GMSH', status: 'completed', elementCount: 150000, nodeCount: 28000, createdAt: '2024-01-08' },
    ]

    const mockSimulations: Simulation[] = [
      { id: '1', name: 'Airfoil AoA 5deg', projectId: '1', meshId: '1', solverType: 'OpenFOAM', status: 'running', progress: 65, currentIteration: 650, maxIterations: 1000, createdAt: '2024-01-15' },
      { id: '2', name: 'Pipe Flow Re=50000', projectId: '2', meshId: '2', solverType: 'OpenFOAM', status: 'running', progress: 42, currentIteration: 420, maxIterations: 1000, createdAt: '2024-01-14' },
      { id: '3', name: 'Car Aerodynamics - 60mph', projectId: '4', meshId: '4', solverType: 'OpenFOAM', status: 'pending', progress: 0, currentIteration: 0, maxIterations: 2000, createdAt: '2024-01-12' },
      { id: '4', name: 'Heat Exchanger - Design 1', projectId: '3', meshId: '3', solverType: 'OpenFOAM', status: 'completed', progress: 100, currentIteration: 1000, maxIterations: 1000, createdAt: '2024-01-10' },
      { id: '5', name: 'Turbine Blade - Cooling', projectId: '5', meshId: '5', solverType: 'OpenFOAM', status: 'failed', progress: 78, currentIteration: 780, maxIterations: 1000, createdAt: '2024-01-08' },
    ]

    setTimeout(() => {
      setStats(mockStats)
      setRecentProjects(mockProjects)
      setRecentMeshes(mockMeshes)
      setRecentSimulations(mockSimulations)
      setLoading(false)
    }, 500)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'completed':
      case 'running':
        return 'status-success'
      case 'pending':
      case 'generating':
        return 'status-warning'
      case 'failed':
      case 'error':
        return 'status-error'
      case 'draft':
        return 'status-info'
      default:
        return 'status-default'
    }
  }

  const getStatusLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  if (loading) {
    return <div className="dashboard loading">Loading dashboard...</div>
  }

  return (
    <div className="dashboard">
      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon projects">📁</div>
          <div className="stat-content">
            <span className="stat-value">{stats.totalProjects}</span>
            <span className="stat-label">Total Projects</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon meshes">🔲</div>
          <div className="stat-content">
            <span className="stat-value">{stats.totalMeshes}</span>
            <span className="stat-label">Total Meshes</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon simulations">⚙️</div>
          <div className="stat-content">
            <span className="stat-value">{stats.totalSimulations}</span>
            <span className="stat-label">Total Simulations</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon running">🏃</div>
          <div className="stat-content">
            <span className="stat-value">{stats.runningSimulations}</span>
            <span className="stat-label">Running</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon completed">✅</div>
          <div className="stat-content">
            <span className="stat-value">{stats.completedSimulations}</span>
            <span className="stat-label">Completed</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon cpu">⏱️</div>
          <div className="stat-content">
            <span className="stat-value">{stats.totalCpuHours.toFixed(1)}</span>
            <span className="stat-label">CPU Hours</span>
          </div>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h3>Recent Projects</h3>
          <button className="btn btn-secondary">View All</button>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Solver</th>
                <th>Status</th>
                <th>Meshes</th>
                <th>Simulations</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {recentProjects.map((project) => (
                <tr key={project.id}>
                  <td>
                    <div className="project-name">
                      <strong>{project.name}</strong>
                      <span className="project-description">{project.description}</span>
                    </div>
                  </td>
                  <td><span className="solver-badge">{project.solver}</span></td>
                  <td><span className={`status-badge ${getStatusColor(project.status)}`}>{getStatusLabel(project.status)}</span></td>
                  <td>{project.meshCount}</td>
                  <td>{project.simulationCount}</td>
                  <td>{project.updatedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="dashboard-grid">
        <section className="dashboard-section">
          <div className="section-header">
            <h3>Recent Meshes</h3>
            <button className="btn btn-secondary">View All</button>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Project</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Elements</th>
                  <th>Nodes</th>
                </tr>
              </thead>
              <tbody>
                {recentMeshes.map((mesh) => (
                  <tr key={mesh.id}>
                    <td>{mesh.name}</td>
                    <td>{mesh.projectId}</td>
                    <td><span className="format-badge">{mesh.format}</span></td>
                    <td><span className={`status-badge ${getStatusColor(mesh.status)}`}>{getStatusLabel(mesh.status)}</span></td>
                    <td>{mesh.elementCount.toLocaleString()}</td>
                    <td>{mesh.nodeCount.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="dashboard-section">
          <div className="section-header">
            <h3>Recent Simulations</h3>
            <button className="btn btn-secondary">View All</button>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Solver</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Iteration</th>
                </tr>
              </thead>
              <tbody>
                {recentSimulations.map((sim) => (
                  <tr key={sim.id}>
                    <td>{sim.name}</td>
                    <td><span className="solver-badge">{sim.solverType}</span></td>
                    <td><span className={`status-badge ${getStatusColor(sim.status)}`}>{getStatusLabel(sim.status)}</span></td>
                    <td>
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${sim.progress}%` }}></div>
                      </div>
                      <span className="progress-text">{sim.progress}%</span>
                    </td>
                    <td>{sim.currentIteration} / {sim.maxIterations}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section className="dashboard-section quick-actions">
        <h3>Quick Actions</h3>
        <div className="action-buttons">
          <button className="btn btn-primary action-btn">
            <span className="action-icon">➕</span>
            <span>New Project</span>
          </button>
          <button className="btn btn-secondary action-btn">
            <span className="action-icon">🔲</span>
            <span>Generate Mesh</span>
          </button>
          <button className="btn btn-secondary action-btn">
            <span className="action-icon">▶️</span>
            <span>Run Simulation</span>
          </button>
          <button className="btn btn-secondary action-btn">
            <span className="action-icon">📈</span>
            <span>View Results</span>
          </button>
        </div>
      </section>
    </div>
  )
}