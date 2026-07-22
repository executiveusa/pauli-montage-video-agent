import { run } from './process.mjs';

export function buildRalphyArgs({ taskFile, baseBranch, maxRetries = 3, browser = false }) {
  if (!taskFile || !baseBranch) throw new TypeError('taskFile and baseBranch are required');
  return [
    '--prd', taskFile,
    '--branch-per-task',
    '--no-merge',
    '--base-branch', baseBranch,
    '--max-retries', String(maxRetries),
    browser ? '--browser' : '--no-browser',
  ];
}

export async function runRalphy(options) {
  const bin = process.env.RALPHY_BIN || 'ralphy';
  return run(bin, buildRalphyArgs(options), {
    cwd: options.cwd,
    timeoutMs: options.timeoutMs ?? 60 * 60 * 1000,
    maxOutputBytes: options.maxOutputBytes ?? 25 * 1024 * 1024,
  });
}
