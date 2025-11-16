import React from 'react';
import clsx from 'clsx';

export type BadgeVariant = 'pending' | 'active' | 'completed' | 'failed' | 'warning' | 'info';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export function Badge({ children, variant = 'info', className }: BadgeProps) {
  const variantClasses = {
    pending: 'bg-neutral-100 text-neutral-700 border-neutral-300',
    active: 'bg-primary-100 text-primary-700 border-primary-300',
    completed: 'bg-secondary-100 text-secondary-700 border-secondary-300',
    failed: 'bg-danger-100 text-danger-700 border-danger-300',
    warning: 'bg-warning-100 text-warning-700 border-warning-300',
    info: 'bg-blue-100 text-blue-700 border-blue-300',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

