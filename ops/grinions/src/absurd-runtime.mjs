import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runPhase } from './phase-workflow.mjs';
import { createShellServices } from './services.mjs';

const MODULE_DIR = dirname(fileURLToPath(import.meta.url));
export const DEFAULT_REPO_ROOT = resolve(MODULE_DIR, '../../..');

export async function createGrinionsRuntime(options = {}) {
  const db = options.db || process.env.ABSURD_DATABASE_URL;
  if (!db) {
    throw new Error('GRINIONS runtime requires ABSURD_DATABASE_URL or options.db');
  }

  const { Absurd } = await import('absurd-sdk');
  const app = new Absurd({
    db,
    queueName: options.queueName || process.env.GRINIONS_QUEUE || 'grinions',
  });
  const services = options.services || createShellServices({
    repoRoot: options.repoRoot || DEFAULT_REPO_ROOT,
  });

  app.registerTask(
    { name: 'grinions-phase', defaultMaxAttempts: 5 },
    async (params, ctx) => runPhase(ctx, params, services),
  );

  return app;
}
