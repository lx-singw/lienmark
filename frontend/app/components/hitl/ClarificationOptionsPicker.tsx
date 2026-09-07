'use client';

/**
 * Lienmark HITL Clarification Options Picker
 * Renders suggested single-click option pills to streamline counsel responses.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { Check, Sparkles } from 'lucide-react';

export interface ClarificationOptionsPickerProps {
  readonly options: ReadonlyArray<string>;
  readonly selectedOption: string | null;
  readonly onSelectOption: (option: string | null) => void;
  readonly disabled?: boolean;
  readonly className?: string;
}

export const ClarificationOptionsPicker: React.FC<ClarificationOptionsPickerProps> = ({
  options,
  selectedOption,
  onSelectOption,
  disabled = false,
  className = '',
}) => {
  if (options.length === 0) return null;

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
        <Sparkles className="h-3 w-3 text-sky-400" aria-hidden="true" />
        <span>Suggested Pre-Cleared Options (Single-Click Select):</span>
      </div>

      <div
        className="flex flex-wrap gap-2"
        role="group"
        aria-label="Suggested clarification options"
      >
        {options.map((option) => {
          const isSelected = selectedOption === option;

          return (
            <button
              key={option}
              type="button"
              disabled={disabled}
              onClick={() => onSelectOption(isSelected ? null : option)}
              aria-pressed={isSelected}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all focus:outline-none focus:ring-2 focus:ring-sky-400 ${
                isSelected
                  ? 'bg-sky-500/20 text-sky-200 border border-sky-400 font-semibold shadow-sm ring-1 ring-sky-500/30'
                  : 'bg-slate-900/80 text-slate-300 border border-slate-700/80 hover:border-slate-500 hover:bg-slate-800/80 hover:text-white'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div
                className={`flex h-3.5 w-3.5 items-center justify-center rounded-full border text-[9px] transition-colors ${
                  isSelected
                    ? 'border-sky-400 bg-sky-500 text-slate-950 font-bold'
                    : 'border-slate-600 bg-slate-800 text-transparent'
                }`}
              >
                <Check className="h-2.5 w-2.5 stroke-[3]" aria-hidden="true" />
              </div>
              <span>{option}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ClarificationOptionsPicker;
