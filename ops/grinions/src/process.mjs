import { spawn } from 'node:child_process';

const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const DEFAULT_MAX_OUTPUT_BYTES = 10 * 1024 * 1024;

export function run(command, args = [], options = {}) {
  const timeoutMs = options.timeoutMs === undefined ? DEFAULT_TIMEOUT_MS : Number(options.timeoutMs);
  const maxOutputBytes = options.maxOutputBytes === undefined
    ? DEFAULT_MAX_OUTPUT_BYTES
    : Number(options.maxOutputBytes);

  if (!Number.isFinite(timeoutMs) || timeoutMs < 0) throw new TypeError('timeoutMs must be a non-negative finite number');
  if (!Number.isFinite(maxOutputBytes) || maxOutputBytes <= 0) throw new TypeError('maxOutputBytes must be a positive finite number');

  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: { ...process.env, ...options.env },
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let outputBytes = 0;
    let settled = false;
    let forceKillTimer = null;

    const terminate = () => {
      if (child.exitCode !== null || child.killed) return;
      child.kill('SIGTERM');
      forceKillTimer = setTimeout(() => {
        if (child.exitCode === null) child.kill('SIGKILL');
      }, 2000);
      forceKillTimer.unref?.();
    };

    const fail = (error) => {
      if (settled) return;
      settled = true;
      terminate();
      error.stdout = stdout;
      error.stderr = stderr;
      reject(error);
    };

    const append = (stream, chunk) => {
      if (settled) return;
      outputBytes += Buffer.byteLength(chunk);
      if (outputBytes > maxOutputBytes) {
        const error = new Error(`${command} exceeded output limit of ${maxOutputBytes} bytes`);
        error.code = 'OUTPUT_LIMIT';
        fail(error);
        return;
      }
      if (stream === 'stdout') stdout += chunk;
      else stderr += chunk;
    };

    child.stdout.on('data', (chunk) => append('stdout', chunk));
    child.stderr.on('data', (chunk) => append('stderr', chunk));

    const timeout = timeoutMs === 0 ? null : setTimeout(() => {
      const error = new Error(`${command} timed out after ${timeoutMs}ms`);
      error.code = 'TIMEOUT';
      fail(error);
    }, timeoutMs);
    timeout?.unref?.();

    child.on('error', (error) => fail(error));
    child.on('close', (code, signal) => {
      if (timeout) clearTimeout(timeout);
      if (forceKillTimer) clearTimeout(forceKillTimer);
      if (settled) return;
      settled = true;
      if (code === 0) return resolve({ code, signal, stdout, stderr });
      const error = new Error(`${command} exited ${code ?? signal}: ${stderr || stdout}`.trim());
      error.code = code ?? signal;
      error.stdout = stdout;
      error.stderr = stderr;
      reject(error);
    });
  });
}
