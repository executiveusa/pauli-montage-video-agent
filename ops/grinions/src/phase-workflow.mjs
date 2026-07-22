import { checkpointedSideEffect } from './checkpoints.mjs';

const REQUIRED_PHASE_FIELDS = ['initiativeId', 'phaseId', 'openspecId', 'branch', 'risk'];

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
    await ctx.step(`destructive-action-approval:${actionId}`, () =>
      services.requireDestructiveApproval(phase, action, workspace),
    );
  }

  const execution = await ctx.step('execute-beads', () => services.executeBeads(phase, workspace));
  const integration = await ctx.step('integrate-beads', () => services.integrateBeads(phase, workspace, execution));
  await ctx.step('local-verification', () => services.verifyLocal(phase, workspace, integration));
  await ctx.step('phase-verification', () => services.verifyPhase(phase, workspace));

  const pr = await checkpointedSideEffect(ctx, 'create-or-update-pr', (idempotencyKey) =>
    services.createOrUpdatePr(phase, { idempotencyKey, baseline, rollback, workspace, integration }),
  );

  await ctx.step('pr-watch', () => services.watchPr(phase, pr));
  const judgment = await ctx.step('judge', () => services.judge(phase, pr));
  if (!judgment?.passed) throw new Error(`PHASE_JUDGE_FAILED:${phase.phaseId}`);

  if (phase.risk === 'high') {
    await ctx.step('high-risk-merge-approval', () => services.requireHighRiskApproval(phase, pr));
  }

  const merge = await checkpointedSideEffect(ctx, 'squash-merge', (idempotencyKey) =>
    services.squashMerge(phase, pr, { idempotencyKey, judgment }),
  );

  const postMerge = await ctx.step('post-merge-verification', () => services.verifyPostMerge(phase, merge));
  if (!postMerge?.passed) throw new Error(`POST_MERGE_VERIFY_FAILED:${phase.phaseId}`);
  await ctx.step('attest', () => services.attest(phase, { baseline, rollback, workspace, integration, pr, judgment, merge, postMerge }));

  return { phaseId: phase.phaseId, baseline, rollback, workspace, integration, pr, judgment, merge, postMerge };
}
