import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { CfdComponent } from './base.js';

/**
 * Header component with user info and logout
 */
@customElement('cfd-header')
export class CfdHeader extends CfdComponent {
  @state() private username = 'Guest';

  static override styles = [
    ...CfdComponent.styles,
    css`
      :host {
        display: block;
        background: white;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        z-index: 10;
      }
      .container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        height: 4rem;
        padding: 0 1.5rem;
      }
      .title {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--cfd-color-gray-700, #374151);
      }
      .user-section {
        display: flex;
        align-items: center;
        gap: 1rem;
      }
      .username {
        font-size: 0.875rem;
        color: var(--cfd-color-gray-600, #4b5563);
      }
      button {
        padding: 0.25rem 0.75rem;
        font-size: 0.875rem;
        color: var(--cfd-color-gray-600, #4b5563);
        background: transparent;
        border: 1px solid transparent;
        border-radius: 0.25rem;
        cursor: pointer;
      }
      button:hover {
        color: var(--cfd-color-gray-900, #111827);
        background: var(--cfd-color-gray-100, #f3f4f6);
      }
    `
  ];

  connectedCallback() {
    super.connectedCallback();
    // Listen for auth state changes
    window.addEventListener('auth-change', this.handleAuthChange);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('auth-change', this.handleAuthChange);
  }

  private handleAuthChange = (e: CustomEvent) => {
    this.username = e.detail?.username || 'Guest';
  };

  private handleLogout() {
    window.dispatchEvent(new CustomEvent('logout', { bubbles: true, composed: true }));
  }

  override render() {
    return html`
      <header class="container">
        <div class="title">CFD Simulation Platform</div>
        <div class="user-section">
          <span class="username">${this.username}</span>
          <button @click=${this.handleLogout}>Logout</button>
        </div>
      </header>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-header': CfdHeader;
  }
}