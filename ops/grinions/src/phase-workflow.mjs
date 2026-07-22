import { checkpointedSideEffect } from './checkpoints.mjs';

const REQUIRED_PHASE_FIELDS = ['initiativeId', 'phaseId', 'openspecId', 'branch', 'risk'];
const MAX_BEADS_PER_PHASE = 1000;

function explicitApproval(record) {
  return Boolean(
    record
    && record.approved === true
    && typeof record.approvedBy === 'string'
    && record.approvedBy.trim()
    && typeof record.approvedAt === 'string'
    && record.approvedAt.trim()
    && typeof record.evidence === 'string'
    && record.evidence.trim(),
  );
}

function destructiveApproval(phase, actionId) {
  const approvals = phase.approvals?.destructiveActions;
  if (!Array.isArray(approvals)) return null;
  return approvals.find((item) => String(item?.id) === String(actionId)) || null;
}

function approvalRequired(phase, kind, details, state = {}) {
  return {
    phaseId: phase.phaseId,
    status: 'approval_required',
    approval: { kind, ...details },
    ...state,
  };
}

export function validatePhaseRequest(request) {
  for (const field of REQUIRED_PHASE_FIELDS) {
    if (!request?.[field]) throw new TypeError(`phase request missing ${field}`);
  }
  if (!['low', 'medium', 'high'].includes(request.risk)) {
    throw new TypeError(`unsupported phase risk: ${request.risk}`);
  }
  if (request.destructiveActions && !Array.isArray(request.destructiveActions)) {
    throw new TypeError('destructiveActions must be an array when provided');
  }
  if (request.approvals && (typeof request.approvals !== 'object' || Array.isArray(request.approvals))) {
    throw new TypeError('approvals must be an object when provided');
  }
  return request;
}

export async function runPhase(ctx, request, services) {
  const phase = validatePhaseRequest(request);

  const hydrated = await ctx.step('hydrate-context', () => services.hydrateContext(phase));
  await ctx.step('validate-spec', () => services.validateSpec(phase, hydrated));
  const baseline = await ctx.step('capture-baseline', () => services.captureBaseline(phase));
  const rollback = await ctx.step('write-rollback-receipt', () => services.writeRollbackReceipt(phase, baseline));
  const workspace = await ctx.step('provision-workspace', () => services.provisionWorkspace(phase, baseline));

  for (const action of phase.destructiveActions || []) {
    const actionId = String(action.id || action.name || action).replace(/[^a-zA-Z0-9._-]+/g, '-');
    const approval = destructiveApproval(phase, actionId);
    if (!explicitApproval(approval)) {
      return approvalRequired(
        phase,
        'destructive_action',
        { actionId, action },
        { baseline, rollback, workspace },
      );
    }
    await ctx.step(`destructive-action-approval:${actionId}`, () =>
      services.recordApproval(phase, {
        kind: 'destructive_action',
        actionId,
        action,
        approval,
      }),
    );
  }

  const beads = [];
  for (let iteration = 0; iteration < MAX_BEADS_PER_PHASE; iteration += 1) {
    const ready = await ctx.step(`select-ready-bead:${iteration}`, () => services.selectReadyBead(phase, workspace));

    if (!ready) {
      const status = await ctx.step(`phase-bead-status:${iteration}`, () => services.phaseBeadStatus(phase, workspace));
      if (status.total === 0) throw new Error(`NO_PHASE_BEADS:${phase.phaseId}`);
      if (status.open > 0) {
        throw new Error(`PHASE_BEADS_BLOCKED:${phase.phaseId}:${status.open}`);
      }
      break;
    }

    const beadId = ready.id;
    const claimed = await ctx.step(`claim-bead:${beadId}`, () => services.claimBead(phase, workspace, ready));
    const packet = await ctx.step(`compile-bead:${beadId}`, () => services.compileBead(phase, workspace, claimed));
    const execution = await ctx.step(`execute-bead:${beadId}`, () => services.executeBead(phase, workspace, claimed, packet));
    const integration = await ctx.step(`integrate-bead:${beadId}`, () => services.integrateBead(phase, workspace, claimed, execution));
    const verification = await ctx.step(`verify-bead:${beadId}`, () => services.verifyBead(phase, workspace, claimed, integration));
    const closed = await ctx.step(`close-bead:${beadId}`, () => services.closeBead(phase, workspace, claimed, integration, verification));
    beads.push({ id: beadId, integration, verification, closed });
  }

  if (beads.length >= MAX_BEADS_PER_PHASE) {
    throw new Error(`PHASE_BEAD_LIMIT_EXCEEDED:${phase.phaseId}:${MAX_BEADS_PER_PHASE}`);
  }

  await ctx.step('local-verification', () => services.verifyLocal(phase, workspace, beads));
  await ctx.step('phase-verification', () => services.verifyPhase(phase, workspace));

  const pr = await checkpointedSideEffect(ctx, 'create-or-update-pr', (idempotencyKey) =>
    services.createOrUpdatePr(phase, { idempotencyKey, baseline, rollback, workspace, beads }),
  );

  await ctx.step('pr-watch', () => services.watchPr(phase, pr));
  const judgment = await ctx.step('judge', () => services.judge(phase, pr));
  if (!judgment?.passed) throw new Error(`PHASE_JUDGE_FAILED:${phase.phaseId}`);

  if (phase.risk === 'high') {
    const approval = phase.approvals?.highRiskMerge;
    if (!explicitApproval(approval)) {
      return approvalRequired(
        phase,
        'high_risk_merge',
        { prNumber: pr.number || null, prUrl: pr.url || null },
        { baseline, rollback, workspace, beads, pr, judgment },
      );
    }
    await ctx.step('high-risk-merge-approval', () => services.recordApproval(phase, {
      kind: 'high_risk_merge',
      approval,
      pr,
      judgment,
    }));
  }

  const merge = await checkpointedSideEffect(ctx, 'squash-merge', (idempotencyKey) =>
    services.squashMerge(phase, pr, { idempotencyKey, judgment }),
  );

  const postMerge = await ctx.step('post-merge-verification', () => services.verifyPostMerge(phase, merge));
  if (!postMerge?.passed) throw new Error(`POST_MERGE_VERIFY_FAILED:${phase.phaseId}`);
  await ctx.step('attest', () => services.attest(phase, { baseline, rollback, workspace, beads, pr, judgment, merge, postMerge }));

  return { phaseId: phase.phaseId, status: 'completed', baseline, rollback, workspace, beads, pr, judgment, merge, postMerge };
}
