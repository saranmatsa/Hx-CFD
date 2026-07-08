import { 
  ProviderConfig, 
  ProviderType, 
  ConnectionTestResult, 
  ChatOptions, 
  ChatResponse,
  PROVIDER_OPTIONS,
  isLocalProvider
} from '../types/provider'

/**
 * Provider Service
 * 
 * Manages AI provider connections and provides a unified interface
 * for interacting with different AI providers.
 */

class ProviderService {
  private static instance: ProviderService
  
  static getInstance(): ProviderService {
    if (!ProviderService.instance) {
      ProviderService.instance = new ProviderService()
    }
    return ProviderService.instance
  }
  
  /**
   * Test connection to a provider
   */
  async testConnection(config: ProviderConfig): Promise<ConnectionTestResult> {
    const startTime = Date.now()
    
    try {
      // For local providers, check if the server is running
      if (isLocalProvider(config.type)) {
        return await this.testLocalProvider(config, startTime)
      }
      
      // For cloud providers, make a simple API call
      return await this.testCloudProvider(config, startTime)
    } catch (error) {
      return {
        success: false,
        latency: Date.now() - startTime,
        error: error instanceof Error ? error.message : 'Connection failed'
      }
    }
  }
  
  private async testLocalProvider(config: ProviderConfig, startTime: number): Promise<ConnectionTestResult> {
    const baseUrl = config.baseUrl || config.settings.localEndpoint || 'http://localhost:11434'
    
    try {
      // Try to get models list (works for both Ollama and LM Studio)
      const response = await fetch(`${baseUrl}/api/tags`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(config.settings.timeout || 5000)
      })
      
      if (response.ok) {
        const data = await response.json()
        const models = data.models?.map((m: any) => m.name) || []
        
        return {
          success: true,
          latency: Date.now() - startTime,
          model: models[0] || config.model,
          provider: config.name
        }
      }
      
      // Try OpenAI-compatible endpoint
      const chatResponse = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: config.model,
          messages: [{ role: 'user', content: 'ping' }],
          max_tokens: 1
        }),
        signal: AbortSignal.timeout(config.settings.timeout || 5000)
      })
      
      return {
        success: chatResponse.ok,
        latency: Date.now() - startTime,
        error: chatResponse.ok ? undefined : `HTTP ${chatResponse.status}`,
        model: config.model,
        provider: config.name
      }
    } catch (error) {
      return {
        success: false,
        latency: Date.now() - startTime,
        error: error instanceof Error ? error.message : 'Connection failed'
      }
    }
  }
  
  private async testCloudProvider(config: ProviderConfig, startTime: number): Promise<ConnectionTestResult> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    
    // Add API key to headers based on provider type
    if (config.apiKey) {
      headers['Authorization'] = `Bearer ${config.apiKey}`
    }
    
    // Provider-specific headers
    if (config.type === 'anthropic') {
      headers['x-api-key'] = config.apiKey || ''
      headers['anthropic-version'] = '2023-06-01'
    }
    
    if (config.type === 'gemini') {
      // Gemini uses a different API structure
      const apiKey = config.apiKey || ''
      const response = await fetch(
        `${config.baseUrl}/models?key=${apiKey}`,
        {
          method: 'GET',
          signal: AbortSignal.timeout(config.settings.timeout || 10000)
        }
      )
      
      return {
        success: response.ok,
        latency: Date.now() - startTime,
        error: response.ok ? undefined : `HTTP ${response.status}`,
        provider: config.name
      }
    }
    
    // Standard OpenAI-compatible API test
    const response = await fetch(`${config.baseUrl}/models`, {
      method: 'GET',
      headers,
      signal: AbortSignal.timeout(config.settings.timeout || 10000)
    })
    
    if (response.ok) {
      const data = await response.json()
      const models = data.data?.map((m: any) => m.id) || []
      
      return {
        success: true,
        latency: Date.now() - startTime,
        model: models.includes(config.model) ? config.model : models[0],
        provider: config.name
      }
    }
    
    // Try a simple chat completion as fallback
    const chatResponse = await fetch(`${config.baseUrl}/chat/completions`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: config.model,
        messages: [{ role: 'user', content: 'test' }],
        max_tokens: 1
      }),
      signal: AbortSignal.timeout(config.settings.timeout || 10000)
    })
    
    return {
      success: chatResponse.ok,
      latency: Date.now() - startTime,
      error: chatResponse.ok ? undefined : `HTTP ${chatResponse.status}`,
      model: config.model,
      provider: config.name
    }
  }
  
  /**
   * Send a chat completion request
   */
  async chat(config: ProviderConfig, options: ChatOptions): Promise<ChatResponse> {
    const model = options.model || config.model
    
    try {
      // Handle different provider APIs
      if (config.type === 'anthropic') {
        return await this.chatAnthropic(config, options)
      }
      
      if (config.type === 'gemini') {
        return await this.chatGemini(config, options)
      }
      
      // Default: OpenAI-compatible API
      return await this.chatOpenAICompatible(config, options)
    } catch (error) {
      return {
        content: '',
        model,
        error: error instanceof Error ? error.message : 'Request failed'
      }
    }
  }
  
  private async chatOpenAICompatible(config: ProviderConfig, options: ChatOptions): Promise<ChatResponse> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${config.apiKey || ''}`
    }
    
    const response = await fetch(`${config.baseUrl}/chat/completions`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: options.model || config.model,
        messages: options.messages,
        temperature: options.temperature ?? config.settings.temperature ?? 0.7,
        max_tokens: options.maxTokens ?? config.settings.maxTokens ?? 4096
      }),
      signal: AbortSignal.timeout(config.settings.timeout || 60000)
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error?.message || `HTTP ${response.status}`)
    }
    
    const data = await response.json()
    
    return {
      content: data.choices?.[0]?.message?.content || '',
      model: data.model || config.model,
      usage: data.usage ? {
        promptTokens: data.usage.prompt_tokens,
        completionTokens: data.usage.completion_tokens,
        totalTokens: data.usage.total_tokens
      } : undefined,
      finishReason: data.choices?.[0]?.finish_reason
    }
  }
  
  private async chatAnthropic(config: ProviderConfig, options: ChatOptions): Promise<ChatResponse> {
    // Convert messages to Anthropic format
    const systemMessage = options.messages.find(m => m.role === 'system')
    const chatMessages = options.messages.filter(m => m.role !== 'system')
    
    const response = await fetch(`${config.baseUrl}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': config.apiKey || '',
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true'
      },
      body: JSON.stringify({
        model: options.model || config.model,
        messages: chatMessages.map(m => ({
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.content
        })),
        system: systemMessage?.content,
        max_tokens: options.maxTokens ?? config.settings.maxTokens ?? 4096,
        temperature: options.temperature ?? config.settings.temperature ?? 1.0
      }),
      signal: AbortSignal.timeout(config.settings.timeout || 60000)
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error?.message || `HTTP ${response.status}`)
    }
    
    const data = await response.json()
    
    return {
      content: data.content?.[0]?.text || '',
      model: data.model || config.model,
      usage: data.usage ? {
        promptTokens: data.usage.input_tokens,
        completionTokens: data.usage.output_tokens,
        totalTokens: data.usage.input_tokens + data.usage.output_tokens
      } : undefined,
      finishReason: data.stop_reason
    }
  }
  
  private async chatGemini(config: ProviderConfig, options: ChatOptions): Promise<ChatResponse> {
    const apiKey = config.apiKey || ''
    const model = (options.model || config.model).replace('gemini-', '')
    
    // Convert messages to Gemini format
    const contents = options.messages.map(m => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }]
    }))
    
    const response = await fetch(
      `${config.baseUrl}/models/${options.model || config.model}:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents,
          generationConfig: {
            temperature: options.temperature ?? config.settings.temperature ?? 0.9,
            maxOutputTokens: options.maxTokens ?? config.settings.maxTokens ?? 2048
          }
        }),
        signal: AbortSignal.timeout(config.settings.timeout || 60000)
      }
    )
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error?.message || `HTTP ${response.status}`)
    }
    
    const data = await response.json()
    
    return {
      content: data.candidates?.[0]?.content?.parts?.[0]?.text || '',
      model: config.model,
      usage: data.usageMetadata ? {
        promptTokens: data.usageMetadata.promptTokenCount,
        completionTokens: data.usageMetadata.candidatesTokenCount,
        totalTokens: data.usageMetadata.totalTokenCount
      } : undefined
    }
  }
  
  /**
   * Send a streaming chat completion request
   */
  async chatStream(
    config: ProviderConfig, 
    options: ChatOptions, 
    onChunk: (chunk: string) => void
  ): Promise<void> {
    const model = options.model || config.model
    
    // Handle different provider streaming APIs
    if (config.type === 'anthropic') {
      await this.chatStreamAnthropic(config, options, onChunk)
      return
    }
    
    if (config.type === 'gemini') {
      await this.chatStreamGemini(config, options, onChunk)
      return
    }
    
    // Default: OpenAI-compatible streaming
    await this.chatStreamOpenAI(config, options, onChunk)
  }
  
  private async chatStreamOpenAI(
    config: ProviderConfig, 
    options: ChatOptions, 
    onChunk: (chunk: string) => void
  ): Promise<void> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${config.apiKey || ''}`
    }
    
    const response = await fetch(`${config.baseUrl}/chat/completions`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: options.model || config.model,
        messages: options.messages,
        temperature: options.temperature ?? config.settings.temperature ?? 0.7,
        max_tokens: options.maxTokens ?? config.settings.maxTokens ?? 4096,
        stream: true
      }),
      signal: AbortSignal.timeout(config.settings.timeout || 120000)
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error?.message || `HTTP ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')
    
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') return
          
          try {
            const parsed = JSON.parse(data)
            const content = parsed.choices?.[0]?.delta?.content
            if (content) onChunk(content)
          } catch {
            // Ignore parse errors for incomplete chunks
          }
        }
      }
    }
  }
  
  private async chatStreamAnthropic(
    config: ProviderConfig, 
    options: ChatOptions, 
    onChunk: (chunk: string) => void
  ): Promise<void> {
    const systemMessage = options.messages.find(m => m.role === 'system')
    const chatMessages = options.messages.filter(m => m.role !== 'system')
    
    const response = await fetch(`${config.baseUrl}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': config.apiKey || '',
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true',
        'anthropic-streaming': 'true'
      },
      body: JSON.stringify({
        model: options.model || config.model,
        messages: chatMessages.map(m => ({
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.content
        })),
        system: systemMessage?.content,
        max_tokens: options.maxTokens ?? config.settings.maxTokens ?? 4096,
        temperature: options.temperature ?? config.settings.temperature ?? 1.0,
        stream: true
      }),
      signal: AbortSignal.timeout(config.settings.timeout || 120000)
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error?.message || `HTTP ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')
    
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          try {
            const parsed = JSON.parse(data)
            const content = parsed.delta?.text
            if (content) onChunk(content)
            if (parsed.type === 'message_stop') return
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  }
  
  private async chatStreamGemini(
    config: ProviderConfig, 
    options: ChatOptions, 
    onChunk: (chunk: string) => void
  ): Promise<void> {
    const apiKey = config.apiKey || ''
    
    const contents = options.messages.map(m => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }]
    }))
    
    const response = await fetch(
      `${config.baseUrl}/${options.model || config.model}:streamGenerateContent?key=${apiKey}&alt=sse`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents,
          generationConfig: {
            temperature: options.temperature ?? config.settings.temperature ?? 0.9,
            maxOutputTokens: options.maxTokens ?? config.settings.maxTokens ?? 2048
          }
        }),
        signal: AbortSignal.timeout(config.settings.timeout || 120000)
      }
    )
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')
    
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          try {
            const parsed = JSON.parse(data)
            const content = parsed.candidates?.[0]?.content?.parts?.[0]?.text
            if (content) onChunk(content)
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  }
  
  /**
   * List available models for a provider
   */
  async listModels(config: ProviderConfig): Promise<string[]> {
    try {
      // Local providers
      if (isLocalProvider(config.type)) {
        const baseUrl = config.baseUrl || config.settings.localEndpoint || 'http://localhost:11434'
        
        // Try Ollama format
        const ollamaResponse = await fetch(`${baseUrl}/api/tags`, {
          signal: AbortSignal.timeout(5000)
        })
        
        if (ollamaResponse.ok) {
          const data = await ollamaResponse.json()
          return data.models?.map((m: any) => m.name) || []
        }
        
        // Try OpenAI-compatible format
        const openaiResponse = await fetch(`${baseUrl}/models`, {
          headers: { 'Authorization': `Bearer ${config.apiKey || ''}` },
          signal: AbortSignal.timeout(5000)
        })
        
        if (openaiResponse.ok) {
          const data = await openaiResponse.json()
          return data.data?.map((m: any) => m.id) || []
        }
        
        return [config.model]
      }
      
      // Cloud providers
      if (config.type === 'gemini') {
        const apiKey = config.apiKey || ''
        const response = await fetch(
          `${config.baseUrl}/models?key=${apiKey}`,
          { signal: AbortSignal.timeout(10000) }
        )
        
        if (response.ok) {
          const data = await response.json()
          return data.models?.map((m: any) => m.name) || []
        }
        return []
      }
      
      // Standard OpenAI-compatible
      const response = await fetch(`${config.baseUrl}/models`, {
        headers: { 'Authorization': `Bearer ${config.apiKey || ''}` },
        signal: AbortSignal.timeout(10000)
      })
      
      if (response.ok) {
        const data = await response.json()
        return data.data?.map((m: any) => m.id) || []
      }
      
      return []
    } catch {
      return []
    }
  }
  
  /**
   * Validate API key format (basic validation)
   */
  validateApiKey(type: ProviderType, apiKey: string): boolean {
    if (!apiKey) return false
    
    switch (type) {
      case 'openai':
        return apiKey.startsWith('sk-') && apiKey.length > 20
      case 'anthropic':
        return apiKey.startsWith('sk-ant-') && apiKey.length > 50
      case 'nvidia_nim':
        return apiKey.length > 20
      case 'openrouter':
        return apiKey.length > 20
      case 'gemini':
        return apiKey.length > 20
      case 'groq':
        return apiKey.length > 20
      case 'ollama':
      case 'lmstudio':
        return true // No API key needed for local
      case 'custom':
        return apiKey.length > 10
      default:
        return apiKey.length > 10
    }
  }
  
  /**
   * Get provider option metadata
   */
  getProviderOption(type: ProviderType) {
    return PROVIDER_OPTIONS.find(p => p.type === type)
  }
  
  /**
   * Check if provider requires API key
   */
  requiresApiKey(type: ProviderType): boolean {
    const option = this.getProviderOption(type)
    return option?.requiresApiKey ?? true
  }
  
  /**
   * Check if provider is local
   */
  isLocalProvider(type: ProviderType): boolean {
    return isLocalProvider(type)
  }
}

export const providerService = ProviderService.getInstance()