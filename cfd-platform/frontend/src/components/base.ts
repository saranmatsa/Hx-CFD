import { LitElement, html, css, PropertyValues } from 'lit';
import { property, state } from 'lit/decorators.js';
import { customElement, query } from 'lit/decorators.js';

/**
 * Base component for all CFD platform components
 * Provides common patterns and utilities
 */
export abstract class CfdComponent extends LitElement {
  @state() protected loading = false;
  @state() protected error: string | null = null;

  static override styles = css`
    :host {
      display: block;
      box-sizing: border-box;
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }

    .error {
      color: var(--cfd-color-error, #dc3545);
      padding: 0.5rem;
      background: var(--cfd-color-error-bg, rgba(220, 53, 69, 0.1));
      border-radius: 4px;
    }
  `;

  protected renderLoading() {
    return html`<div class="loading">Loading...</div>`;
  }

  protected renderError(message?: string) {
    return html`<div class="error">${message || this.error || 'An error occurred'}</div>`;
  }

  protected async withLoading<T>(fn: () => Promise<T>): Promise<T | void> {
    this.loading = true;
    this.error = null;
    try {
      return await fn();
    } catch (e) {
      this.error = e instanceof Error ? e.message : 'Unknown error';
    } finally {
      this.loading = false;
    }
  }
}

/**
 * Base component for form inputs with validation
 */
export abstract class CfdInputComponent extends CfdComponent {
  @property() value = '';
  @property() label = '';
  @property() placeholder = '';
  @property({ type: Boolean }) required = false;
  @property({ type: Boolean }) disabled = false;
  @property() errorMessage = '';

  protected handleInput(e: Event) {
    this.value = (e.target as HTMLInputElement).value;
    this.dispatchEvent(new CustomEvent('input', { detail: this.value }));
  }

  protected handleChange(e: Event) {
    this.value = (e.target as HTMLInputElement).value;
    this.dispatchEvent(new CustomEvent('change', { detail: this.value }));
  }
}