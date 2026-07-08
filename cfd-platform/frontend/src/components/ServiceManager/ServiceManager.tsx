/**
 * Service Manager UI Component
 * 
 * Displays service status and provides controls for starting/stopping services.
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface ServiceInfo {
  name: string;
  service_type: string;
  status: 'STOPPED' | 'STARTING' | 'RUNNING' | 'FAILED' | 'UNHEALTHY' | 'STOPPING';
  port: number | null;
  pid: number | null;
  cpu_percent: number;
  memory_mb: number;
  uptime_seconds: number | null;
  health_status: string | null;
  error_message: string | null;
}

interface ServiceMetrics {
  cpu_percent: number;
  memory_mb: number;
  uptime_seconds: number;
}

// API Configuration
const API_BASE = 'http://127.0.0.1:8000/api/v1/services';

// Status colors
const STATUS_COLORS: Record<string, string> = {
  STOPPED: '#6b7280',
  STARTING: '#f59e0b',
  RUNNING: '#10b981',
  FAILED: '#ef4444',
  UNHEALTHY: '#f97316',
  STOPPING: '#8b5cf6',
};

const STATUS_LABELS: Record<string, string> = {
  STOPPED: 'Stopped',
  STARTING: 'Starting',
  RUNNING: 'Running',
  FAILED: 'Failed',
  UNHEALTHY: 'Unhealthy',
  STOPPING: 'Stopping',
};

// Service type icons
const SERVICE_ICONS: Record<string, string> = {
  FASTAPI: '⚡',
  OPENFOAM: '🌊',
  FREECAD: '📐',
  GMSH: '🔷',
  AI_SERVICES: '🤖',
  CELERY_WORKER: '⚙️',
  REDIS: '🔴',
  POSTGRESQL: '🗄️',
  WEBSOCKET: '🔌',
};

// Format uptime
const formatUptime = (seconds: number | null): string => {
  if (seconds === null) return '-';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
};

// Format memory
const formatMemory = (mb: number): string => {
  if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`;
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${mb.toFixed(1)} MB`;
};

// Service Card Component
interface ServiceCardProps {
  service: ServiceInfo;
  onStart: (name: string) => void;
  onStop: (name: string) => void;
  onRestart: (name: string) => void;
  onHealthCheck: (name: string) => void;
}

const ServiceCard: React.FC<ServiceCardProps> = ({
  service,
  onStart,
  onStop,
  onRestart,
  onHealthCheck,
}) => {
  const isRunning = service.status === 'RUNNING';
  const isStopped = service.status === 'STOPPED';
  const isTransitioning = service.status === 'STARTING' || service.status === 'STOPPING';

  return (
    <div
      style={{
        backgroundColor: '#1f2937',
        borderRadius: '12px',
        padding: '20px',
        border: `2px solid ${STATUS_COLORS[service.status] || '#374151'}`,
        transition: 'all 0.3s ease',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>{SERVICE_ICONS[service.service_type] || '🔧'}</span>
          <div>
            <h3 style={{ margin: 0, color: '#f9fafb', fontSize: '16px', fontWeight: 600 }}>
              {service.name}
            </h3>
            <span style={{ color: '#9ca3af', fontSize: '12px' }}>
              {service.service_type}
            </span>
          </div>
        </div>
        <div
          style={{
            padding: '4px 12px',
            borderRadius: '9999px',
            backgroundColor: STATUS_COLORS[service.status],
            color: 'white',
            fontSize: '12px',
            fontWeight: 500,
          }}
        >
          {STATUS_LABELS[service.status]}
        </div>
      </div>

      {/* Metrics */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        <MetricItem label="Port" value={service.port?.toString() || '-'} />
        <MetricItem label="PID" value={service.pid?.toString() || '-'} />
        <MetricItem label="CPU" value={`${service.cpu_percent.toFixed(1)}%`} />
        <MetricItem label="Memory" value={formatMemory(service.memory_mb)} />
        <MetricItem label="Uptime" value={formatUptime(service.uptime_seconds)} />
        <MetricItem label="Health" value={service.health_status || '-'} />
      </div>

      {/* Error message */}
      {service.error_message && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '8px 12px',
            marginBottom: '16px',
            fontSize: '12px',
            color: '#fca5a5',
          }}
        >
          {service.error_message}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: '8px' }}>
        {!isRunning && !isTransitioning && (
          <ActionButton
            label="Start"
            onClick={() => onStart(service.name)}
            color="#10b981"
          />
        )}
        {isRunning && (
          <>
            <ActionButton
              label="Stop"
              onClick={() => onStop(service.name)}
              color="#ef4444"
            />
            <ActionButton
              label="Restart"
              onClick={() => onRestart(service.name)}
              color="#f59e0b"
            />
          </>
        )}
        <ActionButton
          label="Health Check"
          onClick={() => onHealthCheck(service.name)}
          color="#6366f1"
        />
      </div>
    </div>
  );
};

// Metric Item Component
interface MetricItemProps {
  label: string;
  value: string;
}

const MetricItem: React.FC<MetricItemProps> = ({ label, value }) => (
  <div
    style={{
      backgroundColor: '#374151',
      borderRadius: '8px',
      padding: '8px 12px',
    }}
  >
    <div style={{ color: '#9ca3af', fontSize: '10px', textTransform: 'uppercase' }}>
      {label}
    </div>
    <div style={{ color: '#f9fafb', fontSize: '14px', fontWeight: 500 }}>
      {value}
    </div>
  </div>
);

// Action Button Component
interface ActionButtonProps {
  label: string;
  onClick: () => void;
  color: string;
  disabled?: boolean;
}

const ActionButton: React.FC<ActionButtonProps> = ({
  label,
  onClick,
  color,
  disabled = false,
}) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{
      flex: 1,
      padding: '8px 16px',
      borderRadius: '8px',
      border: 'none',
      backgroundColor: disabled ? '#4b5563' : color,
      color: 'white',
      fontSize: '12px',
      fontWeight: 500,
      cursor: disabled ? 'not-allowed' : 'pointer',
      transition: 'all 0.2s ease',
      opacity: disabled ? 0.5 : 1,
    }}
  >
    {label}
  </button>
);

// Summary Card Component
interface SummaryCardProps {
  title: string;
  value: number;
  color: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ title, value, color }) => (
  <div
    style={{
      backgroundColor: '#1f2937',
      borderRadius: '12px',
      padding: '20px',
      textAlign: 'center',
    }}
  >
    <div style={{ fontSize: '32px', fontWeight: 700, color }}>
      {value}
    </div>
    <div style={{ color: '#9ca3af', fontSize: '14px', marginTop: '4px' }}>
      {title}
    </div>
  </div>
);

// Main Service Manager Component
export const ServiceManager: React.FC = () => {
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Fetch services
  const fetchServices = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}`);
      if (!response.ok) throw new Error('Failed to fetch services');
      const data = await response.json();
      setServices(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  // Start service
  const handleStart = async (name: string) => {
    try {
      const response = await fetch(`${API_BASE}/${name}/start`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to start service');
      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start service');
    }
  };

  // Stop service
  const handleStop = async (name: string) => {
    try {
      const response = await fetch(`${API_BASE}/${name}/stop`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to stop service');
      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop service');
    }
  };

  // Restart service
  const handleRestart = async (name: string) => {
    try {
      const response = await fetch(`${API_BASE}/${name}/restart`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to restart service');
      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart service');
    }
  };

  // Health check
  const handleHealthCheck = async (name: string) => {
    try {
      const response = await fetch(`${API_BASE}/${name}/health`);
      if (!response.ok) throw new Error('Health check failed');
      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Health check failed');
    }
  };

  // Start all services
  const handleStartAll = async () => {
    try {
      const response = await fetch(`${API_BASE}/start-all`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to start services');
      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start services');
    }
  };

  // Stop all services
  const handleStopAll = async () => {
    try {
      const response = await fetch(`${API_BASE}/stop-all`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to stop services');
      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop services');
    }
  };

  // WebSocket connection
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      try {
        ws = new WebSocket('ws://127.0.0.1:8000/api/v1/services/ws');

        ws.onopen = () => {
          setWsConnected(true);
          console.log('WebSocket connected');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'initial_state' || data.type === 'services_update') {
              setServices(data.services);
            } else if (data.type === 'metrics_update') {
              setServices(data.services);
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          console.log('WebSocket disconnected, reconnecting...');
          reconnectTimeout = setTimeout(connect, 3000);
        };

        ws.onerror = (err) => {
          console.error('WebSocket error:', err);
        };
      } catch (err) {
        console.error('Failed to connect WebSocket:', err);
        reconnectTimeout = setTimeout(connect, 3000);
      }
    };

    connect();

    // Initial fetch
    fetchServices();

    // Poll for updates as fallback
    const pollInterval = setInterval(fetchServices, 10000);

    return () => {
      clearInterval(pollInterval);
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, [fetchServices]);

  // Calculate summary
  const summary = {
    total: services.length,
    running: services.filter((s) => s.status === 'RUNNING').length,
    stopped: services.filter((s) => s.status === 'STOPPED').length,
    failed: services.filter((s) => s.status === 'FAILED' || s.status === 'UNHEALTHY').length,
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
        Loading services...
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '24px',
        }}
      >
        <div>
          <h1 style={{ margin: 0, color: '#f9fafb', fontSize: '24px', fontWeight: 700 }}>
            Service Manager
          </h1>
          <p style={{ margin: '4px 0 0', color: '#9ca3af', fontSize: '14px' }}>
            Monitor and control local desktop services
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              backgroundColor: wsConnected ? '#10b981' : '#ef4444',
              borderRadius: '9999px',
              fontSize: '12px',
              color: 'white',
            }}
          >
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: 'white',
              }}
            />
            {wsConnected ? 'Connected' : 'Disconnected'}
          </div>
          <button
            onClick={handleStartAll}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#10b981',
              color: 'white',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Start All
          </button>
          <button
            onClick={handleStopAll}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#ef4444',
              color: 'white',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Stop All
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '12px 16px',
            marginBottom: '24px',
            color: '#fca5a5',
            fontSize: '14px',
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: '16px',
              padding: '4px 8px',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: '#ef4444',
              color: 'white',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Summary cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <SummaryCard title="Total Services" value={summary.total} color="#6366f1" />
        <SummaryCard title="Running" value={summary.running} color="#10b981" />
        <SummaryCard title="Stopped" value={summary.stopped} color="#6b7280" />
        <SummaryCard title="Failed/Unhealthy" value={summary.failed} color="#ef4444" />
      </div>

      {/* Service cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
          gap: '16px',
        }}
      >
        {services.map((service) => (
          <ServiceCard
            key={service.name}
            service={service}
            onStart={handleStart}
            onStop={handleStop}
            onRestart={handleRestart}
            onHealthCheck={handleHealthCheck}
          />
        ))}
      </div>

      {services.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: '#9ca3af',
          }}
        >
          No services registered
        </div>
      )}
    </div>
  );
};

export default ServiceManager;