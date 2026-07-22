import { createGrinionsRuntime } from './absurd-runtime.mjs';

const app = await createGrinionsRuntime();
const parsedConcurrency = Number.parseInt(process.env.GRINIONS_CONCURRENCY ?? '1', 10);
const concurrency = Number.isInteger(parsedConcurrency) && parsedConcurrency > 0 ? parsedConcurrency : 1;
let worker = null;
let shuttingDown = false;

async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`GRINIONS worker shutting down on ${signal}`);
  try {
    if (worker) await worker.close();
  } finally {
    await app.close();
  }
}

for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, () => {
    shutdown(signal)
      .then(() => process.exit(0))
      .catch((error) => {
        console.error(error);
        process.exit(1);
      });
  });
}

console.log(`GRINIONS worker listening on ${process.env.GRINIONS_QUEUE || 'grinions'} (concurrency=${concurrency})`);
worker = await app.startWorker({ concurrency });
