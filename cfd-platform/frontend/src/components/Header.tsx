import { useProviderStore } from '../store/providerStore'
import { Link } from 'react-router-dom'

export default function Header() {
  const { providers, activeProviderId } = useProviderStore()
  const activeProvider = providers.find(p => p.id === activeProviderId)

  return (
    <header className="bg-white shadow-sm z-10">
      <div className="flex items-center justify-between h-16 px-6">
        <div className="flex items-center">
          <h2 className="text-lg font-semibold text-gray-700">CFD Simulation Platform</h2>
        </div>
        <div className="flex items-center gap-4">
          {activeProvider && (
            <span className="text-sm text-gray-600">
              Provider: {activeProvider.name}
            </span>
          )}
          <Link
            to="/setup"
            className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
          >
            Settings
          </Link>
        </div>
      </div>
    </header>
  )
}