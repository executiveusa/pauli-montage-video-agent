import { runPhase } from './phase-workflow.mjs';
import { createShellServices } from './services.mjs';

export async function createGrinionsRuntime(options = {}) {
  const { Absurd } = await import('absurd-sdk');
  const app = new Absurd({
    db: options.db || process.env.ABSURD_DATABASE_URL,
    queueName: options.queueName || process.env.GRINIONS_QUEUE || 'grinions',
  });
  const services = options.services || createShellServices({ repoRoot: options.repoRoot });

  app.registerTask(
    { name: 'grinions-phase', defaultMaxAttempts: 5 },
    async (params, ctx) => runPhase(ctx, params, services),
  );

  return app;
}
