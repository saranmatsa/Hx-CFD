import React from 'react';
import { tokens } from '../../tokens';

interface PanelProps {
  title: string;
  children: React.ReactNode;
  width?: string;
  height?: string;
  onPin?: () => void;
  onExpand?: () => void;
  onClose?: () => void;
  style?: React.CSSProperties;
}

export const Panel: React.FC<PanelProps> = ({
  title,
  children,
  width = '300px',
  height = '100%',
  onPin,
  onExpand,
  onClose,
  style
}) => {
  return (
    <div
      style={{
        width,
        height,
        backgroundColor: tokens.color.structural.titanium[900],
        border: '1px solid ' + tokens.color.structural.titanium[500],
        borderRadius: tokens.radius.md,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        boxShadow: tokens.elevation[1],
        ...style,
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          height: '36px',
          padding: '0 ' + tokens.spacing[3],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid ' + tokens.color.structural.titanium[500],
        }}
      >
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: tokens.color.structural.titanium[300],
          }}
        >
          {title}
        </span>
        <div style={{ display: 'flex', gap: tokens.spacing[1] }}>
          {onPin && (
            <button
              onClick={onPin}
              style={{
                width: '24px',
                height: '24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'transparent',
                border: 'none',
                borderRadius: tokens.radius.sm,
                color: tokens.color.structural.titanium[300],
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              📌
            </button>
          )}
          {onExpand && (
            <button
              onClick={onExpand}
              style={{
                width: '24px',
                height: '24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'transparent',
                border: 'none',
                borderRadius: tokens.radius.sm,
                color: tokens.color.structural.titanium[300],
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              ⛶
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              style={{
                width: '24px',
                height: '24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'transparent',
                border: 'none',
                borderRadius: tokens.radius.sm,
                color: tokens.color.structural.titanium[300],
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Panel Content */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: tokens.spacing[3],
        }}
      >
        {children}
      </div>
    </div>
  );
};
