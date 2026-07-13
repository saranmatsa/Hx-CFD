import { useState, useEffect } from 'react'

interface SolverConfig {
  id: string
  name: string
  path: string
  version: string
  status: 'found' | 'not_found' | 'checking'
  type: 'openfoam' | 'gmsh' | 'paraview' | 'python'
}

interface ProjectSettings {
  defaultSolver: string
  defaultTurbulenceModel: string
  defaultMeshAlgorithm: string
  autoSaveInterval: number
  maxConcurrentSimulations: number
  defaultOutputFormat: string
}

interface AppSettings {
  theme: 'light' | 'dark' | 'system'
  language: string
  autoCheckUpdates: boolean
  telemetryEnabled: boolean
  logLevel: 'debug' | 'info' | 'warn' | 'error'
}

interface LicenseInfo {
  type: 'community' | 'professional' | 'enterprise'
  status: 'active' | 'expired' | 'trial'
  expiresAt?: string
  features: string[]
}

export function SettingsView() {
  const [activeTab, setActiveTab] = useState<'solvers' | 'projects' | 'app' | 'license' | 'advanced'>('solvers')
  const [solvers, setSolvers] = useState<SolverConfig[]>([])
  const [projectSettings, setProjectSettings] = useState<ProjectSettings>({
    defaultSolver: 'openfoam',
    defaultTurbulenceModel: 'kOmegaSST',
    defaultMeshAlgorithm: 'delaunay3d',
    autoSaveInterval: 300,
    maxConcurrentSimulations: 2,
    defaultOutputFormat: 'vtk',
  })
  const [appSettings, setAppSettings] = useState<AppSettings>({
    theme: 'system',
    language: 'en',
    autoCheckUpdates: true,
    telemetryEnabled: false,
    logLevel: 'info',
  })
  const [license] = useState<LicenseInfo>({
    type: 'community',
    status: 'active',
    features: ['Basic CFD', 'Mesh Generation', 'Post-Processing'],
  })
  const [checkingSolvers, setCheckingSolvers] = useState(false)
  const [testingSolver, setTestingSolver] = useState<string | null>(null)
  const [showAddSolverModal, setShowAddSolverModal] = useState(false)
  const [newSolver, setNewSolver] = useState({ name: '', path: '', type: 'openfoam' as SolverConfig['type'] })

  useEffect(() => {
    const mockSolvers: SolverConfig[] = [
      { id: '1', name: 'OpenFOAM v11', path: 'C:\\OpenFOAM\\v11', version: '11.0.0', status: 'found', type: 'openfoam' },
      { id: '2', name: 'OpenFOAM v10', path: 'C:\\OpenFOAM\\v10', version: '10.1.1', status: 'found', type: 'openfoam' },
      { id: '3', name: 'Gmsh 4.12.2', path: 'C:\\Gmsh\\4.12.2\\gmsh.exe', version: '4.12.2', status: 'found', type: 'gmsh' },
      { id: '4', name: 'ParaView 5.12.0', path: 'C:\\ParaView\\5.12.0\\bin\\paraview.exe', version: '5.12.0', status: 'found', type: 'paraview' },
      { id: '5', name: 'Python 3.11', path: 'C:\\Python311\\python.exe', version: '3.11.5', status: 'found', type: 'python' },
      { id: '6', name: 'SU2 v7.5.1', path: 'C:\\SU2\\v7.5.1\\bin\\SU2_CFD.exe', version: '7.5.1', status: 'not_found', type: 'openfoam' },
    ]
    setSolvers(mockSolvers)
  }, [])

  const checkSolver = async (solver: SolverConfig) => {
    setTestingSolver(solver.id)
    await new Promise(resolve => setTimeout(resolve, 1500))
    setSolvers(prev => prev.map(s => s.id === solver.id ? { ...s, status: 'found' as const } : s))
    setTestingSolver(null)
  }

  const checkAllSolvers = async () => {
    setCheckingSolvers(true)
    await new Promise(resolve => setTimeout(resolve, 2000))
    setSolvers(prev => prev.map(s => ({ ...s, status: 'found' as const })))
    setCheckingSolvers(false)
  }

  const handleAddSolver = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newSolver.name || !newSolver.path) return

    const solver: SolverConfig = {
      id: Date.now().toString(),
      name: newSolver.name,
      path: newSolver.path,
      version: 'Unknown',
      status: 'checking',
      type: newSolver.type,
    }
    setSolvers([...solvers, solver])
    setShowAddSolverModal(false)
    setNewSolver({ name: '', path: '', type: 'openfoam' })
    setTimeout(() => checkSolver(solver), 500)
  }

  const handleRemoveSolver = (id: string) => {
    if (window.confirm('Remove this solver configuration?')) {
      setSolvers(prev => prev.filter(s => s.id !== id))
    }
  }

  const handleProjectSettingsChange = (key: keyof ProjectSettings, value: any) => {
    setProjectSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleAppSettingsChange = (key: keyof AppSettings, value: any) => {
    setAppSettings(prev => ({ ...prev, [key]: value }))
    if (key === 'theme') {
      document.documentElement.setAttribute('data-theme', value)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'found': return 'status-success'
      case 'not_found': return 'status-error'
      case 'checking': return 'status-warning'
      default: return 'status-default'
    }
  }

  const getStatusLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'openfoam': return '🌊'
      case 'gmsh': return '🔷'
      case 'paraview': return '📊'
      case 'python': return '🐍'
      default: return '⚙️'
    }
  }

  const getTypeLabel = (type: string) => {
    return type.charAt(0).toUpperCase() + type.slice(1)
  }

  return (
    <div className="settings-view">
      <div className="view-header">
        <h2>Settings</h2>
      </div>

      <div className="settings-layout">
        <nav className="settings-nav">
          <button className={`nav-item ${activeTab === 'solvers' ? 'active' : ''}`} onClick={() => setActiveTab('solvers')}>
            <span className="nav-icon">⚙️</span> Solvers & Tools
          </button>
          <button className={`nav-item ${activeTab === 'projects' ? 'active' : ''}`} onClick={() => setActiveTab('projects')}>
            <span className="nav-icon">📁</span> Project Defaults
          </button>
          <button className={`nav-item ${activeTab === 'app' ? 'active' : ''}`} onClick={() => setActiveTab('app')}>
            <span className="nav-icon">🎨</span> Appearance
          </button>
          <button className={`nav-item ${activeTab === 'license' ? 'active' : ''}`} onClick={() => setActiveTab('license')}>
            <span className="nav-icon">📄</span> License
          </button>
          <button className={`nav-item ${activeTab === 'advanced' ? 'active' : ''}`} onClick={() => setActiveTab('advanced')}>
            <span className="nav-icon">🔧</span> Advanced
          </button>
        </nav>

        <div className="settings-content">
          {activeTab === 'solvers' && (
            <div className="settings-section">
              <div className="section-header">
                <h3>Solver & Tool Configuration</h3>
                <div className="section-actions">
                  <button className="btn btn-secondary" onClick={checkAllSolvers} disabled={checkingSolvers}>
                    {checkingSolvers ? '🔄 Checking...' : '🔍 Check All'}
                  </button>
                  <button className="btn btn-primary" onClick={() => setShowAddSolverModal(true)}>
                    + Add Solver
                  </button>
                </div>
              </div>

              <div className="solvers-table">
                <table>
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Name</th>
                      <th>Path</th>
                      <th>Version</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {solvers.map(solver => (
                      <tr key={solver.id}>
                        <td><span className="type-badge">{getTypeIcon(solver.type)} {getTypeLabel(solver.type)}</span></td>
                        <td><strong>{solver.name}</strong></td>
                        <td className="path-cell" title={solver.path}>{solver.path}</td>
                        <td>{solver.version}</td>
                        <td>
                          <span className={`status-badge ${getStatusColor(solver.status)}`}>
                            {solver.status === 'checking' ? '🔄 Checking...' : getStatusLabel(solver.status)}
                          </span>
                        </td>
                        <td className="actions-cell">
                          {solver.status !== 'found' && !testingSolver && (
                            <button className="btn btn-sm btn-secondary" onClick={() => checkSolver(solver)}>
                              Check
                            </button>
                          )}
                          {testingSolver === solver.id && <span className="checking">🔄</span>}
                          <button className="btn btn-sm btn-danger" onClick={() => handleRemoveSolver(solver.id)}>
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="solver-hints">
                <h4>Expected Paths</h4>
                <ul>
                  <li><strong>OpenFOAM:</strong> Root installation directory (e.g., <code>C:\OpenFOAM\v11</code>)</li>
                  <li><strong>Gmsh:</strong> Executable file (e.g., <code>C:\Gmsh\4.12.2\gmsh.exe</code>)</li>
                  <li><strong>ParaView:</strong> Executable file (e.g., <code>C:\ParaView\5.12.0\bin\paraview.exe</code>)</li>
                  <li><strong>Python:</strong> Executable file (e.g., <code>C:\Python311\python.exe</code>)</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'projects' && (
            <div className="settings-section">
              <h3>Project Default Settings</h3>
              <div className="settings-form">
                <div className="form-group">
                  <label>Default Solver</label>
                  <select value={projectSettings.defaultSolver} onChange={(e) => handleProjectSettingsChange('defaultSolver', e.target.value)}>
                    <option value="openfoam">OpenFOAM</option>
                    <option value="su2">SU2</option>
                    <option value="code_saturne">Code_Saturne</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Default Turbulence Model</label>
                  <select value={projectSettings.defaultTurbulenceModel} onChange={(e) => handleProjectSettingsChange('defaultTurbulenceModel', e.target.value)}>
                    <option value="kOmegaSST">k-ω SST</option>
                    <option value="kEpsilon">k-ε</option>
                    <option value="realizableKE">Realizable k-ε</option>
                    <option value="spalartAllmaras">Spalart-Allmaras</option>
                    <option value="laminar">Laminar</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Default Mesh Algorithm</label>
                  <select value={projectSettings.defaultMeshAlgorithm} onChange={(e) => handleProjectSettingsChange('defaultMeshAlgorithm', e.target.value)}>
                    <option value="delaunay3d">Delaunay 3D</option>
                    <option value="hxt">HXT (Hex-dominant)</option>
                    <option value="netgen">Netgen</option>
                    <option value="mmg">MMG</option>
                    <option value="boundaryLayer">Boundary Layer</option>
                  </select>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Auto-save Interval (seconds)</label>
                    <input
                      type="number"
                      value={projectSettings.autoSaveInterval}
                      onChange={(e) => handleProjectSettingsChange('autoSaveInterval', parseInt(e.target.value))}
                      min="60"
                      max="3600"
                    />
                  </div>
                  <div className="form-group">
                    <label>Max Concurrent Simulations</label>
                    <input
                      type="number"
                      value={projectSettings.maxConcurrentSimulations}
                      onChange={(e) => handleProjectSettingsChange('maxConcurrentSimulations', parseInt(e.target.value))}
                      min="1"
                      max="8"
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Default Output Format</label>
                  <select value={projectSettings.defaultOutputFormat} onChange={(e) => handleProjectSettingsChange('defaultOutputFormat', e.target.value)}>
                    <option value="vtk">VTK (Legacy)</option>
                    <option value="vtu">VTU (XML)</option>
                    <option value="foam">OpenFOAM Native</option>
                    <option value="cgns">CGNS</option>
                  </select>
                </div>
                <div className="form-actions">
                  <button className="btn btn-primary">Save Project Defaults</button>
                  <button className="btn btn-secondary">Reset to Defaults</button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'app' && (
            <div className="settings-section">
              <h3>Appearance & Behavior</h3>
              <div className="settings-form">
                <div className="form-group">
                  <label>Theme</label>
                  <select value={appSettings.theme} onChange={(e) => handleAppSettingsChange('theme', e.target.value as 'light' | 'dark' | 'system')}>
                    <option value="system">System Default</option>
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Language</label>
                  <select value={appSettings.language} onChange={(e) => handleAppSettingsChange('language', e.target.value)}>
                    <option value="en">English</option>
                    <option value="de">German</option>
                    <option value="fr">French</option>
                    <option value="es">Spanish</option>
                    <option value="ja">Japanese</option>
                    <option value="zh">Chinese</option>
                  </select>
                </div>
                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={appSettings.autoCheckUpdates}
                      onChange={(e) => handleAppSettingsChange('autoCheckUpdates', e.target.checked)}
                    />
                    Automatically check for updates
                  </label>
                </div>
                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={appSettings.telemetryEnabled}
                      onChange={(e) => handleAppSettingsChange('telemetryEnabled', e.target.checked)}
                    />
                    Send anonymous usage statistics
                  </label>
                </div>
                <div className="form-group">
                  <label>Log Level</label>
                  <select value={appSettings.logLevel} onChange={(e) => handleAppSettingsChange('logLevel', e.target.value as 'debug' | 'info' | 'warn' | 'error')}>
                    <option value="debug">Debug</option>
                    <option value="info">Info</option>
                    <option value="warn">Warning</option>
                    <option value="error">Error Only</option>
                  </select>
                </div>
                <div className="form-actions">
                  <button className="btn btn-primary">Save Appearance Settings</button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'license' && (
            <div className="settings-section">
              <h3>License Information</h3>
              <div className="license-card">
                <div className="license-header">
                  <div className="license-type">
                    <span className={`license-badge ${license.type}`}>{license.type.charAt(0).toUpperCase() + license.type.slice(1)}</span>
                    <span className={`license-status ${license.status}`}>{license.status.charAt(0).toUpperCase() + license.status.slice(1)}</span>
                  </div>
                  {license.expiresAt && (
                    <div className="license-expiry">
                      Expires: {new Date(license.expiresAt).toLocaleDateString()}
                    </div>
                  )}
                </div>
                <div className="license-features">
                  <h4>Included Features</h4>
                  <ul>
                    {license.features.map((feature, i) => (
                      <li key={i}>✓ {feature}</li>
                    ))}
                  </ul>
                </div>
                <div className="license-actions">
                  {license.type === 'community' && (
                    <button className="btn btn-primary">Upgrade License</button>
                  )}
                  {license.status === 'trial' && (
                    <button className="btn btn-secondary">Enter License Key</button>
                  )}
                  <button className="btn btn-secondary">View License Details</button>
                </div>
              </div>

              <div className="license-comparison">
                <h4>Feature Comparison</h4>
                <table>
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>Community</th>
                      <th>Professional</th>
                      <th>Enterprise</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr><td>Basic CFD Solvers</td><td>✓</td><td>✓</td><td>✓</td></tr>
                    <tr><td>Mesh Generation (Gmsh)</td><td>✓</td><td>✓</td><td>✓</td></tr>
                    <tr><td>Post-Processing (ParaView)</td><td>✓</td><td>✓</td><td>✓</td></tr>
                    <tr><td>Parallel Processing</td><td>2 cores</td><td>16 cores</td><td>Unlimited</td></tr>
                    <tr><td>Optimization Module</td><td>✗</td><td>✓</td><td>✓</td></tr>
                    <tr><td>Custom Solvers</td><td>✗</td><td>✓</td><td>✓</td></tr>
                    <tr><td>Cloud/HPC Integration</td><td>✗</td><td>✗</td><td>✓</td></tr>
                    <tr><td>Priority Support</td><td>✗</td><td>✓</td><td>✓</td></tr>
                    <tr><td>Source Code Access</td><td>✗</td><td>✗</td><td>✓</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'advanced' && (
            <div className="settings-section">
              <h3>Advanced Settings</h3>
              <div className="settings-form">
                <div className="form-group">
                  <label>Working Directory</label>
                  <input type="text" value="C:\\CFD\\Projects" readOnly />
                  <small>Change requires application restart</small>
                </div>
                <div className="form-group">
                  <label>Cache Directory</label>
                  <input type="text" value="C:\\CFD\\Cache" readOnly />
                </div>
                <div className="form-group">
                  <label>Log Directory</label>
                  <input type="text" value="C:\\CFD\\Logs" readOnly />
                </div>
                <div className="form-group checkbox-group">
                  <label>
                    <input type="checkbox" defaultChecked />
                    Enable GPU Acceleration (if available)
                  </label>
                </div>
                <div className="form-group checkbox-group">
                  <label>
                    <input type="checkbox" defaultChecked />
                    Use System Proxy Settings
                  </label>
                </div>
                <div className="form-group checkbox-group">
                  <label>
                    <input type="checkbox" />
                    Enable Experimental Features
                  </label>
                </div>
                <div className="form-group">
                  <label>Python Environment Path</label>
                  <input type="text" value="C:\\CFD\\venv" readOnly />
                  <small>Managed by the application</small>
                </div>
                <div className="form-actions">
                  <button className="btn btn-secondary">Open Config Folder</button>
                  <button className="btn btn-secondary">View Logs</button>
                  <button className="btn btn-danger">Reset All Settings</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {showAddSolverModal && (
        <div className="modal-overlay" onClick={() => setShowAddSolverModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Solver / Tool</h3>
              <button className="modal-close" onClick={() => setShowAddSolverModal(false)}>×</button>
            </div>
            <form onSubmit={handleAddSolver} className="modal-form">
              <div className="form-group">
                <label>Type</label>
                <select
                  value={newSolver.type}
                  onChange={(e) => setNewSolver({ ...newSolver, type: e.target.value as SolverConfig['type'] })}
                >
                  <option value="openfoam">OpenFOAM</option>
                  <option value="gmsh">Gmsh</option>
                  <option value="paraview">ParaView</option>
                  <option value="python">Python</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={newSolver.name}
                  onChange={(e) => setNewSolver({ ...newSolver, name: e.target.value })}
                  required
                  placeholder="e.g., OpenFOAM v11"
                />
              </div>
              <div className="form-group">
                <label>Path</label>
                <input
                  type="text"
                  value={newSolver.path}
                  onChange={(e) => setNewSolver({ ...newSolver, path: e.target.value })}
                  required
                  placeholder="e.g., C:\\OpenFOAM\\v11"
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddSolverModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Add Solver</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}