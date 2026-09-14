import React from 'react';

export const Badge: React.FC<{ children: React.ReactNode; variant?: 'default' | 'success' | 'warning' | 'error' | 'outline' }> = ({ children, variant = 'default' }) => {
  return (
    <span className={`badge badge-${variant}`}>
      {children}
    </span>
  );
};
