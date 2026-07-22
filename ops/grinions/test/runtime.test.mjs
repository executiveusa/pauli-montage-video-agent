import assert from 'node:assert/strict';
import test from 'node:test';
import { createGrinionsRuntime } from '../src/absurd-runtime.mjs';
import { validatePhaseRequest } from '../src/phase-workflow.mjs';

test('runtime fails before SDK construction when the control-plane database is missing', async () => {
  const previous = process.env.ABSURD_DATABASE_URL;
  delete process.env.ABSURD_DATABASE_URL;
  try {
    await assert.rejects(
      () => createGrinionsRuntime({ db: '' }),
      /requires ABSURD_DATABASE_URL or options\.db/,
    );
  } finally {
    if (previous === undefined) delete process.env.ABSURD_DATABASE_URL;
    else process.env.ABSURD_DATABASE_URL = previous;
  }
});

test('phase request validation fails before durable enqueue for incomplete input', () => {
  assert.throws(
    () => validatePhaseRequest({ phaseId: '01' }),
    /phase request missing initiativeId/,
  );
  assert.throws(
    () => validatePhaseRequest({
      initiativeId: 'yappy-clipz',
      phaseId: '01',
      openspecId: 'phase-01',
      branch: 'phase/01',
      risk: 'unknown',
    }),
    /unsupported phase risk/,
  );
});
