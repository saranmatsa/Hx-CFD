import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { CfdComponent } from './base.js';

/**
 * Loading spinner component
 */
@customElement('cfd-spinner')
export class CfdSpinner extends CfdComponent {
  @property({ type: String }) size: 'sm' | 'md' | 'lg' = 'md';

  static override styles = [
    ...CfdComponent.styles,
    css`
      .spinner {
        border-radius: 50%;
        border: 2px solid var(--cfd-color-gray-200, #e5e7eb);
        border-top-color: var(--cfd-color-primary, #3b82f6);
        animation: spin 0.8s linear infinite;
      }
      .spinner.sm { width: 1rem; height: 1rem; }
      .spinner.md { width: 2rem; height: 2rem; }
      .spinner.lg { width: 3rem; height: 3rem; border-width: 3px; }
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
    `
  ];

  override render() {
    return html`<div class="spinner ${this.size}"></div>`;
  }
}

/**
 * Loading overlay with message
 */
@customElement('cfd-loading-overlay')
export class CfdLoadingOverlay extends CfdComponent {
  @property({ type: String }) message = 'Loading...';

  static override styles = [
    ...CfdComponent.styles,
    css`
      :host {
        display: block;
        position: relative;
      }
      .overlay {
        position: absolute;
        inset: 0;
        background: rgba(255, 255, 255, 0.75);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10;
      }
      .content {
        text-align: center;
      }
      .content p {
        margin-top: 0.5rem;
        color: var(--cfd-color-gray-600, #4b5563);
      }
    `
  ];

  override render() {
    return html`
      <slot></slot>
      <div class="overlay">
        <div class="content">
          <cfd-spinner size="lg"></cfd-spinner>
          <p>${this.message}</p>
        </div>
      </div>
    `;
  }
}

/**
 * Loading card placeholder
 */
@customElement('cfd-loading-card')
export class CfdLoadingCard extends CfdComponent {
  @property({ type: String }) title = 'Loading...';

  static override styles = [
    ...CfdComponent.styles,
    css`
      .card {
        background: white;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        padding: 1.5rem;
      }
      .skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 4px;
      }
      .skeleton-line {
        height: 1rem;
        margin-bottom: 0.75rem;
      }
      .skeleton-line:last-child {
        width: 60%;
      }
      @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `
  ];

  override render() {
    return html`
      <div class="card">
        <div class="skeleton skeleton-line" style="width: 40%"></div>
        <div class="skeleton skeleton-line"></div>
        <div class="skeleton skeleton-line"></div>
        <div class="skeleton skeleton-line"></div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cfd-spinner': CfdSpinner;
    'cfd-loading-overlay': CfdLoadingOverlay;
    'cfd-loading-card': CfdLoadingCard;
  }
}