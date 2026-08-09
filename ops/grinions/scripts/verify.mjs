import { access } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validatePhaseReceipt } from '../src/receipt.mjs';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const required = [
  'AGENTS.md',
  'README.md',
  'EMERALD_TABLETS.md',
  'openspec/config.yaml',
  '.ralphy/config.yaml',
  'ops/grinions/src/phase-workflow.mjs',
  'ops/grinions/src/completion.mjs',
  'ops/grinions/src/absurd-runtime.mjs',
  'ops/grinions/src/services.mjs',
  'ops/grinions/src/beads.mjs',
  'ops/grinions/src/receipt.mjs',
  'ops/grinions/test/idempotency.test.mjs',
  'ops/grinions/test/completion.test.mjs',
  'ops/grinions/test/services-completion.test.mjs',
  'ops/grinions/test/process.test.mjs',
  'ops/grinions/test/beads.test.mjs',
  'ops/grinions/test/receipt.test.mjs',
  'ops/grinions/test/runtime.test.mjs',
];

for (const path of required) await access(resolve(repoRoot, path));
validatePhaseReceipt({
  schemaVersion: 1,
  phaseId: 'verify',
  openspecId: 'verify-contract',
  risk: 'low',
  completedAt: '2026-01-01T00:00:00Z',
  baselineMainSha: 'baseline',
  beads: [{ id: 'verify-bead', headSha: 'bead-head', verified: true, closedStatus: 'closed' }],
  pullRequest: { number: 1, url: null, headSha: 'phase-head' },
  judgment: { passed: true, unresolvedReviewThreads: 0 },
  merge: { sha: 'merge', mergedAt: null },
  postMerge: { passed: true, mainSha: 'main' },
  rollback: { baselineCaptured: true, receiptPath: 'ops/rollback/phase-verify.json' },
});
console.log(JSON.stringify({ gate: 'grinions-structure', passed: true, checked: required.length, repoRoot }));
