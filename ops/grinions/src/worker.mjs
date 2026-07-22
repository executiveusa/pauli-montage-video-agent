import { createGrinionsRuntime } from './absurd-runtime.mjs';

const app = await createGrinionsRuntime();
const parsedConcurrency = Number.parseInt(process.env.GRINIONS_CONCURRENCY ?? '1', 10);
const concurrency = Number.isInteger(parsedConcurrency) && parsedConcurrency > 0 ? parsedConcurrency : 1;
console.log(`GRINIONS worker listening on ${process.env.GRINIONS_QUEUE || 'grinions'} (concurrency=${concurrency})`);
await app.startWorker({ concurrency });
