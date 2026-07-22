import { access } from 'node:fs/promises';

const required = [
  'AGENTS.md',
  'README.md',
  'openspec/changes/phase-00-grinions-harness/proposal.md',
  'openspec/changes/phase-00-grinions-harness/tasks.md',
  '.ralphy/config.yaml',
  'ops/grinions/src/phase-workflow.mjs',
  'ops/grinions/src/absurd-runtime.mjs',
  'ops/grinions/test/idempotency.test.mjs',
];

for (const path of required) await access(path);
console.log(JSON.stringify({ gate: 'phase-00-structure', passed: true, checked: required.length }));
