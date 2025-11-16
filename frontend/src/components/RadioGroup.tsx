import React from 'react';
import clsx from 'clsx';

interface RadioOption {
  value: string;
  label: string;
  description?: string;
}

interface RadioGroupProps {
  label?: string;
  options: RadioOption[];
  value: string;
  onChange: (value: string) => void;
  name: string;
  error?: string;
  className?: string;
  direction?: 'horizontal' | 'vertical';
}

export function RadioGroup({
  label,
  options,
  value,
  onChange,
  name,
  error,
  className,
  direction = 'vertical',
}: RadioGroupProps) {
  return (
    <div className={clsx('w-full', className)}>
      {label && (
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          {label}
        </label>
      )}
      <div
        className={clsx(
          'flex gap-4',
          direction === 'vertical' ? 'flex-col' : 'flex-row flex-wrap'
        )}
      >
        {options.map((option) => (
          <label
            key={option.value}
            className={clsx(
              'relative flex items-start cursor-pointer group',
              option.description && 'items-start'
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={(e) => onChange(e.target.value)}
              className="mt-0.5 h-4 w-4 text-primary-600 border-neutral-300 focus:ring-2 focus:ring-primary-500 cursor-pointer"
            />
            <div className="ml-3">
              <span className="block text-sm font-medium text-neutral-900 group-hover:text-primary-600">
                {option.label}
              </span>
              {option.description && (
                <span className="block text-sm text-neutral-500">
                  {option.description}
                </span>
              )}
            </div>
          </label>
        ))}
      </div>
      {error && (
        <p className="mt-1 text-sm text-danger-600">{error}</p>
      )}
    </div>
  );
}

