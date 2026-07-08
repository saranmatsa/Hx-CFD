/**
 * AI Provider Types and Interfaces
 * 
 * This module defines the types and interfaces for the modular AI provider system.
 * Providers can be added by implementing the AIProvider interface.
 */

export type ProviderType = 
  | 'openai' 
  | 'anthropic' 
  | 'nvidia_nim' 
  | 'openrouter' 
  | 'ollama' 
  | 'lmstudio' 
  | 'gemini' 
  | 'groq'
  | 'custom'

export interface ProviderConfig {
  id: string
  name: string
  type: ProviderType
  apiKey?: string
  baseUrl: string
  model: string
  isDefault: boolean
  enabled: boolean
  settings: ProviderSettings
  createdAt: number
  updatedAt: number
}

export interface ProviderSettings {
  maxTokens?: number
  temperature?: number
  topP?: number
  frequencyPenalty?: number
  presencePenalty?: number
  timeout?: number
  localEndpoint?: string // For local providers like Ollama, LM Studio
}

export interface ProviderOption {
  type: ProviderType
  name: string
  description: string
  defaultBaseUrl: string
  supportsStreaming: boolean
  isLocal: boolean
  requiresApiKey: boolean
  defaultModel?: string
  models?: string[]
}

export interface ConnectionTestResult {
  success: boolean
  latency?: number
  error?: string
  model?: string
  provider?: string
}

export interface AIProvider {
  type: ProviderType
  name: string
  
  /**
   * Test the connection to the provider
   */
  testConnection(config: ProviderConfig): Promise<ConnectionTestResult>
  
  /**
   * Send a chat completion request
   */
  chat(options: ChatOptions): Promise<ChatResponse>
  
  /**
   * Send a streaming chat completion request
   */
  chatStream(options: ChatOptions, onChunk: (chunk: string) => void): Promise<void>
  
  /**
   * List available models
   */
  listModels(config: ProviderConfig): Promise<string[]>
  
  /**
   * Validate API key format (basic validation, not server-side)
   */
  validateApiKey(apiKey: string): boolean
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface ChatOptions {
  messages: ChatMessage[]
  model?: string
  temperature?: number
  maxTokens?: number
  stream?: boolean
}

export interface ChatResponse {
  content: string
  model: string
  usage?: {
    promptTokens: number
    completionTokens: number
    totalTokens: number
  }
  finishReason?: 'stop' | 'length' | 'content_filter' | 'error'
  error?: string
}

export interface ProviderCapabilities {
  streaming: boolean
  functionCalling: boolean
  vision: boolean
  jsonMode: boolean
  maxContextLength: number
}

// Provider metadata for UI display
export const PROVIDER_OPTIONS: ProviderOption[] = [
  {
    type: 'openai',
    name: 'OpenAI',
    description: 'GPT-4, GPT-4 Turbo, GPT-3.5 Turbo',
    defaultBaseUrl: 'https://api.openai.com/v1',
    supportsStreaming: true,
    isLocal: false,
    requiresApiKey: true,
    defaultModel: 'gpt-4-turbo-preview',
    models: ['gpt-4-turbo-preview', 'gpt-4', 'gpt-4-32k', 'gpt-3.5-turbo', 'gpt-3.5-turbo-16k']
  },
  {
    type: 'anthropic',
    name: 'Anthropic',
    description: 'Claude 3 Opus, Sonnet, Haiku',
    defaultBaseUrl: 'https://api.anthropic.com/v1',
    supportsStreaming: true,
    isLocal: false,
    requiresApiKey: true,
    defaultModel: 'claude-3-sonnet-20240229',
    models: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']
  },
  {
    type: 'nvidia_nim',
    name: 'NVIDIA NIM',
    description: 'NVIDIA NIM Inference Microservices',
    defaultBaseUrl: 'https://integrate.api.nvidia.com/v1',
    supportsStreaming: true,
    isLocal: false,
    requiresApiKey: true,
    defaultModel: 'mistralai/mixtral-8x7b-instruct-v0.1'
  },
  {
    type: 'openrouter',
    name: 'OpenRouter',
    description: 'Access 100+ models through OpenRouter',
    defaultBaseUrl: 'https://openrouter.ai/api/v1',
    supportsStreaming: true,
    isLocal: false,
    requiresApiKey: true,
    defaultModel: 'anthropic/claude-3-haiku'
  },
  {
    type: 'ollama',
    name: 'Ollama',
    description: 'Local AI models (Llama, Mistral, etc.)',
    defaultBaseUrl: 'http://localhost:11434',
    supportsStreaming: true,
    isLocal: true,
    requiresApiKey: false,
    defaultModel: 'llama3',
    models: ['llama3', 'llama3:70b', 'mistral', 'mixtral', 'codellama', 'phi3', 'qwen2']
  },
  {
    type: 'lmstudio',
    name: 'LM Studio',
    description: 'Local AI models via LM Studio',
    defaultBaseUrl: 'http://localhost:1234/v1',
    supportsStreaming: true,
    isLocal: true,
    requiresApiKey: false,
    defaultModel: 'local-model'
  },
  {
    type: 'gemini',
    name: 'Google Gemini',
    description: 'Gemini Pro, Gemini Ultra',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    supportsStreaming: true,
    isLocal: false,
    requiresApiKey: true,
    defaultModel: 'gemini-1.5-pro'
  },
  {
    type: 'groq',
    name: 'Groq',
    description: 'Fast inference with Groq LPU',
    defaultBaseUrl: 'https://api.groq.com/openai/v1',
    supportsStreaming: true,
    isLocal: false,
    requiresApiKey: true,
    defaultModel: 'mixtral-8x7b-32768'
  },
  {
    type: 'custom',
    name: 'Custom Provider',
    description: 'Configure any OpenAI-compatible API',
    defaultBaseUrl: '',
    supportsStreaming: true,
    isLocal: false,
    requiresApiKey: true,
    defaultModel: ''
  }
]

export function getProviderOption(type: ProviderType): ProviderOption | undefined {
  return PROVIDER_OPTIONS.find(p => p.type === type)
}

export function isLocalProvider(type: ProviderType): boolean {
  const option = getProviderOption(type)
  return option?.isLocal ?? false
}