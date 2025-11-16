import React from 'react';
import clsx from 'clsx';

interface ProgressBarProps {
  progress: number; // 0-100
  label?: string;
  showPercentage?: boolean;
  variant?: 'primary' | 'secondary' | 'warning' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ProgressBar({
  progress,
  label,
  showPercentage = false,
  variant = 'primary',
  size = 'md',
  className,
}: ProgressBarProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));

  const variantClasses = {
    primary: 'bg-primary-500',
    secondary: 'bg-secondary-500',
    warning: 'bg-warning-500',
    danger: 'bg-danger-500',
  };

  const sizeClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
  };

  return (
    <div className={clsx('w-full', className)}>
      {(label || showPercentage) && (
        <div className="flex justify-between items-center mb-1">
          {label && <span className="text-sm font-medium text-neutral-700">{label}</span>}
          {showPercentage && <span className="text-sm font-medium text-neutral-700">{Math.round(clampedProgress)}%</span>}
        </div>
      )}
      <div className={clsx('w-full bg-neutral-200 rounded-full overflow-hidden', sizeClasses[size])}>
        <div
          className={clsx(
            'h-full transition-all duration-300 ease-out rounded-full',
            variantClasses[variant]
          )}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  );
}

