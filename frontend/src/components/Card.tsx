import React from 'react';
import clsx from 'clsx';

interface CardProps {
  children: React.ReactNode;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export function Card({ children, header, footer, className }: CardProps) {
  return (
    <div className={clsx('card', className)}>
      {header && (
        <div className="px-6 py-4 border-b border-neutral-200">
          {header}
        </div>
      )}
      <div className="px-6 py-4">{children}</div>
      {footer && (
        <div className="px-6 py-4 border-t border-neutral-200 bg-neutral-50">
          {footer}
        </div>
      )}
    </div>
  );
}

