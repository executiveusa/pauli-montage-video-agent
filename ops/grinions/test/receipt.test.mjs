import assert from 'node:assert/strict';
import test from 'node:test';
import { buildPhaseReceipt, validatePhaseReceipt } from '../src/receipt.mjs';

const phase = {
  phaseId: '00',
  openspecId: 'phase-00-grinions-harness',
  risk: 'medium',
};

const evidence = {
  baseline: { mainSha: 'base-sha' },
  rollback: { baselineMainSha: 'base-sha' },
  beads: [{
    id: 'bd-a1b2',
    integration: { headSha: 'bead-head' },
    verification: { passed: true },
    closed: { status: 'closed' },
  }],
  pr: { number: 42 },
  judgment: { passed: true, headRefOid: 'phase-head', unresolvedReviewThreads: 0 },
  merge: { sha: 'merge-sha', mergedAt: '2026-07-22T00:00:00Z' },
  postMerge: { passed: true, mainSha: 'main-sha' },
};

test('buildPhaseReceipt emits a stable versioned evidence contract', () => {
  const receipt = buildPhaseReceipt(phase, evidence, '2026-07-22T01:00:00Z');
  assert.equal(receipt.schemaVersion, 1);
  assert.equal(receipt.phaseId, '00');
  assert.equal(receipt.merge.sha, 'merge-sha');
  assert.equal(receipt.postMerge.mainSha, 'main-sha');
  assert.deepEqual(receipt.beads, [{ id: 'bd-a1b2', headSha: 'bead-head', verified: true, closedStatus: 'closed' }]);
  assert.equal('workspace' in receipt, false);
});

test('receipt validation rejects unverified or incomplete completion evidence', () => {
  assert.throws(
    () => buildPhaseReceipt(phase, { ...evidence, judgment: { passed: false } }),
    /passed judgment/,
  );
  assert.throws(
    () => buildPhaseReceipt(phase, { ...evidence, merge: {} }),
    /merge\.sha/,
  );
  assert.throws(
    () => validatePhaseReceipt({ schemaVersion: 99 }),
    /unsupported phase receipt schemaVersion/,
  );
});
