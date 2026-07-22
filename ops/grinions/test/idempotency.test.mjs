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

function services(counters) {
  return {
    hydrateContext: async () => true,
    validateSpec: async () => true,
    captureBaseline: async () => ({ mainSha: 'base' }),
    writeRollbackReceipt: async () => ({ ok: true }),
    provisionWorkspace: async () => ({ path: '/tmp/worktree', branch: phase.branch }),
    executeBeads: async () => ({ ok: true, taskBranches: [] }),
    integrateBeads: async () => ({ headSha: 'phase-head', integratedBranches: [] }),
    verifyLocal: async () => true,
    verifyPhase: async () => true,
    createOrUpdatePr: async (_phase, meta) => {
      counters.pr += 1;
      assert.match(meta.idempotencyKey, /create-or-update-pr/);
      return { number: 42 };
    },
    watchPr: async () => ({ passed: true }),
    judge: async () => ({ passed: true, headRefOid: 'phase-head' }),
    requireHighRiskApproval: async () => true,
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
  await runPhase(new MemoryContext(persisted), phase, services(counters));
  await runPhase(new MemoryContext(persisted), phase, services(counters));
  assert.deepEqual(counters, { pr: 1, merge: 1 });
});

test('a simulated restart resumes after completed checkpoints', async () => {
  const persisted = new Map();
  const counters = { pr: 0, merge: 0 };
  const first = services(counters);
  first.executeBeads = async () => { throw new Error('simulated worker death'); };
  await assert.rejects(() => runPhase(new MemoryContext(persisted), phase, first), /simulated worker death/);
  assert.equal(persisted.has('capture-baseline'), true);
  await runPhase(new MemoryContext(persisted), phase, services(counters));
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
