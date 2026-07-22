import { access } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const required = [
  'AGENTS.md',
  'README.md',
  'openspec/config.yaml',
  '.ralphy/config.yaml',
  'ops/grinions/src/phase-workflow.mjs',
  'ops/grinions/src/absurd-runtime.mjs',
  'ops/grinions/src/services.mjs',
  'ops/grinions/test/idempotency.test.mjs',
];

for (const path of required) await access(resolve(repoRoot, path));
console.log(JSON.stringify({ gate: 'grinions-structure', passed: true, checked: required.length, repoRoot }));
