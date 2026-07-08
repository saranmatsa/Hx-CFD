/**
 * Event Bus System for Interactive Engineering Analysis Workspace
 * Provides event-driven architecture for real-time parameter updates and analysis
 */

import type { 
  WorkspaceEvent, 
  ParameterChangeEvent, 
  AnalysisUpdateEvent,
  MetricsStreamEvent,
  ConvergenceEvent,
  WorkspaceState,
  AnalysisResult,
  EngineeringMetrics,
  ParameterBase
} from '../types/workspace';

// ============================================================
// Event Bus Implementation
// ============================================================

type EventHandler<T extends WorkspaceEvent = WorkspaceEvent> = (event: T) => void;

interface Subscription {
  id: string;
  eventType: string | '*';
  handler: EventHandler;
  priority: number;
  once: boolean;
}

class EventBus {
  private subscriptions: Map<string, Subscription[]> = new Map();
  private eventHistory: WorkspaceEvent[] = [];
  private maxHistorySize = 1000;
  private emitter: EventEmitter;

  constructor() {
    this.emitter = new EventEmitter();
  }

  /**
   * Subscribe to workspace events
   */
  subscribe<T extends WorkspaceEvent>(
    eventType: T['type'] | '*',
    handler: EventHandler<T>,
    options: { priority?: number; once?: boolean } = {}
  ): () => void {
    const { priority = 0, once = false } = options;
    const id = this.generateId();
    
    const subscription: Subscription = {
      id,
      eventType,
      handler: handler as EventHandler,
      priority,
      once
    };

    const existing = this.subscriptions.get(eventType) || [];
    this.subscriptions.set(eventType, [...existing, subscription].sort((a, b) => b.priority - a.priority));

    // Return unsubscribe function
    return () => this.unsubscribe(id);
  }

  /**
   * Unsubscribe from events
   */
  unsubscribe(subscriptionId: string): void {
    for (const [eventType, subs] of this.subscriptions.entries()) {
      const filtered = subs.filter(s => s.id !== subscriptionId);
      if (filtered.length > 0) {
        this.subscriptions.set(eventType, filtered);
      } else {
        this.subscriptions.delete(eventType);
      }
    }
  }

  /**
   * Emit an event to all subscribers
   */
  emit<T extends WorkspaceEvent>(event: T): void {
    // Store in history
    this.eventHistory.push(event);
    if (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory.shift();
    }

    // Emit to specific type subscribers
    const typeSubs = this.subscriptions.get(event.type) || [];
    this.emitToSubscribers(typeSubs, event);

    // Emit to wildcard subscribers
    const wildcardSubs = this.subscriptions.get('*') || [];
    this.emitToSubscribers(wildcardSubs, event);
  }

  private emitToSubscribers(subs: Subscription[], event: WorkspaceEvent): void {
    const toRemove: string[] = [];
    
    for (const sub of subs) {
      try {
        sub.handler(event);
        if (sub.once) {
          toRemove.push(sub.id);
        }
      } catch (error) {
        console.error(`Error in event handler for ${event.type}:`, error);
      }
    }

    // Remove one-time subscriptions
    for (const id of toRemove) {
      this.unsubscribe(id);
    }
  }

  /**
   * Get event history
   */
  getHistory(limit?: number): WorkspaceEvent[] {
    if (limit) {
      return this.eventHistory.slice(-limit);
    }
    return [...this.eventHistory];
  }

  /**
   * Clear event history
   */
  clearHistory(): void {
    this.eventHistory = [];
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Simple EventEmitter for internal use
class EventEmitter {
  private listeners: Map<string, Set<Function>> = new Map();

  on(event: string, listener: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(listener);
  }

  off(event: string, listener: Function): void {
    this.listeners.get(event)?.delete(listener);
  }

  emit(event: string, ...args: unknown[]): void {
    this.listeners.get(event)?.forEach(listener => {
      try {
        listener(...args);
      } catch (error) {
        console.error(`Error in emitter listener for ${event}:`, error);
      }
    });
  }
}

// Singleton instance
export const eventBus = new EventBus();

// ============================================================
// Parameter Change Events
// ============================================================

export function emitParameterChange(
  parameterId: string,
  oldValue: number,
  newValue: number,
  source: 'user' | 'optimization' | 'import' = 'user'
): void {
  const event: ParameterChangeEvent = {
    type: 'PARAMETER_CHANGE',
    parameterId,
    oldValue,
    newValue,
    timestamp: Date.now(),
    source
  };
  eventBus.emit(event);
}

export function onParameterChange(
  handler: (event: ParameterChangeEvent) => void,
  options?: { once?: boolean }
): () => void {
  return eventBus.subscribe('PARAMETER_CHANGE', handler as EventHandler, options);
}

// ============================================================
// Analysis Update Events
// ============================================================

export function emitAnalysisUpdate(
  result: Partial<AnalysisResult>,
  isPartial: boolean = false
): void {
  const event: AnalysisUpdateEvent = {
    type: 'ANALYSIS_UPDATE',
    result: {
      ...result,
      timestamp: Date.now()
    } as AnalysisResult,
    isPartial
  };
  eventBus.emit(event);
}

export function onAnalysisUpdate(
  handler: (event: AnalysisUpdateEvent) => void,
  options?: { once?: boolean }
): () => void {
  return eventBus.subscribe('ANALYSIS_UPDATE', handler as EventHandler, options);
}

// ============================================================
// Metrics Stream Events
// ============================================================

export function emitMetricsStream(
  metrics: Partial<EngineeringMetrics>
): void {
  const event: MetricsStreamEvent = {
    type: 'METRICS_STREAM',
    metrics,
    timestamp: Date.now()
  };
  eventBus.emit(event);
}

export function onMetricsStream(
  handler: (event: MetricsStreamEvent) => void
): () => void {
  return eventBus.subscribe('METRICS_STREAM', handler as EventHandler);
}

// ============================================================
// Convergence Events
// ============================================================

export function emitConvergence(data: ConvergenceEvent['data']): void {
  const event: ConvergenceEvent = {
    type: 'CONVERGENCE',
    data
  };
  eventBus.emit(event);
}

export function onConvergence(
  handler: (event: ConvergenceEvent) => void
): () => void {
  return eventBus.subscribe('CONVERGENCE', handler as EventHandler);
}

// ============================================================
// Debounced Parameter Updates
// ============================================================

export function createDebouncedParameterEmitter(
  delay: number = 100
): (parameterId: string, oldValue: number, newValue: number) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let pendingChanges: Map<string, { oldValue: number; newValue: number }> = new Map();

  return (parameterId: string, oldValue: number, newValue: number) => {
    pendingChanges.set(parameterId, { oldValue, newValue });

    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      for (const [id, { oldValue: ov, newValue: nv }] of pendingChanges) {
        emitParameterChange(id, ov, nv);
      }
      pendingChanges.clear();
      timeoutId = null;
    }, delay);
  };
}

// ============================================================
// Throttled Event Emission
// ============================================================

export function createThrottledEmitter<T extends WorkspaceEvent>(
  eventCreator: (data: T['type'] extends 'PARAMETER_CHANGE' ? 
    { parameterId: string; oldValue: number; newValue: number } : unknown
  ) => T,
  delay: number = 16 // ~60fps
): (data: Parameters<typeof eventCreator>[0]) => void {
  let lastEmit = 0;
  let pendingData: unknown = null;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return (data) => {
    pendingData = data;
    const now = Date.now();

    if (now - lastEmit >= delay) {
      eventBus.emit(eventCreator(pendingData as Parameters<typeof eventCreator>[0]));
      lastEmit = now;
      pendingData = null;
    } else if (!timeoutId) {
      timeoutId = setTimeout(() => {
        if (pendingData) {
          eventBus.emit(eventCreator(pendingData as Parameters<typeof eventCreator>[0]));
          lastEmit = Date.now();
          pendingData = null;
        }
        timeoutId = null;
      }, delay - (now - lastEmit));
    }
  };
}

// ============================================================
// Event Aggregation for Batch Updates
// ============================================================

export function createBatchedEmitter<T extends WorkspaceEvent>(
  batchSize: number = 10,
  maxDelay: number = 100
): {
  add: (event: T) => void;
  flush: () => void;
} {
  let batch: T[] = [];
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  const flush = () => {
    if (batch.length === 0) return;
    
    const events = [...batch];
    batch = [];
    
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }

    // Emit all events in batch
    for (const event of events) {
      eventBus.emit(event);
    }
  };

  const add = (event: T) => {
    batch.push(event);

    if (batch.length >= batchSize) {
      flush();
    } else if (!timeoutId) {
      timeoutId = setTimeout(flush, maxDelay);
    }
  };

  return { add, flush };
}

// ============================================================
// Event Filtering and Transformation
// ============================================================

export function createFilteredEventBus(
  filter: (event: WorkspaceEvent) => boolean
): {
  subscribe: <T extends WorkspaceEvent>(
    eventType: T['type'] | '*',
    handler: EventHandler<T>
  ) => () => void;
  emit: (event: WorkspaceEvent) => void;
} {
  return {
    subscribe: (eventType, handler) => {
      return eventBus.subscribe(eventType, (event) => {
        if (filter(event)) {
          handler(event as T);
        }
      });
    },
    emit: (event) => {
      if (filter(event)) {
        eventBus.emit(event);
      }
    }
  };
}

// Export the event bus for direct use
export { EventBus };