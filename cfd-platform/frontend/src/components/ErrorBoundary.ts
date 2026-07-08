import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { CfdComponent } from './base.js';

/**
 * Error boundary component for catching and displaying errors
 */
@customElement('cfd-error-boundary')
export class CfdErrorBoundary extends CfdComponent {
  @property() fallback: string | undefined;
  @state() private hasError = false;
  @state() private errorMessage = '';

  static override styles = [
    ...CfdComponent.styles,
    css`
      :host {
        display: block;
      }
      .container {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--cfd-color-gray-50, #f9fafb);
      }
      .card {
        max-width: 28rem;
        width: 100%;
        background: white;
        border-radius: 0.5rem;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        padding: 1.5rem;
      }
      .icon-container {
        width: 3rem;
        height: 3rem;
        background: var(--cfd-color-error-light, #fee2e2);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 1rem;
      }
      .icon-container svg {
        width: 1.5rem;
        height: 1.5rem;
        color: var(--cfd-color-error, #dc3545);
      }
      h2 {
        font-size: 1.25rem;
        font-weight: 700;
        text-align: center;
        color: var(--cfd-color-gray-900, #111827);
        margin-bottom: 0.5rem;
      }
      p {
        text-align: center;
        color: var(--cfd-color-gray-600, #4b5563);
        margin-bottom: 1rem;
      }
      button {
        width: 100%;
        padding: 0.625rem 1rem;
        background: var(--cfd-color-primary, #3b82f6);
        color: white;
        border-radius: 0.5rem;
        border: none;
        cursor: pointer;
        font-weight: 500;
      }
      button:hover {
        background: var(--cfd-color-primary-dark, #2563eb);
      }
    `
  ];

  handleReload() {
    window.location.reload();
  }

  override render() {
    if (this.hasError) {
      return html`
        <div class="container">
          <div class="card">
            <div class="icon-container">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2>Something went wrong</h2>
            <p>${this.errorMessage || 'An unexpected error occurred'}</p>
            <button @click=${this.handleReload}>Reload Page</button>
          </div>
        </div>
      `;
    }
    return html`<slot></slot>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-error-boundary': CfdErrorBoundary;
  }
}