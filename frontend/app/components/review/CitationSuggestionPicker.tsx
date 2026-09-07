'use client';

/**
 * Lienmark Citation Suggestion Picker (Sprint 4.3)
 * Provides pre-populated legal citation chips, statutory preview,
 * and 1-click insertion into counsel adjudication text areas.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import React, { useState, useMemo } from 'react';
import { Scale, BookOpen, Check, Plus, Sparkles, FileText } from 'lucide-react';
import { CitationTemplateUI, CitationSuggestionPickerProps } from './review_types';
import { DEFAULT_CITATION_TEMPLATES, getCitationByCategory } from './review_utils';

export const CitationSuggestionPicker: React.FC<CitationSuggestionPickerProps> = ({
  onSelectCitation,
  selectedCitationText = '',
  templates = DEFAULT_CITATION_TEMPLATES,
  className = '',
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [previewedTemplate, setPreviewedTemplate] = useState<CitationTemplateUI>(
    templates[0] ?? DEFAULT_CITATION_TEMPLATES[0]
  );

  const categories = useMemo(() => {
    const set = new Set<string>(['All']);
    templates.forEach((t) => set.add(t.category));
    return Array.from(set);
  }, [templates]);

  const filteredTemplates = useMemo(() => {
    return getCitationByCategory(selectedCategory, templates);
  }, [selectedCategory, templates]);

  const handleChipClick = (tmpl: CitationTemplateUI): void => {
    setPreviewedTemplate(tmpl);
  };

  const handleInsertClick = (tmpl: CitationTemplateUI): void => {
    onSelectCitation(tmpl.text, tmpl);
  };

  const isCurrentActive = (tmplText: string): boolean => {
    return Boolean(selectedCitationText && selectedCitationText.includes(tmplText.slice(0, 30)));
  };

  return (
    <div className={`space-y-3 rounded-lg border border-slate-800/80 bg-slate-900/50 p-3 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="h-4 w-4 text-sky-400" aria-hidden="true" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Pre-Populated Legal Citation Suggestion Picker
          </span>
        </div>
        <span className="inline-flex items-center gap-1 rounded bg-sky-950/60 px-2 py-0.5 text-[10px] font-mono text-sky-300 border border-sky-500/30">
          <Sparkles className="h-2.5 w-2.5" /> 1-Click Insert
        </span>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Citation categories">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            role="tab"
            aria-selected={selectedCategory === cat}
            onClick={() => setSelectedCategory(cat)}
            className={`rounded px-2 py-0.5 text-[11px] font-medium transition-colors ${
              selectedCategory === cat
                ? 'bg-sky-500 text-slate-950 font-bold'
                : 'bg-slate-800/70 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Citation Chips */}
      <div className="flex flex-wrap gap-2">
        {filteredTemplates.map((tmpl) => {
          const isSelected = previewedTemplate.id === tmpl.id;
          const isInserted = isCurrentActive(tmpl.text);
          return (
            <button
              key={tmpl.id}
              type="button"
              onClick={() => handleChipClick(tmpl)}
              className={`group flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs transition-all ${
                isSelected
                  ? 'border-sky-400 bg-sky-950/70 text-white ring-1 ring-sky-500/40'
                  : 'border-slate-800 bg-slate-950/50 text-slate-300 hover:border-slate-700 hover:bg-slate-800/60'
              }`}
            >
              <BookOpen className="h-3 w-3 text-sky-400" />
              <span className="font-medium">{tmpl.title}</span>
              {isInserted && (
                <span className="inline-flex items-center text-[10px] font-bold text-emerald-400">
                  <Check className="h-3 w-3" />
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Preview & 1-Click Insertion Box */}
      {previewedTemplate && (
        <div className="rounded-md border border-slate-800/90 bg-slate-950/70 p-2.5 text-xs">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/60">
            <div className="flex items-center gap-2">
              <FileText className="h-3.5 w-3.5 text-amber-400" />
              <span className="font-mono text-[11px] font-semibold text-amber-300">
                {previewedTemplate.statute}
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleInsertClick(previewedTemplate)}
              className="inline-flex items-center gap-1 rounded bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/40 px-2 py-0.5 font-mono text-[11px] font-bold transition-all"
            >
              <Plus className="h-3 w-3" /> Insert Citation
            </button>
          </div>
          <p className="mt-1.5 text-slate-300 font-sans text-[11px] leading-relaxed line-clamp-3">
            {previewedTemplate.text}
          </p>
        </div>
      )}
    </div>
  );
};

export default CitationSuggestionPicker;
