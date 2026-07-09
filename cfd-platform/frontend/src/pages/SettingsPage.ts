import { LitElement, html, css } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { ProviderType, PROVIDER_OPTIONS, ProviderConfig } from '../types/provider'
import { useProviderStore } from '../store/providerStore'
import { providerService } from '../services/providerService'

@customElement('settings-page')
export class SettingsPage extends LitElement {
  static styles = css`
    :host {
      display: block;
      padding: 2rem;
    }
    
    .container {
      max-width: 1000px;
      margin: 0 auto;
    }
    
    h1 {
      font-size: 2rem;
      font-weight: 700;
      margin-bottom: 2rem;
      color: #1f2937;
    }
    
    .section {
      background: white;
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 2rem;
      border: 1px solid #e5e7eb;
    }
    
    .section-title {
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 1.5rem;
      color: #111827;
      border-bottom: 2px solid #f3f4f6;
      padding-bottom: 0.75rem;
    }
    
    .provider-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    
    .provider-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem;
      background: #f9fafb;
      border-radius: 8px;
      border: 1px solid #e5e7eb;
    }
    
    .provider-info {
      display: flex;
      align-items: center;
      gap: 1rem;
      flex: 1;
    }
    
    .provider-icon {
      font-size: 1.5rem;
    }
    
    .provider-details {
      display: flex;
      flex-direction: column;
    }
    
    .provider-name {
      font-weight: 600;
      color: #111827;
    }
    
    .provider-model {
      font-size: 0.875rem;
      color: #6b7280;
    }
    
    .provider-actions {
      display: flex;
      gap: 0.5rem;
    }
    
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.875rem;
      font-weight: 500;
      transition: all 0.2s;
    }
    
    .btn-primary {
      background: #3b82f6;
      color: white;
    }
    
    .btn-primary:hover {
      background: #2563eb;
    }
    
    .btn-secondary {
      background: #e5e7eb;
      color: #374151;
    }
    
    .btn-secondary:hover {
      background: #d1d5db;
    }
    
    .btn-danger {
      background: #ef4444;
      color: white;
    }
    
    .btn-danger:hover {
      background: #dc2626;
    }
    
    .btn-sm {
      padding: 0.375rem 0.75rem;
      font-size: 0.75rem;
    }
    
    .form-group {
      margin-bottom: 1.5rem;
    }
    
    label {
      display: block;
      font-weight: 500;
      margin-bottom: 0.5rem;
      color: #374151;
      font-size: 0.875rem;
    }
    
    input, select, textarea {
      width: 100%;
      padding: 0.5rem;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 0.875rem;
      box-sizing: border-box;
    }
    
    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .form-hint {
      font-size: 0.75rem;
      color: #6b7280;
      margin-top: 0.25rem;
    }
    
    .form-error {
      font-size: 0.75rem;
      color: #ef4444;
      margin-top: 0.25rem;
    }
    
    .form-success {
      font-size: 0.75rem;
      color: #10b981;
      margin-top: 0.25rem;
    }
    
    .modal {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 1000;
      align-items: center;
      justify-content: center;
    }
    
    .modal.open {
      display: flex;
    }
    
    .modal-content {
      background: white;
      border-radius: 12px;
      padding: 2rem;
      max-width: 500px;
      width: 90%;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }
    
    .modal-title {
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: #111827;
    }
    
    .modal-actions {
      display: flex;
      gap: 0.5rem;
      justify-content: flex-end;
      margin-top: 1.5rem;
    }
    
    .badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      background: #dbeafe;
      color: #0c4a6e;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 500;
    }
    
    .badge.default {
      background: #fcd34d;
      color: #78350f;
    }
    
    .empty-state {
      text-align: center;
      padding: 3rem 1rem;
      color: #6b7280;
    }
    
    .empty-icon {
      font-size: 3rem;
      margin-bottom: 1rem;
    }
    
    .divider {
      height: 1px;
      background: #e5e7eb;
      margin: 2rem 0;
    }
  `
  
  @state()
  private showModal = false
  
  @state()
  private editingProvider: string | null = null
  
  @state()
  private formState = {
    name: '',
    type: 'openai' as ProviderType,
    apiKey: '',
    baseUrl: '',
    model: '',
    temperature: 0.7,
    maxTokens: 4096
  }
  
  @state()
  private validationErrors: Record<string, string> = {}
  
  @state()
  private testingConnection = false
  
  @state()
  private testResult: string = ''
  
  private store = useProviderStore.getState()
  
  connectedCallback() {
    super.connectedCallback()
    useProviderStore.subscribe(() => {
      this.requestUpdate()
    })
  }
  
  private openModal(providerId?: string) {
    if (providerId) {
      const provider = this.store.getProviderById(providerId)
      if (provider) {
        this.formState = {
          name: provider.name,
          type: provider.type,
          apiKey: provider.apiKey || '',
          baseUrl: provider.baseUrl,
          model: provider.model,
          temperature: provider.settings?.temperature || 0.7,
          maxTokens: provider.settings?.maxTokens || 4096
        }
        this.editingProvider = providerId
      }
    } else {
      this.formState = {
        name: '',
        type: 'openai',
        apiKey: '',
        baseUrl: '',
        model: '',
        temperature: 0.7,
        maxTokens: 4096
      }
      this.editingProvider = null
    }
    this.showModal = true
    this.validationErrors = {}
    this.testResult = ''
  }
  
  private closeModal() {
    this.showModal = false
    this.editingProvider = null
  }
  
  private validate(): boolean {
    const errors: Record<string, string> = {}
    
    if (!this.formState.name.trim()) {
      errors.name = 'Provider name is required'
    }
    if (!this.formState.apiKey.trim()) {
      errors.apiKey = 'API key is required'
    }
    if (!this.formState.model.trim()) {
      errors.model = 'Model is required'
    }
    if (!this.formState.baseUrl.trim()) {
      errors.baseUrl = 'Base URL is required'
    }
    
    this.validationErrors = errors
    return Object.keys(errors).length === 0
  }
  
  private async testConnection() {
    if (!this.validate()) return
    
    this.testingConnection = true
    const config: ProviderConfig = {
      id: this.editingProvider || 'test',
      name: this.formState.name,
      type: this.formState.type,
      apiKey: this.formState.apiKey,
      baseUrl: this.formState.baseUrl,
      model: this.formState.model,
      isDefault: false,
      enabled: true,
      settings: {
        temperature: this.formState.temperature,
        maxTokens: this.formState.maxTokens
      },
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    
    const result = await providerService.testConnection(config)
    this.testResult = result.success 
      ? `✓ Connected (${result.latency}ms)`
      : `✗ ${result.error || 'Connection failed'}`
    this.testingConnection = false
  }
  
  private saveProvider() {
    if (!this.validate()) return
    
    if (this.editingProvider) {
      this.store.updateProvider(this.editingProvider, {
        name: this.formState.name,
        apiKey: this.formState.apiKey,
        baseUrl: this.formState.baseUrl,
        model: this.formState.model,
        settings: {
          temperature: this.formState.temperature,
          maxTokens: this.formState.maxTokens
        }
      })
    } else {
      this.store.addProvider({
        name: this.formState.name,
        type: this.formState.type,
        apiKey: this.formState.apiKey,
        baseUrl: this.formState.baseUrl,
        model: this.formState.model,
        isDefault: this.store.providers.length === 0,
        enabled: true,
        settings: {
          temperature: this.formState.temperature,
          maxTokens: this.formState.maxTokens
        }
      })
    }
    
    this.closeModal()
  }
  
  private deleteProvider(id: string) {
    if (confirm('Are you sure you want to delete this provider?')) {
      this.store.removeProvider(id)
    }
  }
  
  private setDefault(id: string) {
    this.store.setDefaultProvider(id)
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
  
  render() {
    const providers = this.store.providers
    
    return html`
      <div class="container">
        <h1>⚙️ Settings</h1>
        
        <div class="section">
          <div class="section-title">
            AI Providers
            <button class="btn btn-primary" style="float: right;" @click=${() => this.openModal()}>
              + Add Provider
            </button>
          </div>
          
          ${providers.length === 0 ? html`
            <div class="empty-state">
              <div class="empty-icon">🔌</div>
              <p>No providers configured yet</p>
              <p style="font-size: 0.875rem;">Add an AI provider to get started</p>
            </div>
          ` : html`
            <div class="provider-list">
              ${providers.map(p => html`
                <div class="provider-item">
                  <div class="provider-info">
                    <div class="provider-icon">${this.getProviderIcon(p.type)}</div>
                    <div class="provider-details">
                      <div class="provider-name">
                        ${p.name}
                        ${p.isDefault ? html`<span class="badge default">Default</span>` : ''}
                      </div>
                      <div class="provider-model">${p.type} • ${p.model}</div>
                    </div>
                  </div>
                  <div class="provider-actions">
                    ${!p.isDefault ? html`
                      <button class="btn btn-secondary btn-sm" @click=${() => this.setDefault(p.id)}>
                        Set Default
                      </button>
                    ` : ''}
                    <button class="btn btn-secondary btn-sm" @click=${() => this.openModal(p.id)}>
                      Edit
                    </button>
                    <button class="btn btn-danger btn-sm" @click=${() => this.deleteProvider(p.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              `)}
            </div>
          `}
        </div>
        
        <div class="modal ${this.showModal ? 'open' : ''}">
          <div class="modal-content">
            <h2 class="modal-title">
              ${this.editingProvider ? 'Edit Provider' : 'Add New Provider'}
            </h2>
            
            <div class="form-group">
              <label>Name</label>
              <input 
                type="text" 
                .value=${this.formState.name}
                @input=${(e: Event) => this.formState.name = (e.target as HTMLInputElement).value}
                placeholder="e.g., My OpenAI Account"
              />
              ${this.validationErrors.name ? html`<div class="form-error">${this.validationErrors.name}</div>` : ''}
            </div>
            
            ${!this.editingProvider ? html`
              <div class="form-group">
                <label>Provider Type</label>
                <select 
                  .value=${this.formState.type}
                  @input=${(e: Event) => this.formState.type = (e.target as HTMLSelectElement).value as ProviderType}
                >
                  ${PROVIDER_OPTIONS.map(opt => html`
                    <option value=${opt.type}>${opt.name}</option>
                  `)}
                </select>
              </div>
            ` : ''}
            
            <div class="form-group">
              <label>API Key</label>
              <input 
                type="password" 
                .value=${this.formState.apiKey}
                @input=${(e: Event) => this.formState.apiKey = (e.target as HTMLInputElement).value}
                placeholder="Paste your API key here"
              />
              <div class="form-hint">Stored securely in your browser's local storage</div>
              ${this.validationErrors.apiKey ? html`<div class="form-error">${this.validationErrors.apiKey}</div>` : ''}
            </div>
            
            <div class="form-group">
              <label>Base URL</label>
              <input 
                type="text" 
                .value=${this.formState.baseUrl}
                @input=${(e: Event) => this.formState.baseUrl = (e.target as HTMLInputElement).value}
              />
              ${this.validationErrors.baseUrl ? html`<div class="form-error">${this.validationErrors.baseUrl}</div>` : ''}
            </div>
            
            <div class="form-group">
              <label>Model</label>
              <input 
                type="text" 
                .value=${this.formState.model}
                @input=${(e: Event) => this.formState.model = (e.target as HTMLInputElement).value}
                placeholder="e.g., gpt-4-turbo"
              />
              ${this.validationErrors.model ? html`<div class="form-error">${this.validationErrors.model}</div>` : ''}
            </div>
            
            <div class="divider"></div>
            
            <div class="form-group">
              <label>Temperature (${this.formState.temperature})</label>
              <input 
                type="range" 
                min="0" 
                max="2" 
                step="0.1"
                .value=${String(this.formState.temperature)}
                @input=${(e: Event) => this.formState.temperature = parseFloat((e.target as HTMLInputElement).value)}
              />
              <div class="form-hint">Lower = focused, Higher = creative</div>
            </div>
            
            <div class="form-group">
              <label>Max Tokens</label>
              <input 
                type="number" 
                .value=${String(this.formState.maxTokens)}
                @input=${(e: Event) => this.formState.maxTokens = parseInt((e.target as HTMLInputElement).value)}
              />
            </div>
            
            ${this.testResult ? html`
              <div class="form-success">${this.testResult}</div>
            ` : ''}
            
            <div class="modal-actions">
              <button class="btn btn-secondary" @click=${() => this.closeModal()}>
                Cancel
              </button>
              <button 
                class="btn btn-secondary" 
                @click=${() => this.testConnection()}
                ?disabled=${this.testingConnection}
              >
                ${this.testingConnection ? 'Testing...' : 'Test Connection'}
              </button>
              <button 
                class="btn btn-primary" 
                @click=${() => this.saveProvider()}
              >
                ${this.editingProvider ? 'Update' : 'Save'} Provider
              </button>
            </div>
          </div>
        </div>
      </div>
    `
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'settings-page': SettingsPage
  }
}
