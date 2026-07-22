import assert from 'node:assert/strict';
import { appendFile, readFile, rm } from 'node:fs/promises';
import test from 'node:test';
import { Absurd } from 'absurd-sdk';

const db = process.env.ABSURD_DATABASE_URL;
const enabled = Boolean(db);

async function lineCount(path) {
  try {
    const value = await readFile(path, 'utf8');
    return value.trim() ? value.trim().split('\n').length : 0;
  } catch {
    return 0;
  }
}

test('Absurd retry replays checkpoints without duplicating completed side effects', { skip: !enabled, timeout: 30000 }, async () => {
  const marker = `/tmp/grinions-absurd-${process.pid}.log`;
  await rm(marker, { force: true });
  const app = new Absurd({ db, queueName: 'grinions_test' });

  app.registerTask({ name: 'checkpoint-proof', defaultMaxAttempts: 3 }, async (_params, ctx) => {
    const sideEffect = await ctx.step('external-side-effect', async () => {
      await appendFile(marker, `${ctx.taskID}\n`, 'utf8');
      return { written: true };
    });

    const failure = await ctx.beginStep('fail-once');
    if (!failure.done) {
      await ctx.completeStep(failure, { simulated: true });
      throw new Error('simulated transient failure after checkpoint');
    }

    return { sideEffect, lines: await lineCount(marker) };
  });

  const worker = await app.startWorker({ concurrency: 1 });
  const { taskID } = await app.spawn('checkpoint-proof', {}, { queue: 'grinions_test' });
  const result = await app.awaitTaskResult(taskID, { timeout: 20 });

  assert.equal(result.state, 'completed');
  assert.equal(await lineCount(marker), 1);

  await worker.close();
  await app.close();
  await rm(marker, { force: true });
});
