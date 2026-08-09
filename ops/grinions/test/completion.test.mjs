import assert from 'node:assert/strict';
import test from 'node:test';
import {
  classifyCompletionEvidence,
  parseWorkIdentity,
  workIdentityMarker,
} from '../src/completion.mjs';

const identity = {
  repository: 'executiveusa/pauli-montage-video-agent',
  initiativeId: 'yappy-upgrade',
  openspecId: 'upgrade-00-grinions-replay-guard',
  phaseId: 'upgrade-00',
};
const branch = 'agent/grinions-completed-phase-guard';

function pr(overrides = {}) {
  return {
    number: 40,
    state: 'CLOSED',
    mergedAt: '2026-08-09T12:00:00Z',
    mergeCommit: { oid: 'merge-sha' },
    headRefName: branch,
    body: workIdentityMarker(identity),
    integratedIntoMain: true,
    ...overrides,
  };
}

function receipt(overrides = {}) {
  return {
    schemaVersion: 1,
    phaseId: identity.phaseId,
    openspecId: identity.openspecId,
    risk: 'medium',
    completedAt: '2026-08-09T12:00:00Z',
    baselineMainSha: 'base',
    beads: [{ id: 'bead-1', headSha: 'bead-head', verified: true, closedStatus: 'closed' }],
    pullRequest: { number: 40, url: null, headSha: 'phase-head' },
    judgment: { passed: true, unresolvedReviewThreads: 0 },
    merge: { sha: 'merge-sha', mergedAt: '2026-08-09T12:00:00Z' },
    postMerge: { passed: true, mainSha: 'main-sha' },
    rollback: { baselineCaptured: true, receiptPath: 'ops/rollback/phase-upgrade-00.json' },
    ...overrides,
  };
}

test('identity marker round-trips the immutable composite identity', () => {
  const { phaseId: _displayOnly, ...immutableIdentity } = identity;
  assert.deepEqual(parseWorkIdentity(workIdentityMarker(identity)), immutableIdentity);
});

test('matching merged PR integrated into main is already completed without a local receipt', () => {
  const result = classifyCompletionEvidence({ identity, branch, pullRequests: [pr()] });
  assert.equal(result.status, 'already_completed');
  assert.equal(result.mergeSha, 'merge-sha');
});

test('local-only receipt is inconsistent and never authoritative completion evidence', () => {
  const result = classifyCompletionEvidence({
    identity,
    branch,
    pullRequests: [],
    receipt: receipt(),
  });
  assert.equal(result.status, 'inconsistent');
  assert.equal(result.reason, 'receipt_without_canonical_pull_request');
});

test('open, closed-unmerged, mismatched and non-ancestor PR evidence fails closed', () => {
  const cases = [
    pr({ state: 'OPEN', mergedAt: null, mergeCommit: null }),
    pr({ state: 'CLOSED', mergedAt: null, mergeCommit: null }),
    pr({ body: workIdentityMarker({ ...identity, openspecId: 'other' }) }),
    pr({ integratedIntoMain: false }),
  ];
  for (const candidate of cases) {
    const result = classifyCompletionEvidence({ identity, branch, pullRequests: [candidate] });
    assert.equal(result.status, 'inconsistent');
  }
});

test('no receipt, PR or conflicting branch history is not completed', () => {
  const result = classifyCompletionEvidence({ identity, branch, pullRequests: [] });
  assert.equal(result.status, 'not_completed');
});

test('duplicate matching PR history is ambiguous and blocks replay', () => {
  const result = classifyCompletionEvidence({ identity, branch, pullRequests: [pr(), pr({ number: 41 })] });
  assert.equal(result.status, 'inconsistent');
  assert.equal(result.reason, 'ambiguous_completion_history');
});

test('receipt contradictions block canonical completion evidence', () => {
  const canonical = pr({ headRefOid: 'phase-head' });
  const contradictions = [
    receipt({ pullRequest: { number: 99, headSha: 'phase-head' } }),
    receipt({ pullRequest: { number: 40, headSha: 'wrong-head' } }),
    receipt({ merge: { sha: 'wrong-merge', mergedAt: '2026-08-09T12:00:00Z' } }),
    receipt({ phaseId: 'different-phase' }),
    receipt({ judgment: { passed: false } }),
  ];
  for (const receipt of contradictions) {
    const result = classifyCompletionEvidence({ identity, branch, pullRequests: [canonical], receipt });
    assert.equal(result.status, 'inconsistent');
  }
});

test('a receipt requires a verified post-merge Git ancestry chain', () => {
  const canonical = pr({ headRefOid: 'phase-head' });
  const result = classifyCompletionEvidence({
    identity,
    branch,
    pullRequests: [canonical],
    receipt: receipt(),
    receiptGitEvidence: {
      postMergeShaValid: false,
      mergeIntegratedAtPostMerge: false,
      postMergeIntegratedIntoMain: false,
    },
  });
  assert.equal(result.status, 'inconsistent');
  assert.equal(result.reason, 'receipt_post_merge_sha_invalid');
});

test('malformed markers on unrelated branches do not deny every phase', () => {
  const result = classifyCompletionEvidence({
    identity,
    branch,
    pullRequests: [{ number: 2, headRefName: 'unrelated', body: '<!-- grinions-work-identity: {bad} -->' }],
  });
  assert.equal(result.status, 'not_completed');
});

test('an identity marker on a noncanonical branch cannot prove or block completion', () => {
  const canonicalBranch = 'grinions/yappy-upgrade/upgrade-00-canonical';
  const result = classifyCompletionEvidence({
    identity,
    branch,
    canonicalBranch,
    pullRequests: [pr({ headRefName: 'attacker/unrelated' })],
  });
  assert.equal(result.status, 'not_completed');
});
