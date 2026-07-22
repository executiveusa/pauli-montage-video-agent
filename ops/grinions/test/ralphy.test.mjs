import assert from 'node:assert/strict';
import test from 'node:test';
import { buildRalphyArgs } from '../src/ralphy.mjs';

test('Ralphy is always isolated from merge authority', () => {
  const args = buildRalphyArgs({ taskFile: 'tasks.md', baseBranch: 'phase/00', maxRetries: 3 });
  assert.equal(args.includes('--branch-per-task'), true);
  assert.equal(args.includes('--no-merge'), true);
  assert.equal(args.includes('--create-pr'), false);
  assert.equal(args.includes('--fast'), false);
  assert.equal(args.includes('--no-tests'), false);
  assert.equal(args.includes('--no-lint'), false);
});
