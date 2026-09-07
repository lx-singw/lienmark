/**
 * frontend/app/components/intake/intake_utils.ts
 *
 * Utility functions for Multimodal Intake Stepper, Category Badges,
 * and Confidentiality Indicators.
 * Sprint 2.3: Multimodal Intake Pipeline.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import {
  ExtractionStageId,
  StageStatus,
  type IntakeStage,
  type StepStatus,
  type StageDefinition,
  type CategoryBadgeProps,
  type ConfidentialityBadgeProps,
} from './types';

export const MAX_CONFIDENTIAL_WORDS = 20;

export const EXTRACTION_STAGES: readonly StageDefinition[] = [
  {
    id: ExtractionStageId.STAGE_1_TOKENIZATION_AST,
    stageNumber: 1,
    title: 'Document Tokenization & AST Parsing',
    modelSubtitle: 'PDF / Fountain AST Parser v2',
    description: 'Decomposing scene headings, sluglines, parentheticals, and action paragraphs.',
    iconName: 'FileCode2',
  },
  {
    id: ExtractionStageId.STAGE_2_MULTIMODAL_EXTRACTION,
    stageNumber: 2,
    title: 'Primary Multimodal Extraction',
    modelSubtitle: 'Gemini 2.5 Flash (Google Cloud GenAI ADK)',
    description: 'Zero-shot multimodal extraction of primary props, music cues, and trademarks.',
    iconName: 'Sparkles',
  },
  {
    id: ExtractionStageId.STAGE_3_SELF_REFLECTION,
    stageNumber: 3,
    title: 'Self-Reflection & Background Detection Pass',
    modelSubtitle: 'Gemini 2.5 Flash Adversarial Verifier',
    description: 'Secondary verification pass catching obscure background artwork, posters, and ambient cues.',
    iconName: 'ScanEye',
  },
  {
    id: ExtractionStageId.STAGE_4_CONFIDENTIALITY_SNAPSHOT,
    stageNumber: 4,
    title: 'Confidentiality Trimming & Baseline Snapshot',
    modelSubtitle: 'Lienmark Sanitizer & Firestore Baseline Engine',
    description: 'Trimming descriptions to <= 20 words, stripping spoilers, and locking immutable snapshot.',
    iconName: 'ShieldCheck',
  },
];

export const INTAKE_STEPS: readonly {
  readonly stage: IntakeStage;
  readonly label: string;
}[] = [
  { stage: 'PARSING', label: 'Screenplay Parsing' },
  { stage: 'EXTRACTING_PRIMARY', label: 'Primary Extraction' },
  { stage: 'SELF_REFLECTION', label: 'Self-Reflection Audit' },
  { stage: 'BASELINE_COMMITTED', label: 'Baseline Registration' },
] as const;

export function formatElapsedTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00.0s';
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(1);
  return `${String(mins).padStart(2, '0')}:${secs.padStart(4, '0')}s`;
}

export function formatTokenCount(tokens: number): string {
  if (!tokens || tokens < 0) return '0 tokens';
  return `${tokens.toLocaleString()} tokens`;
}

export function getStageTheme(status: StageStatus) {
  switch (status) {
    case StageStatus.COMPLETED:
      return {
        badgeBg: 'bg-emerald-950/80',
        textColor: 'text-emerald-300',
        borderColor: 'border-emerald-500/50',
        iconBg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        barGradient: 'from-emerald-500 to-teal-400',
      };
    case StageStatus.ACTIVE:
      return {
        badgeBg: 'bg-sky-950/80',
        textColor: 'text-sky-300',
        borderColor: 'border-sky-500/60 ring-1 ring-sky-500/30',
        iconBg: 'bg-sky-500/20 text-sky-400 border-sky-500/40 animate-pulse',
        barGradient: 'from-sky-500 to-cyan-400',
      };
    case StageStatus.FAILED:
      return {
        badgeBg: 'bg-rose-950/80',
        textColor: 'text-rose-300',
        borderColor: 'border-rose-500/60',
        iconBg: 'bg-rose-500/20 text-rose-400 border-rose-500/40',
        barGradient: 'from-rose-500 to-red-400',
      };
    default:
      return {
        badgeBg: 'bg-slate-900/60',
        textColor: 'text-slate-400',
        borderColor: 'border-slate-800',
        iconBg: 'bg-slate-800/80 text-slate-500 border-slate-700',
        barGradient: 'from-slate-700 to-slate-600',
      };
  }
}

export function validateConfidentiality(description: string, maxWords = MAX_CONFIDENTIAL_WORDS) {
  if (!description || typeof description !== 'string') {
    return { wordCount: 0, isCompliant: true, overflow: 0 };
  }
  const words = description.trim().split(/\s+/).filter(Boolean);
  const wordCount = words.length;
  return {
    wordCount,
    isCompliant: wordCount <= maxWords,
    overflow: Math.max(0, wordCount - maxWords),
  };
}

export function calculateStepperProgress(stage: IntakeStage): number {
  switch (stage) {
    case 'PARSING': return 25;
    case 'EXTRACTING_PRIMARY': return 50;
    case 'SELF_REFLECTION': return 75;
    case 'BASELINE_COMMITTED': return 100;
    default: return 0;
  }
}

export function getStepperStepStatus(
  stepIndex: number,
  currentStepIndex: number,
  isError: boolean = false
): StepStatus {
  if (isError && stepIndex === currentStepIndex) return 'error';
  if (stepIndex < currentStepIndex) return 'completed';
  if (stepIndex === currentStepIndex) return 'active';
  return 'upcoming';
}

export function getAssetCategoryBadgeProps(assetType: string): CategoryBadgeProps {
  const normalized = (assetType || '').trim().toLowerCase();
  switch (normalized) {
    case 'music':
    case 'music_cue':
      return { label: 'MUSIC CUE', bg: 'bg-indigo-950/80', text: 'text-indigo-300', border: 'border-indigo-500/50', iconName: 'Music' };
    case 'footage':
    case 'clip':
      return { label: 'ARCHIVAL FOOTAGE', bg: 'bg-sky-950/80', text: 'text-sky-300', border: 'border-sky-500/50', iconName: 'Film' };
    case 'brand':
    case 'trademark':
      return { label: 'TRADEMARK', bg: 'bg-cyan-950/80', text: 'text-cyan-300', border: 'border-cyan-500/50', iconName: 'Tag' };
    case 'artwork':
    case 'art':
      return { label: 'ARTWORK', bg: 'bg-purple-950/80', text: 'text-purple-300', border: 'border-purple-500/50', iconName: 'Palette' };
    case 'prop':
      return { label: 'PROP', bg: 'bg-amber-950/80', text: 'text-amber-300', border: 'border-amber-500/50', iconName: 'Box' };
    case 'likeness':
      return { label: 'LIKENESS', bg: 'bg-rose-950/80', text: 'text-rose-300', border: 'border-rose-500/50', iconName: 'User' };
    default:
      return { label: normalized ? normalized.toUpperCase() : 'OTHER', bg: 'bg-slate-800', text: 'text-slate-300', border: 'border-slate-700', iconName: 'Film' };
  }
}

export const getClaimCategoryStyle = getAssetCategoryBadgeProps;

export function detectDialogueQuotes(text: string): boolean {
  if (!text) return false;
  return /"[^"]*"|'[^']*'/.test(text);
}

export function getConfidentialityBadgeProps(
  description: string,
  targetWordLimit: number = 20
): ConfidentialityBadgeProps {
  const clean = (description || '').trim();
  const words = clean ? clean.split(/\s+/) : [];
  const wordCount = words.length;
  const hasDialogue = detectDialogueQuotes(clean);
  const isConfidential = wordCount <= targetWordLimit && wordCount > 0;

  if (isConfidential) {
    return {
      isConfidential: true,
      label: 'CONFIDENTIAL / ZERO-SPOILER',
      wordCount,
      bg: 'bg-emerald-950/80',
      text: 'text-emerald-300',
      border: 'border-emerald-500/50',
      iconName: 'ShieldCheck',
      hasDialogue,
    };
  }

  return {
    isConfidential: false,
    label: `EXCEEDS ${targetWordLimit} WORDS`,
    wordCount,
    bg: 'bg-amber-950/80',
    text: 'text-amber-300',
    border: 'border-amber-500/50',
    iconName: 'AlertTriangle',
    hasDialogue,
  };
}
