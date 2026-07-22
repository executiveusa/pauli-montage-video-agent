import { checkpointedSideEffect } from './checkpoints.mjs';

const REQUIRED_PHASE_FIELDS = ['initiativeId', 'phaseId', 'openspecId', 'branch', 'risk'];

export function validatePhaseRequest(request) {
  for (const field of REQUIRED_PHASE_FIELDS) {
    if (!request?.[field]) throw new TypeError(`phase request missing ${field}`);
  }
  if (!['low', 'medium', 'high'].includes(request.risk)) {
    throw new TypeError(`unsupported phase risk: ${request.risk}`);
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
  const execution = await ctx.step('execute-beads', () => services.executeBeads(phase, workspace));
  await ctx.step('local-verification', () => services.verifyLocal(phase, execution));
  await ctx.step('phase-verification', () => services.verifyPhase(phase));

  const pr = await checkpointedSideEffect(ctx, 'create-or-update-pr', (idempotencyKey) =>
    services.createOrUpdatePr(phase, { idempotencyKey, baseline, rollback }),
  );

  await ctx.step('pr-watch', () => services.watchPr(phase, pr));
  await ctx.step('judge', () => services.judge(phase, pr));

  if (phase.risk === 'high') {
    await ctx.step('high-risk-merge-approval', () => services.requireHighRiskApproval(phase, pr));
  }

  const merge = await checkpointedSideEffect(ctx, 'squash-merge', (idempotencyKey) =>
    services.squashMerge(phase, pr, { idempotencyKey }),
  );

  const postMerge = await ctx.step('post-merge-verification', () => services.verifyPostMerge(phase, merge));
  await ctx.step('attest', () => services.attest(phase, { baseline, pr, merge, postMerge }));

  return { phaseId: phase.phaseId, baseline, rollback, pr, merge, postMerge };
}
