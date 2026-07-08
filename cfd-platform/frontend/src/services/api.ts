import { providerService } from './providerService'
import type { ChatOptions, ChatResponse } from '../types/provider'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, ...fetchOptions } = options
  
  let url = `${API_BASE_URL}${endpoint}`
  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      searchParams.append(key, String(value))
    })
    url += `?${searchParams.toString()}`
  }
  
  // No auth token needed - this is a local-first application
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  }
  
  const response = await fetch(url, { ...fetchOptions, headers })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }
  
  if (response.status === 204) {
    return undefined as T
  }
  
  return response.json()
}

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),
  
  post: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'POST', body: JSON.stringify(data) }),
  
  patch: <T>(endpoint: string, data: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PATCH', body: JSON.stringify(data) }),
  
  delete: (endpoint: string, options?: RequestOptions) =>
    request(endpoint, { ...options, method: 'DELETE' }),
}

// AI Provider integration
export const ai = {
  /**
   * Send a chat completion request to the configured AI provider
   */
  chat: async (options: ChatOptions): Promise<ChatResponse> => {
    return providerService.chat(options)
  },
  
  /**
   * Get the current active provider configuration
   */
  getActiveProvider: () => {
    return providerService.getActiveProvider()
  },
  
  /**
   * Test connection with the current provider
   */
  testConnection: () => {
    return providerService.testConnection(providerService.getActiveProvider()!)
  },
  
  /**
   * Get available models from the current provider
   */
  getModels: () => {
    return providerService.getModels(providerService.getActiveProvider()?.type || 'openai')
  },
}