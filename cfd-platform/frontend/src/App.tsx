import { Routes, Route, Navigate } from 'react-router-dom'
import { useProviderStore } from './store/providerStore'
import SetupPage from './pages/SetupPage'
import DashboardPage from './pages/DashboardPage'
import ProjectPage from './pages/ProjectPage'
import SimulationPage from './pages/SimulationPage'
import UploadPage from './pages/UploadPage'
import ResultsPage from './pages/ResultsPage'
import PipelinePage from './pages/PipelinePage'
import DependencyManagerPage from './pages/DependencyManagerPage'
import SettingsPage from './pages/SettingsPage'
import Layout from './components/Layout'

function SetupRoute({ children }: { children: React.ReactNode }) {
  const { providers, isSetupComplete } = useProviderStore()
  // Redirect to setup if no providers configured
  if (providers.length === 0) {
    return <Navigate to="/setup" />
  }
  return <>{children}</>
}

function RequireSetup({ children }: { children: React.ReactNode }) {
  const { providers } = useProviderStore()
  // Show setup if no providers, otherwise show children
  if (providers.length === 0) {
    return <Navigate to="/setup" />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/setup" element={<SetupPage />} />
      <Route
        path="/*"
        element={
          <RequireSetup>
            <Layout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/projects" element={<DashboardPage />} />
                <Route path="/projects/:projectId" element={<ProjectPage />} />
                <Route path="/simulations/:simulationId" element={<SimulationPage />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/results/:id" element={<ResultsPage />} />
                <Route path="/pipeline" element={<PipelinePage />} />
                <Route path="/dependencies" element={<DependencyManagerPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </Layout>
          </RequireSetup>
        }
      />
    </Routes>
  )
}
