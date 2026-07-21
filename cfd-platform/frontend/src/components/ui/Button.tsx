import React from 'react';
import { tokens } from '../../tokens';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  style?: React.CSSProperties;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'secondary',
  size = 'md',
  disabled = false,
  style
}) => {
  const sizeStyles = {
    sm: {
      padding: tokens.spacing[1] + ' ' + tokens.spacing[2],
      fontSize: '12px',
    },
    md: {
      padding: tokens.spacing[2] + ' ' + tokens.spacing[3],
      fontSize: '13px',
    },
    lg: {
      padding: tokens.spacing[3] + ' ' + tokens.spacing[4],
      fontSize: '14px',
    },
  };

  const variantStyles = {
    primary: {
      backgroundColor: tokens.color.structural.titanium[700],
      color: tokens.color.structural.white,
      border: '1px solid ' + tokens.color.structural.titanium[500],
    },
    secondary: {
      backgroundColor: tokens.color.structural.titanium[900],
      color: tokens.color.structural.white,
      border: '1px solid ' + tokens.color.structural.titanium[500],
    },
    ghost: {
      backgroundColor: 'transparent',
      color: tokens.color.structural.white,
      border: 'none',
    },
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        ...sizeStyles[size],
        ...variantStyles[variant],
        borderRadius: tokens.radius.sm,
        fontFamily: tokens.type.family.ui,
        fontWeight: 500,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'all ' + tokens.motion.duration.instant + ' ' + tokens.motion.easing.standard,
        opacity: disabled ? 0.5 : 1,
        ...style,
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor = variantStyles[variant].backgroundColor;
        }
      }}
      onMouseDown={(e) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[500];
        }
      }}
      onMouseUp={(e) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor = tokens.color.structural.titanium[700];
        }
      }}
    >
      {children}
    </button>
  );
};
