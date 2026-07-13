import { useState } from 'react'
import './App.css'
import { Dashboard } from './components/Dashboard'
import { ProjectsView } from './components/ProjectsView'
import { MeshesView } from './components/MeshesView'
import { SimulationsView } from './components/SimulationsView'
import { PostProcessingView } from './components/PostProcessingView'
import { SettingsView } from './components/SettingsView'

type View = 'dashboard' | 'projects' | 'meshes' | 'simulations' | 'post-processing' | 'settings'

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const navigation = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'projects', label: 'Projects', icon: '📁' },
    { id: 'meshes', label: 'Meshes', icon: '🔲' },
    { id: 'simulations', label: 'Simulations', icon: '⚙️' },
    { id: 'post-processing', label: 'Post-Processing', icon: '📈' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ]

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />
      case 'projects':
        return <ProjectsView />
      case 'meshes':
        return <MeshesView />
      case 'simulations':
        return <SimulationsView />
      case 'post-processing':
        return <PostProcessingView />
      case 'settings':
        return <SettingsView />
      default:
        return <Dashboard />
    }
  }

  return (
    <div className="app">
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h1>HX CFD</h1>
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>
        <nav className="sidebar-nav">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${currentView === item.id ? 'active' : ''}`}
              onClick={() => setCurrentView(item.id as View)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="version-info">
            <span>HX CFD v1.0.0</span>
            <span className="backend-status">Backend: Connected</span>
          </div>
        </div>
      </aside>
      <main className="main-content">
        <header className="main-header">
          <h2>{navigation.find(n => n.id === currentView)?.label}</h2>
          <div className="header-actions">
            <button className="btn btn-primary" onClick={() => setCurrentView('projects')}>
              + New Project
            </button>
          </div>
        </header>
        <div className="content-area">
          {renderView()}
        </div>
      </main>
    </div>
  )
}

export default App