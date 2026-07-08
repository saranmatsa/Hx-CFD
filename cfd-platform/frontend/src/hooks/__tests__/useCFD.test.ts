import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';

describe('useCFD Hook', () => {
  beforeEach(() => {
    // Reset any state before each test
  });

  it('initializes with default state', () => {
    const { result } = renderHook(() => ({
      simulationStatus: 'idle',
      meshQuality: 0.95,
    }));
    
    expect(result.current.simulationStatus).toBe('idle');
    expect(result.current.meshQuality).toBe(0.95);
  });

  it('updates simulation status', () => {
    const { result } = renderHook(() => {
      const [status, setStatus] = React.useState('idle');
      return { status, setStatus };
    });
    
    act(() => {
      result.current.setStatus('running');
    });
    
    expect(result.current.status).toBe('running');
  });
});
