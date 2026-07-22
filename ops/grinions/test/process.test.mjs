import assert from 'node:assert/strict';
import test from 'node:test';
import { run } from '../src/process.mjs';

test('run captures normal process output', async () => {
  const result = await run(process.execPath, ['-e', "process.stdout.write('ok')"], { timeoutMs: 1000 });
  assert.equal(result.stdout, 'ok');
});

test('run terminates commands that exceed the timeout', async () => {
  await assert.rejects(
    () => run(process.execPath, ['-e', 'setTimeout(() => {}, 1000)'], { timeoutMs: 50 }),
    (error) => error.code === 'TIMEOUT',
  );
});

test('run terminates commands that exceed the output cap', async () => {
  await assert.rejects(
    () => run(process.execPath, ['-e', "process.stdout.write('x'.repeat(10000))"], { maxOutputBytes: 1000 }),
    (error) => error.code === 'OUTPUT_LIMIT',
  );
});
