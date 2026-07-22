import { createGrinionsRuntime } from './absurd-runtime.mjs';

const app = await createGrinionsRuntime();
const concurrency = Number(process.env.GRINIONS_CONCURRENCY || 1);
console.log(`GRINIONS worker listening on ${process.env.GRINIONS_QUEUE || 'grinions'} (concurrency=${concurrency})`);
await app.startWorker({ concurrency });
