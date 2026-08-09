import assert from 'node:assert/strict';
import { chmod, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { run } from '../src/process.mjs';
import { buildRalphyArgs, runRalphy } from '../src/ralphy.mjs';

test('Ralphy is always isolated from merge authority', () => {
  const args = buildRalphyArgs({ taskFile: 'tasks.md', baseBranch: 'phase/00', maxRetries: 3 });
  assert.equal(args.includes('--codex'), true);
  assert.equal(args.includes('--branch-per-task'), true);
  assert.equal(args.includes('--no-merge'), true);
  assert.deepEqual(args.slice(args.indexOf('--max-iterations'), args.indexOf('--max-iterations') + 2), ['--max-iterations', '1']);
  assert.equal(args.includes('--create-pr'), false);
  assert.equal(args.includes('--fast'), false);
  assert.equal(args.includes('--no-tests'), false);
  assert.equal(args.includes('--no-lint'), false);
});

async function gitFixture() {
  const root = await mkdtemp(join(tmpdir(), 'ralphy-guard-'));
  await run('git', ['init', '--initial-branch=main'], { cwd: root });
  await run('git', ['config', 'user.email', 'ralphy@example.test'], { cwd: root });
  await run('git', ['config', 'user.name', 'Ralphy Test'], { cwd: root });
  await writeFile(join(root, 'tracked.txt'), 'baseline\n');
  await run('git', ['add', 'tracked.txt'], { cwd: root });
  await run('git', ['commit', '-m', 'baseline'], { cwd: root });
  return root;
}

test('Ralphy refuses a dirty caller worktree before launching', async () => {
  const root = await gitFixture();
  try {
    await writeFile(join(root, 'tracked.txt'), 'dirty\n');
    await assert.rejects(
      () => runRalphy({ cwd: root, taskFile: 'task.md', baseBranch: 'main' }),
      /RALPHY_DIRTY_WORKTREE/,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('Ralphy detects untracked files even when git config hides them', async () => {
  const root = await gitFixture();
  try {
    await run('git', ['config', 'status.showUntrackedFiles', 'no'], { cwd: root });
    await writeFile(join(root, 'untracked.txt'), 'must be detected\n');
    await assert.rejects(
      () => runRalphy({ cwd: root, taskFile: 'task.md', baseBranch: 'main' }),
      /RALPHY_DIRTY_WORKTREE/,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('Ralphy fails when the engine leaks an autostash or changes caller state', async () => {
  const root = await gitFixture();
  const fakeRoot = await mkdtemp(join(tmpdir(), 'fake-ralphy-'));
  const fake = join(fakeRoot, 'ralphy');
  const oldBin = process.env.RALPHY_BIN;
  try {
    await writeFile(fake, '#!/bin/sh\nprintf "changed\\n" > tracked.txt\ngit stash push -m leaked >/dev/null\n');
    await chmod(fake, 0o755);
    process.env.RALPHY_BIN = fake;
    await assert.rejects(
      () => runRalphy({ cwd: root, taskFile: 'task.md', baseBranch: 'main' }),
      /RALPHY_WORKTREE_NOT_RESTORED/,
    );
  } finally {
    if (oldBin === undefined) delete process.env.RALPHY_BIN;
    else process.env.RALPHY_BIN = oldBin;
    await rm(root, { recursive: true, force: true });
    await rm(fakeRoot, { recursive: true, force: true });
  }
});
