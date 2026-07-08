import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import { ProviderType, PROVIDER_OPTIONS, ProviderConfig, ConnectionTestResult } from '../types/provider'
import { useProviderStore } from '../store/providerStore'
import { providerService } from '../services/providerService'

@customElement('setup-page')
export class SetupPage extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: #e4e4e7;
      padding: 2rem;
      box-sizing: border-box;
    }
    
    .container {
      width: 100%;
      max-width: 900px;
    }
    
    .header {
      text-align: center;
      margin-bottom: 3rem;
    }
    
    .logo {
      font-size: 3rem;
      margin-bottom: 1rem;
    }
    
    h1 {
      font-size: 2.5rem;
      font-weight: 700;
      margin: 0 0 0.5rem 0;
      background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    
    .subtitle {
      font-size: 1.125rem;
      color: #a1a1aa;
      margin: 0;
    }
    
    .provider-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }
    
    .provider-card {
      background: rgba(255, 255, 255, 0.05);
      border: 2px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 1.25rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    
    .provider-card:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(96, 165, 250, 0.5);
      transform: translateY(-2px);
    }
    
    .provider-card.selected {
      background: rgba(96, 165, 250, 0.15);
      border-color: #60a5fa;
    }
    
    .provider-card.local {
      border-color: rgba(52, 211, 153, 0.5);
    }
    
    .provider-card.local.selected {
      background: rgba(52, 211, 153, 0.15);
      border-color: #34d399;
    }
    
    .provider-icon {
      font-size: 2rem;
      margin-bottom: 0.75rem;
    }
    
    .provider-name {
      font-size: 1.125rem;
      font-weight: 600;
      margin: 0 0 0.25rem 0;
    }
    
    .provider-desc {
      font-size: 0.875rem;
      color: #a1a1aa;
      margin: 0;
    }
    
    .provider-badge {
      display: inline-block;
      font-size: 0.75rem;
      padding: 0.125rem 0.5rem;
      border-radius: 9999px;
      background: rgba(52, 211, 153, 0.2);
      color: #34d399;
      margin-top: 0.5rem;
    }
    
    .config-form {
      background: rgba(255, 255, 255, 0.05);
      border-radius: 16px;
      padding: 2rem;
      margin-top: 2rem;
    }
    
    .form-title {
      font-size: 1.5rem;
      font-weight: 600;
      margin: 0 0 1.5rem 0;
    }
    
    .form-group {
      margin-bottom: 1.5rem;
    }
    
    label {
      display: block;
      font-size: 0.875rem;
      font-weight: 500;
      color: #a1a1aa;
      margin-bottom: 0.5rem;
    }
    
    input, select {
      width: 100%;
      padding: 0.75rem 1rem;
      font-size: 1rem;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 8px;
      color: #e4e4e7;
      box-sizing: border-box;
      transition: border-color 0.2s ease;
    }
    
    input:focus, select:focus {
      outline: none;
      border-color: #60a5fa;
    }
    
    input::placeholder {
      color: #71717a;
    }
    
    .input-hint {
      font-size: 0.75rem;
      color: #71717a;
      margin-top: 0.25rem;
    }
    
    .input-error {
      font-size: 0.75rem;
      color: #f87171;
      margin-top: 0.25rem;
    }
    
    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 0.75rem 1.5rem;
      font-size: 1rem;
      font-weight: 500;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    
    .btn-primary {
      background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
      color: white;
    }
    
    .btn-primary:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(96, 165, 250, 0.4);
    }
    
    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }
    
    .btn-secondary {
      background: rgba(255, 255, 255, 0.1);
      color: #e4e4e7;
    }
    
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.15);
    }
    
    .btn-test {
      padding: 0.5rem 1rem;
      font-size: 0.875rem;
    }
    
    .btn-group {
      display: flex;
      gap: 1rem;
      margin-top: 1.5rem;
    }
    
    .status {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-size: 0.875rem;
      margin-top: 1rem;
    }
    
    .status.success {
      background: rgba(52, 211, 153, 0.15);
      color: #34d399;
    }
    
    .status.error {
      background: rgba(248, 113, 113, 0.15);
      color: #f87171;
    }
    
    .status.testing {
      background: rgba(96, 165, 250, 0.15);
      color: #60a5fa;
    }
    
    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid transparent;
      border-top-color: currentColor;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    
    .saved-providers {
      margin-top: 2rem;
      padding-top: 2rem;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .saved-title {
      font-size: 1rem;
      font-weight: 600;
      margin: 0 0 1rem 0;
      color: #a1a1aa;
    }
    
    .saved-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .saved-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;
    }
    
    .saved-item-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    
    .saved-item-name {
      font-weight: 500;
    }
    
    .saved-item-model {
      font-size: 0.875rem;
      color: #71717a;
    }
    
    .saved-item-actions {
      display: flex;
      gap: 0.5rem;
    }
    
    .btn-icon {
      padding: 0.5rem;
      background: transparent;
      border: none;
      color: #a1a1aa;
      cursor: pointer;
      border-radius: 4px;
      transition: all 0.2s ease;
    }
    
    .btn-icon:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #e4e4e7;
    }
    
    .btn-icon.danger:hover {
      background: rgba(248, 113, 113, 0.2);
      color: #f87171;
    }
    
    .skip-link {
      display: block;
      text-align: center;
      margin-top: 2rem;
      color: #71717a;
      text-decoration: none;
      font-size: 0.875rem;
    }
    
    .skip-link:hover {
      color: #a1a1aa;
    }
    
    .advanced-toggle {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: #71717a;
      cursor: pointer;
      margin-top: 1rem;
    }
    
    .advanced-toggle:hover {
      color: #a1a1aa;
    }
    
    .advanced-section {
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
    }
    
    .checkbox-label input {
      width: auto;
    }
  `
  
  @state()
  private selectedProvider: ProviderType | null = null
  
  @state()
  private apiKey: string = ''
  
  @state()
  private baseUrl: string = ''
  
  @state()
  private model: string = ''
  
  @state()
  private localEndpoint: string = ''
  
  @state()
  private isTesting: boolean = false
  
  @state()
  private testResult: ConnectionTestResult | null = null
  
  @state()
  private isSaving: boolean = false
  
  @state()
  private showAdvanced: boolean = false
  
  @state()
  private temperature: number = 0.7
  
  @state()
  private maxTokens: number = 4096
  
  @state()
  private timeout: number = 60000
  
  @state()
  private apiKeyError: string = ''
  
  private store = useProviderStore.getState()
  
  connectedCallback() {
    super.connectedCallback()
    // Subscribe to store changes
    useProviderStore.subscribe(() => {
      this.requestUpdate()
    })
  }
  
  private selectProvider(type: ProviderType) {
    this.selectedProvider = type
    this.testResult = null
    this.apiKeyError = ''
    
    const option = PROVIDER_OPTIONS.find(p => p.type === type)
    if (option) {
      this.baseUrl = option.defaultBaseUrl
      this.model = option.defaultModel || ''
      
      // Set local endpoint for local providers
      if (option.isLocal) {
        if (type === 'ollama') {
          this.localEndpoint = 'http://localhost:11434'
          this.baseUrl = 'http://localhost:11434'
        } else if (type === 'lmstudio') {
          this.localEndpoint = 'http://localhost:1234/v1'
          this.baseUrl = 'http://localhost:1234/v1'
        }
      }
    }
  }
  
  private validateApiKey() {
    if (!this.selectedProvider) return true
    
    const option = PROVIDER_OPTIONS.find(p => p.type === this.selectedProvider)
    if (!option?.requiresApiKey) return true
    
    if (!this.apiKey) {
      this.apiKeyError = 'API key is required for this provider'
      return false
    }
    
    if (!providerService.validateApiKey(this.selectedProvider, this.apiKey)) {
      this.apiKeyError = 'Invalid API key format'
      return false
    }
    
    this.apiKeyError = ''
    return true
  }
  
  private async testConnection() {
    if (!this.selectedProvider || !this.validateApiKey()) return
    
    this.isTesting = true
    this.testResult = null
    
    const config: ProviderConfig = {
      id: 'test',
      name: PROVIDER_OPTIONS.find(p => p.type === this.selectedProvider)?.name || '',
      type: this.selectedProvider,
      apiKey: this.apiKey || undefined,
      baseUrl: this.baseUrl,
      model: this.model,
      isDefault: false,
      enabled: true,
      settings: {
        temperature: this.temperature,
        maxTokens: this.maxTokens,
        timeout: this.timeout,
        localEndpoint: this.localEndpoint
      },
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    
    this.testResult = await providerService.testConnection(config)
    this.isTesting = false
  }
  
  private async saveProvider() {
    if (!this.selectedProvider || !this.validateApiKey()) return
    
    this.isSaving = true
    
    const option = PROVIDER_OPTIONS.find(p => p.type === this.selectedProvider)
    
    this.store.addProvider({
      name: option?.name || this.selectedProvider,
      type: this.selectedProvider,
      apiKey: this.apiKey || undefined,
      baseUrl: this.baseUrl,
      model: this.model,
      isDefault: this.store.providers.length === 0,
      enabled: true,
      settings: {
        temperature: this.temperature,
        maxTokens: this.maxTokens,
        timeout: this.timeout,
        localEndpoint: this.localEndpoint
      }
    })
    
    // Reset form
    this.selectedProvider = null
    this.apiKey = ''
    this.baseUrl = ''
    this.model = ''
    this.localEndpoint = ''
    this.testResult = null
    this.isSaving = false
  }
  
  private removeProvider(id: string) {
    this.store.removeProvider(id)
  }
  
  private setDefaultProvider(id: string) {
    this.store.setDefaultProvider(id)
  }
  
  private continueToApp() {
    this.store.completeSetup()
    // Navigate to main app - this will be handled by the router
    window.location.hash = '#/'
  }
  
  private renderProviderCard(option: typeof PROVIDER_OPTIONS[0]) {
    const isSelected = this.selectedProvider === option.type
    const isLocal = option.isLocal
    
    return html`
      <div 
        class="provider-card ${isSelected ? 'selected' : ''} ${isLocal ? 'local' : ''}"
        @click=${() => this.selectProvider(option.type)}
      >
        <div class="provider-icon">${this.getProviderIcon(option.type)}</div>
        <h3 class="provider-name">${option.name}</h3>
        <p class="provider-desc">${option.description}</p>
        ${isLocal ? html`<span class="provider-badge">Local</span>` : ''}
      </div>
    `
  }
  
  private getProviderIcon(type: ProviderType): string {
    const icons: Record<ProviderType, string> = {
      openai: '🤖',
      anthropic: '🧠',
      nvidia_nim: '🎮',
      openrouter: '🔀',
      ollama: '🦙',
      lmstudio: '💻',
      gemini: '✨',
      groq: '⚡',
      custom: '🔧'
    }
    return icons[type] || '🔗'
  }
  
  private renderConfigForm() {
    if (!this.selectedProvider) return null
    
    const option = PROVIDER_OPTIONS.find(p => p.type === this.selectedProvider)
    if (!option) return null
    
    return html`
      <div class="config-form">
        <h2 class="form-title">Configure ${option.name}</h2>
        
        ${option.requiresApiKey ? html`
          <div class="form-group">
            <label for="apiKey">API Key</label>
            <input 
              type="password" 
              id="apiKey" 
              .value=${this.apiKey}
              @input=${(e: Event) => { this.apiKey = (e.target as HTMLInputElement).value; this.validateApiKey() }}
              placeholder="Enter your API key"
            />
            ${this.apiKeyError ? html`<div class="input-error">${this.apiKeyError}</div>` : ''}
            <div class="input-hint">Your API key is stored securely on your local machine only</div>
          </div>
        ` : ''}
        
        <div class="form-group">
          <label for="baseUrl">API Base URL</label>
          <input 
            type="text" 
            id="baseUrl" 
            .value=${this.baseUrl}
            @input=${(e: Event) => this.baseUrl = (e.target as HTMLInputElement).value}
            placeholder=${option.defaultBaseUrl}
          />
          <div class="input-hint">The base URL for the API endpoint</div>
        </div>
        
        <div class="form-group">
          <label for="model">Model</label>
          <input 
            type="text" 
            id="model" 
            .value=${this.model}
            @input=${(e: Event) => this.model = (e.target as HTMLInputElement).value}
            placeholder=${option.defaultModel || 'e.g., gpt-4-turbo-preview'}
            list="model-suggestions"
          />
          ${option.models ? html`
            <datalist id="model-suggestions">
              ${option.models.map(m => html`<option value=${m}>`)}
            </datalist>
          ` : ''}
          <div class="input-hint">The model to use for completions</div>
        </div>
        
        <div class="advanced-toggle" @click=${() => this.showAdvanced = !this.showAdvanced}>
          ${this.showAdvanced ? '▼' : '▶'} Advanced Settings
        </div>
        
        ${this.showAdvanced ? html`
          <div class="advanced-section">
            <div class="form-row">
              <div class="form-group">
                <label for="temperature">Temperature (${this.temperature})</label>
                <input 
                  type="range" 
                  id="temperature" 
                  min="0" 
                  max="2" 
                  step="0.1"
                  .value=${String(this.temperature)}
                  @input=${(e: Event) => this.temperature = parseFloat((e.target as HTMLInputElement).value)}
                />
                <div class="input-hint">Lower = more focused, Higher = more creative</div>
              </div>
              
              <div class="form-group">
                <label for="maxTokens">Max Tokens</label>
                <input 
                  type="number" 
                  id="maxTokens" 
                  .value=${String(this.maxTokens)}
                  @input=${(e: Event) => this.maxTokens = parseInt((e.target as HTMLInputElement).value) || 4096}
                />
                <div class="input-hint">Maximum response length</div>
              </div>
            </div>
            
            <div class="form-group">
              <label for="timeout">Request Timeout (ms)</label>
              <input 
                type="number" 
                id="timeout" 
                .value=${String(this.timeout)}
                @input=${(e: Event) => this.timeout = parseInt((e.target as HTMLInputElement).value) || 60000}
              />
            </div>
          </div>
        ` : ''}
        
        <div class="btn-group">
          <button 
            class="btn btn-secondary btn-test" 
            @click=${this.testConnection}
            ?disabled=${this.isTesting}
          >
            ${this.isTesting ? html`<span class="spinner"></span> Testing...` : 'Test Connection'}
          </button>
        </div>
        
        ${this.testResult ? html`
          <div class="status ${this.testResult.success ? 'success' : 'error'}">
            ${this.testResult.success 
              ? html`✓ Connected successfully${this.testResult.latency ? ` (${this.testResult.latency}ms)` : ''}`
              : html`✗ ${this.testResult.error || 'Connection failed'}`
            }
          </div>
        ` : ''}
        
        <div class="btn-group">
          <button 
            class="btn btn-primary" 
            @click=${this.saveProvider}
            ?disabled=${this.isSaving || (option.requiresApiKey && !this.apiKey) || !this.model}
          >
            ${this.isSaving ? 'Saving...' : 'Save Provider'}
          </button>
          <button class="btn btn-secondary" @click=${() => { this.selectedProvider = null; this.testResult = null }}>
            Cancel
          </button>
        </div>
      </div>
    `
  }
  
  render() {
    const providers = this.store.providers
    const hasProviders = providers.length > 0
    
    return html`
      <div class="container">
        <div class="header">
          <div class="logo">🔬</div>
          <h1>CFD Platform</h1>
          <p class="subtitle">Configure your AI provider to get started</p>
        </div>
        
        ${!this.selectedProvider ? html`
          <div class="provider-grid">
            ${PROVIDER_OPTIONS.map(opt => this.renderProviderCard(opt))}
          </div>
          
          ${hasProviders ? html`
            <div class="saved-providers">
              <h3 class="saved-title">Saved Providers</h3>
              <div class="saved-list">
                ${providers.map(p => html`
                  <div class="saved-item">
                    <div class="saved-item-info">
                      <span>${this.getProviderIcon(p.type)}</span>
                      <div>
                        <div class="saved-item-name">${p.name} ${p.isDefault ? '(Default)' : ''}</div>
                        <div class="saved-item-model">${p.model}</div>
                      </div>
                    </div>
                    <div class="saved-item-actions">
                      ${!p.isDefault ? html`
                        <button class="btn-icon" @click=${() => this.setDefaultProvider(p.id)} title="Set as default">
                          ⭐
                        </button>
                      ` : ''}
                      <button class="btn-icon danger" @click=${() => this.removeProvider(p.id)} title="Remove">
                        🗑️
                      </button>
                    </div>
                  </div>
                `)}
              </div>
            </div>
          ` : ''}
          
          ${hasProviders ? html`
            <a class="skip-link" href="#" @click=${(e: Event) => { e.preventDefault(); this.continueToApp() }}>
              Continue to App →
            </a>
          ` : ''}
        ` : this.renderConfigForm()}
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'setup-page': SetupPage
  }
}