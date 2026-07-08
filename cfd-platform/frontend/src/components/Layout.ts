import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { CfdComponent } from './base.js';

/**
 * Layout component with sidebar, header, and main content area
 */
@customElement('cfd-layout')
export class CfdLayout extends CfdComponent {
  @property({ type: String }) activePage = 'dashboard';

  static override styles = [
    ...CfdComponent.styles,
    css`
      :host {
        display: flex;
        height: 100vh;
        background: var(--cfd-color-gray-100, #f3f4f6);
      }
      .main {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .content {
        flex: 1;
        overflow: auto;
        padding: 1.5rem;
      }
    `
  ];

  private handleNavigate(e: Event) {
    const customEvent = e as CustomEvent;
    this.dispatchEvent(new CustomEvent('page-change', { 
      detail: customEvent.detail,
      bubbles: true,
      composed: true 
    }));
  }

  override render() {
    return html`
      <cfd-sidebar @navigate=${this.handleNavigate}></cfd-sidebar>
      <div class="main">
        <cfd-header></cfd-header>
        <main class="content">
          <slot></slot>
        </main>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-layout': CfdLayout;
  }
}