'use client';

/**
 * Lienmark HITL Resumption Progress Stepper
 * Live execution progress stepper displaying the 4-phase unblocking pipeline:
 * Step 1: Clarification Resolved (Autonomous / Manual)
 * Step 2: Checkpoint Hydrated (State Restored)
 * Step 3: Targeted Agreement Verification (Signatures, Territory, Rights)
 * Step 4: Claim Clearance Updated (Ready for Counsel Sign-off)
 * Features animated glowing emerald transitions without full-page refresh.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState } from 'react';
import {
  CheckCircle2,
  Loader2,
  Clock,
  Cpu,
  Sparkles,
} from 'lucide-react';
import {
  ResumptionSession,
  ResumptionStepDetail,
  ResumptionStepStatus,
} from './resumption_types';
import {
  getStepStatusClasses,
  GOLDEN_RESUMPTION_SESSION,
} from './resumption_utils';
import { StepDetailDrawer } from './StepDetailDrawer';

export interface ResumptionProgressStepperProps {
  readonly session?: ResumptionSession;
  readonly onOpenAgreementViewer?: () => void;
  readonly onSignOff?: () => void;
  readonly className?: string;
}

function renderStepIcon(status: ResumptionStepStatus): React.ReactElement {
  if (status === 'completed') {
    return <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />;
  }
  if (status === 'in_progress') {
    return <Loader2 className="h-4 w-4 text-emerald-300 animate-spin" aria-hidden="true" />;
  }
  return <Clock className="h-4 w-4 text-slate-500" aria-hidden="true" />;
}

function renderStepBadge(step: ResumptionStepDetail): React.ReactElement {
  const styles = getStepStatusClasses(step.status);
  const statusLabel =
    step.status === 'completed'
      ? 'COMPLETED'
      : step.status === 'in_progress'
      ? 'PROCESSING'
      : 'PENDING';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-mono font-bold border uppercase ${styles.badgeClass}`}
    >
      {step.status === 'in_progress' && (
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
      )}
      {statusLabel}
    </span>
  );
}

interface StepCardProps {
  readonly step: ResumptionStepDetail;
  readonly isSelected: boolean;
  readonly onSelect: () => void;
}

const StepCard: React.FC<StepCardProps> = ({ step, isSelected, onSelect }) => {
  const styles = getStepStatusClasses(step.status);
  return (
    <div
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect()}
      className={`relative flex flex-col justify-between rounded-xl border p-3.5 cursor-pointer transition-all duration-300 ${
        styles.containerClass
      } ${
        isSelected
          ? 'ring-2 ring-emerald-400 border-emerald-400 shadow-[0_0_18px_rgba(16,185,129,0.3)]'
          : 'hover:border-slate-700 hover:bg-slate-900/60'
      }`}
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div
            className={`flex h-6 w-6 items-center justify-center rounded-full border text-xs font-mono font-bold ${styles.iconClass}`}
          >
            {renderStepIcon(step.status)}
          </div>
          {renderStepBadge(step)}
        </div>
        <div>
          <h4 className="text-xs font-bold text-slate-100 line-clamp-1">{step.title}</h4>
          <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5 leading-relaxed">
            {step.subtitle}
          </p>
        </div>
      </div>
      {step.completedAt && (
        <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
          <span>Timestamp:</span>
          <span className="text-emerald-400 font-semibold">{step.completedAt}</span>
        </div>
      )}
    </div>
  );
};

interface StepperHeaderProps {
  readonly checkpointId: string;
  readonly claimKey: string;
  readonly isAllComplete: boolean;
  readonly currentStep: number;
}

const StepperHeaderRibbon: React.FC<StepperHeaderProps> = ({
  checkpointId,
  claimKey,
  isAllComplete,
  currentStep,
}) => (
  <div className="flex flex-wrap items-center justify-between border-b border-slate-800/80 pb-3 gap-2">
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
        <Cpu className="h-4 w-4 text-emerald-400" aria-hidden="true" />
      </div>
      <div>
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
            Clearance Resumption Pipeline
          </h3>
          <span className="rounded bg-slate-800 border border-slate-700 px-1.5 py-0.2 text-[10px] font-mono text-emerald-300">
            Checkpoint: {checkpointId}
          </span>
        </div>
        <p className="text-[11px] text-slate-400">
          Target Claim: <span className="font-mono text-white">{claimKey}</span> &middot; Zero Token Waste
        </p>
      </div>
    </div>
    <div className="flex items-center gap-2">
      {isAllComplete ? (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/20 border border-emerald-400/50 px-3 py-1 text-[11px] font-mono font-bold text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)]">
          <Sparkles className="h-3 w-3 text-emerald-400 animate-pulse" />
          RESTORED &amp; READY
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-800 border border-slate-700 px-2.5 py-1 text-[11px] font-mono text-slate-300">
          <Loader2 className="h-3 w-3 text-emerald-400 animate-spin" />
          Step {currentStep} of 4
        </span>
      )}
    </div>
  </div>
);

export const ResumptionProgressStepper: React.FC<ResumptionProgressStepperProps> = ({
  session = GOLDEN_RESUMPTION_SESSION,
  onOpenAgreementViewer,
  onSignOff,
  className = '',
}) => {
  const [activeStepNumber, setActiveStepNumber] = useState<number>(session.currentStep);
  const activeStep = session.steps[activeStepNumber - 1] ?? session.steps[0];

  return (
    <div
      aria-label="Clearance Resumption Live Stepper"
      className={`rounded-xl border border-emerald-500/40 bg-[#0c1322]/95 p-5 shadow-[0_0_25px_rgba(16,185,129,0.15)] backdrop-blur-md space-y-4 ${className}`}
    >
      <StepperHeaderRibbon
        checkpointId={session.checkpointId}
        claimKey={session.claimKey}
        isAllComplete={session.isCompleted}
        currentStep={session.currentStep}
      />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {session.steps.map((step) => (
          <StepCard
            key={step.id}
            step={step}
            isSelected={activeStepNumber === step.stepNumber}
            onSelect={() => setActiveStepNumber(step.stepNumber)}
          />
        ))}
      </div>
      <StepDetailDrawer
        activeStep={activeStep}
        isAllComplete={session.isCompleted}
        onOpenAgreementViewer={onOpenAgreementViewer}
        onSignOff={onSignOff}
      />
    </div>
  );
};

export default ResumptionProgressStepper;
