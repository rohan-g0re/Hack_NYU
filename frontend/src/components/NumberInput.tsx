import React from 'react';
import clsx from 'clsx';

interface NumberInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  error?: string;
  helpText?: string;
  onIncrement?: () => void;
  onDecrement?: () => void;
}

export function NumberInput({
  label,
  error,
  helpText,
  className,
  id,
  onIncrement,
  onDecrement,
  ...props
}: NumberInputProps) {
  const generatedId = React.useId();
  const inputId = id || generatedId;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-neutral-700 mb-1">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {onDecrement && (
          <button
            type="button"
            onClick={onDecrement}
            className="absolute left-2 p-1 text-neutral-500 hover:text-neutral-700 focus:outline-none"
            disabled={props.disabled}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </button>
        )}
        <input
          id={inputId}
          type="number"
          className={clsx(
            'w-full px-3 py-2 border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors',
            error
              ? 'border-danger-500 focus:ring-danger-500'
              : 'border-neutral-300',
            (onIncrement || onDecrement) && 'px-10 text-center',
            props.disabled && 'bg-neutral-100 cursor-not-allowed',
            className
          )}
          {...props}
        />
        {onIncrement && (
          <button
            type="button"
            onClick={onIncrement}
            className="absolute right-2 p-1 text-neutral-500 hover:text-neutral-700 focus:outline-none"
            disabled={props.disabled}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
      </div>
      {error && (
        <p className="mt-1 text-sm text-danger-600">{error}</p>
      )}
      {helpText && !error && (
        <p className="mt-1 text-sm text-neutral-500">{helpText}</p>
      )}
    </div>
  );
}

