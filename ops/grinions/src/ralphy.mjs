import { run } from './process.mjs';

export function buildRalphyArgs({ taskFile, baseBranch, maxRetries = 3, browser = false }) {
  if (!taskFile || !baseBranch) throw new TypeError('taskFile and baseBranch are required');
  return [
    '--codex',
    '--prd', taskFile,
    '--branch-per-task',
    '--no-merge',
    '--base-branch', baseBranch,
    '--max-iterations', '1',
    '--max-retries', String(maxRetries),
    browser ? '--browser' : '--no-browser',
  ];
}

export async function runRalphy(options) {
  const bin = process.env.RALPHY_BIN || 'ralphy';
  const [{ stdout: status }, { stdout: branch }, { stdout: head }, { stdout: stashes }] = await Promise.all([
    run('git', ['status', '--porcelain'], { cwd: options.cwd }),
    run('git', ['branch', '--show-current'], { cwd: options.cwd }),
    run('git', ['rev-parse', 'HEAD'], { cwd: options.cwd }),
    run('git', ['stash', 'list', '--format=%H'], { cwd: options.cwd }),
  ]);
  if (status.trim()) throw new Error('RALPHY_DIRTY_WORKTREE');
  let result;
  let executionError;
  try {
    result = await run(bin, buildRalphyArgs(options), {
      cwd: options.cwd,
      timeoutMs: options.timeoutMs ?? 60 * 60 * 1000,
      maxOutputBytes: options.maxOutputBytes ?? 25 * 1024 * 1024,
    });
  } catch (error) {
    executionError = error;
  }

  const [{ stdout: afterStatus }, { stdout: afterBranch }, { stdout: afterHead }, { stdout: afterStashes }] = await Promise.all([
    run('git', ['status', '--porcelain'], { cwd: options.cwd }),
    run('git', ['branch', '--show-current'], { cwd: options.cwd }),
    run('git', ['rev-parse', 'HEAD'], { cwd: options.cwd }),
    run('git', ['stash', 'list', '--format=%H'], { cwd: options.cwd }),
  ]);
  if (
    afterStatus.trim()
    || afterBranch.trim() !== branch.trim()
    || afterHead.trim() !== head.trim()
    || afterStashes.trim() !== stashes.trim()
  ) {
    throw new Error('RALPHY_WORKTREE_NOT_RESTORED');
  }
  if (executionError) throw executionError;
  return result;
}
