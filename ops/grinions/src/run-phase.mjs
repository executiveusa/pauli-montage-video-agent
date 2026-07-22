import { readFile } from 'node:fs/promises';
import { createGrinionsRuntime } from './absurd-runtime.mjs';
import { validatePhaseRequest } from './phase-workflow.mjs';

const phaseFile = process.argv[2];
if (!phaseFile) throw new Error('usage: npm run run-phase -- <phase.json>');
const phase = validatePhaseRequest(JSON.parse(await readFile(phaseFile, 'utf8')));
const app = await createGrinionsRuntime();
try {
  const { taskID } = await app.spawn('grinions-phase', phase, { queue: process.env.GRINIONS_QUEUE || 'grinions' });
  console.log(JSON.stringify({ taskID, phaseId: phase.phaseId }));
} finally {
  await app.close();
}
