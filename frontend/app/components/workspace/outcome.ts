import { record } from './model';

const rows = (value: unknown) => Array.isArray(value) ? value.map(record) : [];

export function productionOutcome(snapshot: unknown, missionValue: unknown, automationValue: unknown) {
  const saved = record(snapshot), mission = record(missionValue), automation = record(automationValue);
  const claims = rows(saved.claims).filter(c => c.state !== 'removed');
  const approved = claims.filter(c => ['carried_forward', 're_attested'].includes(String(c.state)) && record(c.decision).action === 'sign_off');
  const preserved = approved.filter(c => c.state === 'carried_forward').length;
  const questions = rows(automation.clarifications).filter(q => q.status === 'PENDING');
  const active = ['QUEUED', 'PROCESSING'].includes(String(mission.status));
  const blockers = claims.length - approved.length;
  const errors = claims.filter(c => c.investigation_error).length;
  const calls = Object.values(record(mission.calls)).map(record);
  const completedCalls = calls.filter(c => c.status === 'COMPLETED').length;
  const changed = claims.filter(c => rows(c.change_summary).length > 0).length;
  const failed = mission.status === 'FAILED' || mission.outcome === 'NEEDS_ATTENTION' || errors > 0;
  const title = active ? 'A change is being investigated.' : failed ? 'Research needs attention.' : !claims.length ? 'Your next production change starts here.' :
    blockers === 0 ? 'All recorded claims have reviewer approval.' : questions.length ? 'The next step needs production information.' : 'The next step needs reviewer authority.';
  const next = active ? ['Follow the investigation', '/investigations', 'The worker is processing the received change within its authorized allowance.'] :
    failed ? ['Inspect the interruption', '/investigations', 'Inspect the recorded failure before relying on this result.'] :
    !claims.length ? ['Add the first cut', '/revisions', 'Add a complete screenplay or cue sheet to establish the first review record.'] :
    questions.length ? ['Answer the open questions', '/inbox', `${questions.length} open question${questions.length === 1 ? '' : 's'} retain their context and resume when matching evidence arrives.`] :
    blockers ? ['Open the review queue', '/decisions', `${blockers} claim${blockers === 1 ? '' : 's'} still require an authorized decision.`] :
    ['Prepare the draft schedule', '/delivery', 'Inspect the recorded scope and supporting evidence before the delivery handoff.'];
  const triggerKind = String(record(mission.trigger).kind || '');
  const changeDescription = triggerKind === 'agreement' ? 'Supporting document reassessed' : triggerKind === 'evidence' ? 'Relied-on sources checked' : triggerKind === 'directive' ? 'Reviewer directive investigated' :
    record(saved.comparison).baseline_snapshot_id ? `${changed} creative uses changed` : 'First review baseline';
  return { title, next, active, preserved, approved: approved.length, blockers, changed, changeDescription, completedCalls,
    total: claims.length, trigger: String(record(mission.trigger).name || 'No source event recorded'),
    baseline: Boolean(record(saved.comparison).baseline_snapshot_id) };
}
