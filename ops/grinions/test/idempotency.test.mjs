import assert from 'node:assert/strict';
import test from 'node:test';
import { runPhase } from '../src/phase-workflow.mjs';

class MemoryContext {
  constructor(checkpoints = new Map()) {
    this.taskID = 'task-123';
    this.checkpoints = checkpoints;
  }
  async step(name, fn) {
    if (this.checkpoints.has(name)) return this.checkpoints.get(name);
    const value = await fn();
    this.checkpoints.set(name, value);
    return value;
  }
}

const phase = {
  initiativeId: 'yappy-clipz',
  phaseId: '00',
  openspecId: 'phase-00-grinions-harness',
  branch: 'phase/00-grinions-harness',
  risk: 'medium',
};

function services(counters, beadState = { closed: false }) {
  return {
    hydrateContext: async () => true,
    validateSpec: async () => true,
    captureBaseline: async () => ({ mainSha: 'base' }),
    writeRollbackReceipt: async () => ({ ok: true }),
    provisionWorkspace: async () => ({ path: '/tmp/worktree', branch: phase.branch }),
    selectReadyBead: async () => beadState.closed ? null : { id: 'bd-a1b2', title: 'Bounded task' },
    phaseBeadStatus: async () => ({ total: 1, open: beadState.closed ? 0 : 1, closed: beadState.closed ? 1 : 0 }),
    claimBead: async () => ({ id: 'bd-a1b2', title: 'Bounded task' }),
    compileBead: async () => ({ beadId: 'bd-a1b2', taskFile: '/tmp/bd-a1b2.md' }),
    executeBead: async () => ({ taskBranches: ['ralphy/bead-bd-a1b2-bounded-task'] }),
    integrateBead: async () => ({ beadId: 'bd-a1b2', headSha: 'phase-head', integratedBranches: ['ralphy/bead-bd-a1b2-bounded-task'] }),
    verifyBead: async () => ({ beadId: 'bd-a1b2', passed: true, requiredEvidence: ['tests'] }),
    closeBead: async () => {
      beadState.closed = true;
      return { id: 'bd-a1b2', status: 'closed' };
    },
    verifyLocal: async () => true,
    verifyPhase: async () => true,
    createOrUpdatePr: async (_phase, meta) => {
      counters.pr += 1;
      assert.match(meta.idempotencyKey, /create-or-update-pr/);
      return { number: 42 };
    },
    watchPr: async () => ({ passed: true }),
    judge: async () => ({ passed: true, headRefOid: 'phase-head' }),
    squashMerge: async (_phase, _pr, meta) => {
      counters.merge += 1;
      assert.match(meta.idempotencyKey, /squash-merge/);
      assert.equal(meta.judgment.passed, true);
      return { sha: 'squash' };
    },
    verifyPostMerge: async () => ({ passed: true }),
    attest: async () => true,
  };
}

test('replay with persisted checkpoints does not duplicate PR or merge side effects', async () => {
  const persisted = new Map();
  const counters = { pr: 0, merge: 0 };
  const beadState = { closed: false };
  const svc = services(counters, beadState);
  await runPhase(new MemoryContext(persisted), phase, svc);
  await runPhase(new MemoryContext(persisted), phase, svc);
  assert.deepEqual(counters, { pr: 1, merge: 1 });
});

test('a simulated restart resumes after completed Bead checkpoints', async () => {
  const persisted = new Map();
  const counters = { pr: 0, merge: 0 };
  const beadState = { closed: false };
  const first = services(counters, beadState);
  first.executeBead = async () => { throw new Error('simulated worker death'); };
  await assert.rejects(() => runPhase(new MemoryContext(persisted), phase, first), /simulated worker death/);
  assert.equal(persisted.has('capture-baseline'), true);
  assert.equal(persisted.has('claim-bead:bd-a1b2'), true);

  const resumed = services(counters, beadState);
  await runPhase(new MemoryContext(persisted), phase, resumed);
  assert.deepEqual(counters, { pr: 1, merge: 1 });
});

test('restart after PR creation reuses the PR checkpoint and merges exactly once', async () => {
  const persisted = new Map();
  const counters = { pr: 0, merge: 0 };
  const beadState = { closed: false };
  const first = services(counters, beadState);
  first.watchPr = async () => { throw new Error('simulated crash after PR creation'); };

  await assert.rejects(
    () => runPhase(new MemoryContext(persisted), phase, first),
    /simulated crash after PR creation/,
  );
  assert.equal(persisted.has('create-or-update-pr'), true);
  assert.deepEqual(counters, { pr: 1, merge: 0 });

  const resumed = services(counters, beadState);
  await runPhase(new MemoryContext(persisted), phase, resumed);
  assert.deepEqual(counters, { pr: 1, merge: 1 });
});

test('a failed judge blocks squash merge', async () => {
  const counters = { pr: 0, merge: 0 };
  const blocked = services(counters);
  blocked.judge = async () => ({ passed: false });
  await assert.rejects(() => runPhase(new MemoryContext(), phase, blocked), /PHASE_JUDGE_FAILED/);
  assert.equal(counters.merge, 0);
});

test('failed post-merge verification blocks attestation', async () => {
  const counters = { pr: 0, merge: 0 };
  let attested = false;
  const broken = services(counters);
  broken.verifyPostMerge = async () => ({ passed: false });
  broken.attest = async () => { attested = true; };
  await assert.rejects(() => runPhase(new MemoryContext(), phase, broken), /POST_MERGE_VERIFY_FAILED/);
  assert.equal(counters.merge, 1);
  assert.equal(attested, false);
});

test('declared destructive actions return approval_required before any Bead executes', async () => {
  const counters = { pr: 0, merge: 0 };
  let selected = false;
  const blocked = services(counters);
  blocked.selectReadyBead = async () => { selected = true; return null; };
  const destructive = { ...phase, destructiveActions: [{ id: 'drop-table' }] };
  const result = await runPhase(new MemoryContext(), destructive, blocked);
  assert.equal(result.status, 'approval_required');
  assert.equal(result.approval.kind, 'destructive_action');
  assert.equal(result.approval.actionId, 'drop-table');
  assert.equal(selected, false);
  assert.deepEqual(counters, { pr: 0, merge: 0 });
});

test('explicit destructive approval evidence allows the phase to proceed', async () => {
  const counters = { pr: 0, merge: 0 };
  const destructive = {
    ...phase,
    destructiveActions: [{ id: 'drop-table' }],
    approvals: {
      destructiveActions: [{
        id: 'drop-table',
        approved: true,
        approvedBy: 'owner',
        approvedAt: '2026-07-22T01:00:00Z',
        evidence: 'explicit test approval',
      }],
    },
  };
  const result = await runPhase(new MemoryContext(), destructive, services(counters));
  assert.equal(result.status, 'completed');
  assert.deepEqual(counters, { pr: 1, merge: 1 });
});

test('high-risk phases return approval_required after judgment without attempting merge', async () => {
  const counters = { pr: 0, merge: 0 };
  const result = await runPhase(new MemoryContext(), { ...phase, risk: 'high' }, services(counters));
  assert.equal(result.status, 'approval_required');
  assert.equal(result.approval.kind, 'high_risk_merge');
  assert.deepEqual(counters, { pr: 1, merge: 0 });
});

test('a phase cannot silently continue without any phase Beads', async () => {
  const counters = { pr: 0, merge: 0 };
  const empty = services(counters);
  empty.selectReadyBead = async () => null;
  empty.phaseBeadStatus = async () => ({ total: 0, open: 0, closed: 0 });
  await assert.rejects(() => runPhase(new MemoryContext(), phase, empty), /NO_PHASE_BEADS/);
  assert.deepEqual(counters, { pr: 0, merge: 0 });
});

test('open phase Beads with none ready fail as blocked work', async () => {
  const counters = { pr: 0, merge: 0 };
  const blocked = services(counters);
  blocked.selectReadyBead = async () => null;
  blocked.phaseBeadStatus = async () => ({ total: 2, open: 2, closed: 0 });
  await assert.rejects(() => runPhase(new MemoryContext(), phase, blocked), /PHASE_BEADS_BLOCKED:00:2/);
});
