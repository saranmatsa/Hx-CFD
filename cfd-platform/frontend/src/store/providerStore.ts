import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { ProviderConfig, ProviderType, ProviderSettings } from '../types/provider'

interface ProviderState {
  // All configured providers
  providers: ProviderConfig[]
  
  // Currently active provider ID
  activeProviderId: string | null
  
  // Whether setup has been completed
  isSetupComplete: boolean
  
  // Actions
  addProvider: (provider: Omit<ProviderConfig, 'id' | 'createdAt' | 'updatedAt'>) => string
  updateProvider: (id: string, updates: Partial<ProviderConfig>) => void
  removeProvider: (id: string) => void
  setActiveProvider: (id: string) => void
  setDefaultProvider: (id: string) => void
  toggleProvider: (id: string) => void
  getActiveProvider: () => ProviderConfig | null
  getProviderById: (id: string) => ProviderConfig | undefined
  getDefaultProvider: () => ProviderConfig | null
  completeSetup: () => void
  resetSetup: () => void
  reorderProviders: (fromIndex: number, toIndex: number) => void
}

function generateId(): string {
  return `provider_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

function encryptData(data: string, key: string): string {
  // Simple XOR encryption for local storage
  // In production, use Web Crypto API for proper encryption
  const encrypted = btoa(data.split('').map((char, i) => 
    String.fromCharCode(char.charCodeAt(0) ^ key.charCodeAt(i % key.length.length))
  ).join(''))
  return encrypted
}

function decryptData(encrypted: string, key: string): string {
  try {
    const decrypted = atob(encrypted).split('').map((char, i) => 
      String.fromCharCode(char.charCodeAt(0) ^ key.charCodeAt(i % key.length.length))
    ).join('')
    return decrypted
  } catch {
    return encrypted // Fallback for unencrypted data
  }
}

// Secure storage adapter for sensitive data
const secureStorage = {
  getItem: (name: string): string | null => {
    const value = localStorage.getItem(name)
    if (!value) return null
    
    // Try to decrypt with machine-specific key
    const machineKey = getMachineKey()
    try {
      return decryptData(value, machineKey)
    } catch {
      return value // Return as-is if decryption fails
    }
  },
  setItem: (name: string, value: string): void => {
    const machineKey = getMachineKey()
    const encrypted = encryptData(value, machineKey)
    localStorage.setItem(name, encrypted)
  },
  removeItem: (name: string): void => {
    localStorage.removeItem(name)
  }
}

function getMachineKey(): string {
  // Generate a machine-specific key based on available browser info
  const keySource = [
    navigator.userAgent,
    screen.width,
    screen.height,
    screen.colorDepth,
    new Date().getTimezoneOffset()
  ].join('|')
  
  // Simple hash function
  let hash = 0
  for (let i = 0; i < keySource.length; i++) {
    const char = keySource.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  return Math.abs(hash).toString(36)
}

export const useProviderStore = create<ProviderState>()(
  persist(
    (set, get) => ({
      providers: [],
      activeProviderId: null,
      isSetupComplete: false,
      
      addProvider: (providerData) => {
        const id = generateId()
        const now = Date.now()
        const newProvider: ProviderConfig = {
          ...providerData,
          id,
          createdAt: now,
          updatedAt: now
        }
        
        set((state) => {
          // If this is the first provider or marked as default, set as active
          const shouldBeActive = state.providers.length === 0 || providerData.isDefault
          const shouldBeSetupComplete = state.isSetupComplete || providerData.isDefault
          
          return {
            providers: [...state.providers, newProvider],
            activeProviderId: shouldBeActive ? id : state.activeProviderId,
            isSetupComplete: shouldBeSetupComplete
          }
        })
        
        return id
      },
      
      updateProvider: (id, updates) => {
        set((state) => ({
          providers: state.providers.map(p => 
            p.id === id 
              ? { ...p, ...updates, updatedAt: Date.now() }
              : p
          )
        }))
      },
      
      removeProvider: (id) => {
        set((state) => {
          const newProviders = state.providers.filter(p => p.id !== id)
          const wasActive = state.activeProviderId === id
          
          return {
            providers: newProviders,
            activeProviderId: wasActive 
              ? (newProviders[0]?.id ?? null) 
              : state.activeProviderId,
            isSetupComplete: newProviders.length > 0 ? state.isSetupComplete : false
          }
        })
      },
      
      setActiveProvider: (id) => {
        set({ activeProviderId: id })
      },
      
      setDefaultProvider: (id) => {
        set((state) => ({
          providers: state.providers.map(p => ({
            ...p,
            isDefault: p.id === id
          }))
        }))
      },
      
      toggleProvider: (id) => {
        set((state) => ({
          providers: state.providers.map(p => 
            p.id === id ? { ...p, enabled: !p.enabled } : p
          )
        }))
      },
      
      getActiveProvider: () => {
        const state = get()
        if (!state.activeProviderId) return null
        return state.providers.find(p => p.id === state.activeProviderId) ?? null
      },
      
      getProviderById: (id) => {
        return get().providers.find(p => p.id === id)
      },
      
      getDefaultProvider: () => {
        return get().providers.find(p => p.isDefault) ?? get().providers[0] ?? null
      },
      
      completeSetup: () => {
        set({ isSetupComplete: true })
      },
      
      resetSetup: () => {
        set({ 
          isSetupComplete: false,
          activeProviderId: null
        })
      },
      
      reorderProviders: (fromIndex, toIndex) => {
        set((state) => {
          const newProviders = [...state.providers]
          const [removed] = newProviders.splice(fromIndex, 1)
          newProviders.splice(toIndex, 0, removed)
          return { providers: newProviders }
        })
      }
    }),
    {
      name: 'provider-storage',
      storage: createJSONStorage(() => secureStorage),
      partialize: (state) => ({
        providers: state.providers,
        activeProviderId: state.activeProviderId,
        isSetupComplete: state.isSetupComplete
      })
    }
  )
)

// Selector hooks for common patterns
export const useActiveProvider = () => useProviderStore(state => state.getActiveProvider())
export const useProviders = () => useProviderStore(state => state.providers)
export const useIsSetupComplete = () => useProviderStore(state => state.isSetupComplete)