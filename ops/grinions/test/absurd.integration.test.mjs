import assert from 'node:assert/strict';
import { access, appendFile, readFile, rm, writeFile } from 'node:fs/promises';
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

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

test('Absurd retry replays checkpoints without duplicating completed side effects', { skip: !enabled, timeout: 45000 }, async () => {
  const marker = `/tmp/grinions-absurd-${process.pid}.log`;
  const failMarker = `/tmp/grinions-absurd-${process.pid}.fail-once`;
  await rm(marker, { force: true });
  await rm(failMarker, { force: true });

  const app = new Absurd({ db, queueName: 'grinions_test' });

  app.registerTask({ name: 'checkpoint-proof', defaultMaxAttempts: 3 }, async (_params, ctx) => {
    const sideEffect = await ctx.step('external-side-effect', async () => {
      await appendFile(marker, `${ctx.taskID}\n`, 'utf8');
      return { written: true };
    });

    // Deliberately fail once *outside* a checkpoint. Absurd should retry the
    // task, replay the completed checkpoint above from Postgres, and continue.
    if (!(await exists(failMarker))) {
      await writeFile(failMarker, 'failed-once\n', 'utf8');
      throw new Error('simulated transient failure after checkpoint');
    }

    return { sideEffect, lines: await lineCount(marker) };
  });

  const workerPromise = app.startWorker({ concurrency: 1 });

  try {
    const { taskID } = await app.spawn(
      'checkpoint-proof',
      {},
      {
        queue: 'grinions_test',
        maxAttempts: 3,
        retryStrategy: { kind: 'fixed', delaySeconds: 1 },
      },
    );
    const result = await app.awaitTaskResult(taskID, { timeout: 30 });

    assert.equal(result.state, 'completed');
    assert.equal(await lineCount(marker), 1);
  } finally {
    await app.close();
    await Promise.race([
      workerPromise.catch(() => undefined),
      new Promise((resolve) => setTimeout(resolve, 2000)),
    ]);
    await rm(marker, { force: true });
    await rm(failMarker, { force: true });
  }
});
