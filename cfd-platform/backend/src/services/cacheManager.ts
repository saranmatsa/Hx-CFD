/**
 * Cache Management System
 * Multi-level caching for analysis results and computed data
 */

import * as crypto from 'crypto';

export interface CacheOptions {
  ttl?: number;
  maxSize?: number;
  compression?: boolean;
  storage?: 'memory' | 'localStorage' | 'IndexedDB';
}

export interface CacheEntry<T = any> {
  key: string;
  value: T;
  timestamp: number;
  accessCount: number;
  lastAccess: number;
  size: number;
  metadata?: Record<string, any>;
}

export interface CacheStats {
  hits: number;
  misses: number;
  evictions: number;
  size: number;
  maxSize: number;
  hitRate: number;
}

export interface SerializedCache {
  version: number;
  entries: [string, CacheEntry][];
  stats: CacheStats;
}

export class CacheManager<T = any> {
  private store: Map<string, CacheEntry<T>> = new Map();
  private accessOrder: string[] = [];
  private stats: CacheStats = {
    hits: 0,
    misses: 0,
    evictions: 0,
    size: 0,
    maxSize: 100,
    hitRate: 0
  };

  private readonly defaultTTL: number;
  private readonly maxSize: number;
  private readonly compression: boolean;
  private readonly storage: 'memory' | 'localStorage' | 'IndexedDB';
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor(options: CacheOptions = {}) {
    this.defaultTTL = options.ttl || 5 * 60 * 1000; // 5 minutes
    this.maxSize = options.maxSize || 100;
    this.compression = options.compression || false;
    this.storage = options.storage || 'memory';
    this.stats.maxSize = this.maxSize;

    if (this.storage !== 'memory') {
      this.initializePersistentStorage();
    }

    this.startCleanupTimer();
  }

  private async initializePersistentStorage() {
    if (this.storage === 'localStorage' && typeof window !== 'undefined') {
      const saved = localStorage.getItem('cfd-cache');
      if (saved) {
        try {
          const data: SerializedCache = JSON.parse(saved);
          for (const [key, entry] of data.entries) {
            this.store.set(key, entry as CacheEntry<T>);
            this.accessOrder.push(key);
          }
          this.stats = data.stats;
        } catch (e) {
          console.error('Failed to load cache from localStorage:', e);
        }
      }
    }
  }

  private persistCache() {
    if (this.storage === 'localStorage' && typeof window !== 'undefined') {
      const data: SerializedCache = {
        version: 1,
        entries: Array.from(this.store.entries()),
        stats: this.stats
      };
      try {
        localStorage.setItem('cfd-cache', JSON.stringify(data));
      } catch (e) {
        console.error('Failed to persist cache:', e);
      }
    }
  }

  private startCleanupTimer() {
    this.cleanupInterval = setInterval(() => {
      this.cleanup();
    }, 60000); // Every minute
  }

  public set(key: string, value: T, options: { ttl?: number; metadata?: Record<string, any> } = {}): void {
    const now = Date.now();
    const size = this.estimateSize(value);

    // Remove if exists
    if (this.store.has(key)) {
      this.remove(key);
    }

    // Evict if necessary
    while (this.store.size >= this.maxSize) {
      this.evictLRU();
    }

    const entry: CacheEntry<T> = {
      key,
      value,
      timestamp: now,
      accessCount: 0,
      lastAccess: now,
      size,
      metadata: options.metadata
    };

    this.store.set(key, entry);
    this.accessOrder.push(key);
    this.stats.size += size;

    // Persist periodically
    if (this.accessOrder.length % 10 === 0) {
      this.persistCache();
    }
  }

  public get(key: string): T | null {
    const entry = this.store.get(key);
    
    if (!entry) {
      this.stats.misses++;
      this.updateHitRate();
      return null;
    }

    // Check TTL
    const ttl = entry.metadata?.ttl || this.defaultTTL;
    if (Date.now() - entry.timestamp > ttl) {
      this.remove(key);
      this.stats.misses++;
      this.updateHitRate();
      return null;
    }

    // Update access metadata
    entry.accessCount++;
    entry.lastAccess = Date.now();
    
    // Move to end of access order (most recently used)
    const index = this.accessOrder.indexOf(key);
    if (index !== -1) {
      this.accessOrder.splice(index, 1);
      this.accessOrder.push(key);
    }

    this.stats.hits++;
    this.updateHitRate();
    return entry.value;
  }

  public has(key: string): boolean {
    const entry = this.store.get(key);
    if (!entry) return false;

    const ttl = entry.metadata?.ttl || this.defaultTTL;
    if (Date.now() - entry.timestamp > ttl) {
      this.remove(key);
      return false;
    }

    return true;
  }

  public remove(key: string): boolean {
    const entry = this.store.get(key);
    if (!entry) return false;

    this.store.delete(key);
    this.accessOrder = this.accessOrder.filter(k => k !== key);
    this.stats.size -= entry.size;
    return true;
  }

  public clear(): void {
    this.store.clear();
    this.accessOrder = [];
    this.stats.size = 0;
    this.persistCache();
  }

  private evictLRU(): void {
    if (this.accessOrder.length === 0) return;

    const lruKey = this.accessOrder[0];
    const entry = this.store.get(lruKey);
    
    if (entry) {
      this.stats.size -= entry.size;
      this.stats.evictions++;
    }

    this.store.delete(lruKey);
    this.accessOrder.shift();
  }

  private cleanup(): void {
    const now = Date.now();
    const toRemove: string[] = [];

    for (const [key, entry] of this.store.entries()) {
      const ttl = entry.metadata?.ttl || this.defaultTTL;
      if (now - entry.timestamp > ttl) {
        toRemove.push(key);
      }
    }

    for (const key of toRemove) {
      this.remove(key);
    }

    if (toRemove.length > 0) {
      this.persistCache();
    }
  }

  private estimateSize(value: T): number {
    try {
      const str = JSON.stringify(value);
      return str.length * 2; // Approximate UTF-16 size
    } catch {
      return 1024; // Default 1KB estimate
    }
  }

  private updateHitRate(): void {
    const total = this.stats.hits + this.stats.misses;
    this.stats.hitRate = total > 0 ? this.stats.hits / total : 0;
  }

  public getStats(): CacheStats {
    return { ...this.stats };
  }

  public getKeys(): string[] {
    return Array.from(this.store.keys());
  }

  public getSize(): number {
    return this.store.size;
  }

  public getMemoryUsage(): number {
    return this.stats.size;
  }

  // Key generation utilities
  public static generateKey(...parts: any[]): string {
    const str = parts.map(p => {
      if (typeof p === 'object') {
        return JSON.stringify(p);
      }
      return String(p);
    }).join('|');
    
    return crypto.createHash('md5').update(str).digest('hex');
  }

  public static generateParameterKey(
    parameters: Record<string, number>,
    fidelity?: string
  ): string {
    const sorted = Object.entries(parameters)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${k}:${v.toFixed(4)}`)
      .join('|');
    
    return crypto.createHash('md5')
      .update(`${fidelity || 'default'}:${sorted}`)
      .digest('hex');
  }

  public dispose(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    this.persistCache();
  }
}

// Specialized caches for different data types
export class ResultCache extends CacheManager {
  constructor(options: CacheOptions = {}) {
    super({ ...options, maxSize: options.maxSize || 50 });
  }

  public setResult(
    parameters: Record<string, number>,
    fidelity: string,
    result: any
  ): void {
    const key = CacheManager.generateParameterKey(parameters, fidelity);
    this.set(key, result, {
      metadata: { type: 'analysis-result', fidelity }
    });
  }

  public getResult(
    parameters: Record<string, number>,
    fidelity: string
  ): any | null {
    const key = CacheManager.generateParameterKey(parameters, fidelity);
    return this.get(key);
  }
}

export class MeshCache extends CacheManager {
  constructor(options: CacheOptions = {}) {
    super({ ...options, maxSize: options.maxSize || 20 });
  }

  public setMesh(
    geometryId: string,
    resolution: string,
    mesh: any
  ): void {
    const key = CacheManager.generateKey(geometryId, resolution);
    this.set(key, mesh, {
      metadata: { type: 'mesh', geometryId, resolution }
    });
  }

  public getMesh(geometryId: string, resolution: string): any | null {
    const key = CacheManager.generateKey(geometryId, resolution);
    return this.get(key);
  }
}

export class FieldCache extends CacheManager {
  constructor(options: CacheOptions = {}) {
    super({ ...options, maxSize: options.maxSize || 30 });
  }

  public setField(
    resultId: string,
    fieldName: string,
    fieldData: any
  ): void {
    const key = CacheManager.generateKey(resultId, fieldName);
    this.set(key, fieldData, {
      metadata: { type: 'field', resultId, fieldName }
    });
  }

  public getField(resultId: string, fieldName: string): any | null {
    const key = CacheManager.generateKey(resultId, fieldName);
    return this.get(key);
  }
}

// Singleton instances
let resultCacheInstance: ResultCache | null = null;
let meshCacheInstance: MeshCache | null = null;
let fieldCacheInstance: FieldCache | null = null;

export function getResultCache(): ResultCache {
  if (!resultCacheInstance) {
    resultCacheInstance = new ResultCache();
  }
  return resultCacheInstance;
}

export function getMeshCache(): MeshCache {
  if (!meshCacheInstance) {
    meshCacheInstance = new MeshCache();
  }
  return meshCacheInstance;
}

export function getFieldCache(): FieldCache {
  if (!fieldCacheInstance) {
    fieldCacheInstance = new FieldCache();
  }
  return fieldCacheInstance;
}