import assert from 'node:assert/strict';
import { chmod, mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { compileBeadTaskPacket } from '../src/beads.mjs';
import { workIdentityMarker } from '../src/completion.mjs';
import { run } from '../src/process.mjs';
import { canonicalPrBranch, createShellServices, selectRalphyTaskBranch } from '../src/services.mjs';

const phase = {
  initiativeId: 'yappy-upgrade',
  phaseId: 'upgrade-00',
  openspecId: 'upgrade-00-grinions-replay-guard',
  branch: 'agent/grinions-completed-phase-guard',
  risk: 'medium',
};

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), 'grinions-completion-'));
  const remote = join(root, 'remote.git');
  const repo = join(root, 'repo');
  const bin = join(root, 'bin');
  const prs = join(root, 'prs.json');
  await mkdir(bin);
  await run('git', ['init', '--bare', '--initial-branch=main', remote], { cwd: root });
  await run('git', ['clone', remote, repo], { cwd: root });
  await run('git', ['config', 'user.email', 'grinions@example.test'], { cwd: repo });
  await run('git', ['config', 'user.name', 'GRINIONS Test'], { cwd: repo });
  await writeFile(join(repo, 'README.md'), 'baseline\n');
  await run('git', ['add', 'README.md'], { cwd: repo });
  await run('git', ['commit', '-m', 'baseline'], { cwd: repo });
  await run('git', ['push', '-u', 'origin', 'main'], { cwd: repo });
  await run('git', ['switch', '-c', phase.branch], { cwd: repo });
  await mkdir(join(repo, 'ops', 'reports'), { recursive: true });
  await writeFile(join(repo, 'ops', 'reports', `phase-${phase.phaseId}.md`), '# Test report\n');
  await writeFile(prs, '[]');

  const gh = join(bin, 'gh');
  await writeFile(gh, `#!/usr/bin/env node
const args = process.argv.slice(2);
if (args[0] === 'repo' && args[1] === 'view') process.stdout.write('executiveusa/pauli-montage-video-agent\\n');
else if (args[0] === 'pr' && args[1] === 'list') {
  const all = JSON.parse(require('node:fs').readFileSync(process.env.GRINIONS_TEST_PRS_FILE, 'utf8'));
  const headIndex = args.indexOf('--head');
  process.stdout.write(JSON.stringify(headIndex === -1 ? all : all.filter((pr) => pr.headRefName === args[headIndex + 1])));
}

else if (args[0] === 'pr' && args[1] === 'create') {
  const fs = require('node:fs');
  const cp = require('node:child_process');
  const bodyPath = args[args.indexOf('--body-file') + 1];
  const branch = args[args.indexOf('--head') + 1];
  const base = args[args.indexOf('--base') + 1];
  const head = cp.execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const created = [{ number: 77, url: 'https://github.test/pull/77', state: 'OPEN', mergedAt: null, mergeCommit: null, headRefName: branch, headRefOid: head, baseRefName: base, body: fs.readFileSync(bodyPath, 'utf8') }];
  fs.writeFileSync(process.env.GRINIONS_TEST_PRS_FILE, JSON.stringify(created));
  process.stdout.write('https://github.test/pull/77\\n');
  if (process.env.GRINIONS_TEST_CREATE_FAIL_AFTER_WRITE === '1') process.exit(1);
}
else if (args[0] === 'pr' && args[1] === 'view') {
  const all = JSON.parse(require('node:fs').readFileSync(process.env.GRINIONS_TEST_PRS_FILE, 'utf8'));
  const viewed = { ...all.find((pr) => String(pr.number) === String(args[2])) };
  if (process.env.GRINIONS_TEST_MUTATE_VIEW_IDENTITY === '1') viewed.body = '';
  process.stdout.write(JSON.stringify(viewed));
}
else { process.stderr.write('unexpected gh call: ' + args.join(' ')); process.exit(2); }
`);
  await chmod(gh, 0o755);
  return { root, repo, bin, prs };
}

test('Ralphy selection accepts exactly one newly created identity-bound branch', () => {
  const before = new Set(['main', 'ralphy/bead-bd-a1b2-stale']);
  const packet = compileBeadTaskPacket({
    id: 'bd-a1b2',
    title: 'Fresh task',
    description: 'Bounded work',
    design: 'One change',
    acceptance: 'Verified',
    scope: ['one file'],
    dependencies: [],
    verification: 'tests pass',
    verificationCommands: [{ command: 'node', args: ['--test'] }],
    evidence: ['test output'],
    prohibitedChanges: ['scope expansion'],
    rollback: 'revert',
    notes: '',
  }, phase);
  const ralphyTitle = packet.match(/^- \[ \] (.+)$/m)[1];
  const ralphySlug = ralphyTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const generatedBranch = `ralphy/${ralphySlug}`;
  assert.equal(
    selectRalphyTaskBranch(before, new Set([...before, generatedBranch]), 'bd-a1b2'),
    generatedBranch,
  );
  assert.throws(
    () => selectRalphyTaskBranch(before, new Set(before), 'bd-a1b2'),
    /RALPHY_TASK_BRANCH_AMBIGUOUS/,
  );
  assert.throws(
    () => selectRalphyTaskBranch(before, new Set([...before, 'ralphy/other-task']), 'bd-a1b2'),
    /RALPHY_TASK_BRANCH_IDENTITY_MISMATCH/,
  );
  assert.throws(
    () => selectRalphyTaskBranch(before, new Set([...before, 'ralphy/bead-bd-a1b2c-unrelated']), 'bd-a1b2'),
    /RALPHY_TASK_BRANCH_IDENTITY_MISMATCH/,
  );
  assert.throws(
    () => selectRalphyTaskBranch(before, new Set([...before, 'ralphy/bead-not-bd-a1b2-unrelated']), 'bd-a1b2'),
    /RALPHY_TASK_BRANCH_IDENTITY_MISMATCH/,
  );
  assert.throws(
    () => selectRalphyTaskBranch(before, new Set([...before, 'ralphy/bead-bd-a1b2-one', 'ralphy/bead-bd-a1b2-two']), 'bd-a1b2'),
    /RALPHY_TASK_BRANCH_AMBIGUOUS/,
  );
});

test('shell completion detection works from canonical evidence in a clean checkout', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  const oldPrsFile = process.env.GRINIONS_TEST_PRS_FILE;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    const { stdout } = await run('git', ['rev-parse', 'HEAD'], { cwd: repo });
    const identity = {
      repository: 'executiveusa/pauli-montage-video-agent',
      initiativeId: phase.initiativeId,
      openspecId: phase.openspecId,
    };
    await writeFile(prs, JSON.stringify([{
      number: 40,
      state: 'MERGED',
      mergedAt: '2026-08-09T12:00:00Z',
      mergeCommit: { oid: stdout.trim() },
      headRefName: canonicalPrBranch(identity),
      body: workIdentityMarker(identity),
    }]));
    const result = await createShellServices({ repoRoot: repo }).classifyPhaseCompletion(phase);
    assert.equal(result.status, 'already_completed');
    assert.equal(result.mergeSha, stdout.trim());
    const replay = await createShellServices({ repoRoot: repo }).createOrUpdatePr(phase, { workspace: { path: repo } });
    assert.equal(replay.alreadyCompleted, true);
    assert.equal(replay.completion.mergeSha, stdout.trim());
  } finally {
    process.env.PATH = oldPath;
    if (oldPrsFile === undefined) delete process.env.GRINIONS_TEST_PRS_FILE;
    else process.env.GRINIONS_TEST_PRS_FILE = oldPrsFile;
    await rm(root, { recursive: true, force: true });
  }
});

test('shell completion rejects a receipt whose post-merge SHA does not exist', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  const oldPrsFile = process.env.GRINIONS_TEST_PRS_FILE;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    const { stdout } = await run('git', ['rev-parse', 'HEAD'], { cwd: repo });
    const mergeSha = stdout.trim();
    const identity = {
      repository: 'executiveusa/pauli-montage-video-agent',
      initiativeId: phase.initiativeId,
      openspecId: phase.openspecId,
    };
    await writeFile(prs, JSON.stringify([{
      number: 40,
      state: 'MERGED',
      mergedAt: '2026-08-09T12:00:00Z',
      mergeCommit: { oid: mergeSha },
      headRefName: canonicalPrBranch(identity),
      headRefOid: mergeSha,
      body: workIdentityMarker(identity),
    }]));
    await mkdir(join(repo, 'ops', 'receipts'), { recursive: true });
    await writeFile(join(repo, 'ops', 'receipts', `phase-${phase.phaseId}.json`), JSON.stringify({
      schemaVersion: 1,
      phaseId: phase.phaseId,
      openspecId: phase.openspecId,
      risk: phase.risk,
      completedAt: '2026-08-09T12:00:00Z',
      baselineMainSha: mergeSha,
      beads: [{ id: 'bead-1', headSha: mergeSha, verified: true, closedStatus: 'closed' }],
      pullRequest: { number: 40, url: null, headSha: mergeSha },
      judgment: { passed: true, unresolvedReviewThreads: 0 },
      merge: { sha: mergeSha, mergedAt: '2026-08-09T12:00:00Z' },
      postMerge: { passed: true, mainSha: 'definitely-not-a-git-sha' },
      rollback: { baselineCaptured: true, receiptPath: `ops/rollback/phase-${phase.phaseId}.json` },
    }));
    const result = await createShellServices({ repoRoot: repo }).classifyPhaseCompletion(phase);
    assert.equal(result.status, 'inconsistent');
    assert.equal(result.reason, 'receipt_post_merge_sha_invalid');
  } finally {
    process.env.PATH = oldPath;
    if (oldPrsFile === undefined) delete process.env.GRINIONS_TEST_PRS_FILE;
    else process.env.GRINIONS_TEST_PRS_FILE = oldPrsFile;
    await rm(root, { recursive: true, force: true });
  }
});

test('canonical origin/main receipt is visible from a stale worker branch', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  const oldPrsFile = process.env.GRINIONS_TEST_PRS_FILE;
  const updater = join(root, 'receipt-updater');
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    const { stdout } = await run('git', ['rev-parse', 'HEAD'], { cwd: repo });
    const phaseHead = stdout.trim();
    const identity = {
      repository: 'executiveusa/pauli-montage-video-agent',
      initiativeId: phase.initiativeId,
      openspecId: phase.openspecId,
    };
    await writeFile(prs, JSON.stringify([{
      number: 40,
      state: 'OPEN',
      mergedAt: null,
      mergeCommit: null,
      headRefName: canonicalPrBranch(identity),
      headRefOid: phaseHead,
      baseRefName: 'main',
      body: workIdentityMarker(identity),
    }]));

    await run('git', ['clone', join(root, 'remote.git'), updater], { cwd: root });
    await run('git', ['config', 'user.email', 'receipt@example.test'], { cwd: updater });
    await run('git', ['config', 'user.name', 'Receipt Updater'], { cwd: updater });
    await mkdir(join(updater, 'ops', 'receipts'), { recursive: true });
    await writeFile(join(updater, 'ops', 'receipts', `phase-${phase.phaseId}.json`), JSON.stringify({
      schemaVersion: 1,
      phaseId: phase.phaseId,
      openspecId: phase.openspecId,
      risk: phase.risk,
      completedAt: '2026-08-09T12:00:00Z',
      baselineMainSha: phaseHead,
      beads: [{ id: 'bead-1', headSha: phaseHead, verified: true, closedStatus: 'closed' }],
      pullRequest: { number: 40, url: null, headSha: phaseHead },
      judgment: { passed: true, unresolvedReviewThreads: 0 },
      merge: { sha: phaseHead, mergedAt: '2026-08-09T12:00:00Z' },
      postMerge: { passed: true, mainSha: phaseHead },
      rollback: { baselineCaptured: true, receiptPath: `ops/rollback/phase-${phase.phaseId}.json` },
    }));
    await run('git', ['add', '.'], { cwd: updater });
    await run('git', ['commit', '-m', 'canonical completion receipt'], { cwd: updater });
    await run('git', ['push', 'origin', 'main'], { cwd: updater });

    await assert.rejects(
      () => createShellServices({ repoRoot: repo }).createOrUpdatePr(phase, { workspace: { path: repo } }),
      /PHASE_COMPLETION_INCONSISTENT:upgrade-00:receipt_with_unmerged_pull_request/,
    );
  } finally {
    process.env.PATH = oldPath;
    if (oldPrsFile === undefined) delete process.env.GRINIONS_TEST_PRS_FILE;
    else process.env.GRINIONS_TEST_PRS_FILE = oldPrsFile;
    await rm(root, { recursive: true, force: true });
  }
});

test('squash merge cannot be redirected away from the canonical PR', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  const oldPrsFile = process.env.GRINIONS_TEST_PRS_FILE;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    const { stdout } = await run('git', ['rev-parse', 'HEAD'], { cwd: repo });
    const headSha = stdout.trim();
    const identity = {
      repository: 'executiveusa/pauli-montage-video-agent',
      initiativeId: phase.initiativeId,
      openspecId: phase.openspecId,
    };
    await writeFile(prs, JSON.stringify([{
      number: 40,
      state: 'OPEN',
      mergedAt: null,
      mergeCommit: null,
      headRefName: canonicalPrBranch(identity),
      headRefOid: headSha,
      baseRefName: 'main',
      body: workIdentityMarker(identity),
    }]));
    await assert.rejects(
      () => createShellServices({ repoRoot: repo }).squashMerge(
        phase,
        { number: 999 },
        { judgment: { headRefOid: headSha } },
      ),
      /PHASE_MERGE_TARGET_MISMATCH/,
    );
    const canonicalCaller = {
      number: 40,
      headSha,
      headRefName: canonicalPrBranch(identity),
      baseRefName: 'main',
      identity,
    };
    await assert.rejects(
      () => createShellServices({ repoRoot: repo }).squashMerge(
        phase,
        { ...canonicalCaller, headSha: 'wrong-head' },
        { judgment: { headRefOid: headSha } },
      ),
      /PHASE_MERGE_TARGET_MISMATCH/,
    );
    process.env.GRINIONS_TEST_MUTATE_VIEW_IDENTITY = '1';
    await assert.rejects(
      () => createShellServices({ repoRoot: repo }).squashMerge(
        phase,
        canonicalCaller,
        { judgment: { headRefOid: headSha } },
      ),
      /PHASE_MERGE_TARGET_MOVED/,
    );
  } finally {
    process.env.PATH = oldPath;
    if (oldPrsFile === undefined) delete process.env.GRINIONS_TEST_PRS_FILE;
    else process.env.GRINIONS_TEST_PRS_FILE = oldPrsFile;
    delete process.env.GRINIONS_TEST_MUTATE_VIEW_IDENTITY;
    await rm(root, { recursive: true, force: true });
  }
});

test('fatal git ancestry inspection is evidence-unavailable, not ordinary non-ancestry', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    await writeFile(prs, JSON.stringify([{
      number: 40,
      state: 'MERGED',
      mergedAt: '2026-08-09T12:00:00Z',
      mergeCommit: { oid: 'not-a-git-object' },
      headRefName: canonicalPrBranch({
        repository: 'executiveusa/pauli-montage-video-agent',
        initiativeId: phase.initiativeId,
        openspecId: phase.openspecId,
      }),
      body: workIdentityMarker({
        repository: 'executiveusa/pauli-montage-video-agent',
        initiativeId: phase.initiativeId,
        openspecId: phase.openspecId,
      }),
    }]));
    await assert.rejects(
      () => createShellServices({ repoRoot: repo }).classifyPhaseCompletion(phase),
      /PHASE_COMPLETION_EVIDENCE_UNAVAILABLE/,
    );
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    await rm(root, { recursive: true, force: true });
  }
});

test('missing merge objects on noncanonical identity branches are ignored', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    await writeFile(prs, JSON.stringify([{
      number: 41,
      state: 'MERGED',
      mergedAt: '2026-08-09T12:00:00Z',
      mergeCommit: { oid: 'missing-noncanonical-object' },
      headRefName: 'unrelated/copied-marker',
      body: workIdentityMarker({
        repository: 'executiveusa/pauli-montage-video-agent',
        initiativeId: phase.initiativeId,
        openspecId: phase.openspecId,
      }),
    }]));
    const result = await createShellServices({ repoRoot: repo }).classifyPhaseCompletion(phase);
    assert.equal(result.status, 'not_completed');
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    await rm(root, { recursive: true, force: true });
  }
});

test('shell pre-PR guard rejects identical tree and accepts a fresh delta', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    const services = createShellServices({ repoRoot: repo });
    await assert.rejects(
      () => services.preparePullRequest(phase, { path: repo }),
      /PHASE_NO_TREE_DELTA/,
    );

    await writeFile(join(repo, 'change.txt'), 'real delta\n');
    await run('git', ['add', 'change.txt'], { cwd: repo });
    await run('git', ['commit', '-m', 'real delta'], { cwd: repo });
    const result = await services.preparePullRequest(phase, { path: repo });
    assert.equal(result.passed, true);
    assert.notEqual(result.headTree, result.mainTree);
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    await rm(root, { recursive: true, force: true });
  }
});

test('definite local PR input failure leaves no identity reservation', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    await rm(join(repo, 'ops', 'reports', `phase-${phase.phaseId}.md`));
    await writeFile(join(repo, 'change.txt'), 'real delta\n');
    await run('git', ['add', '.'], { cwd: repo });
    await run('git', ['commit', '-m', 'real delta'], { cwd: repo });
    await assert.rejects(
      () => createShellServices({ repoRoot: repo }).createOrUpdatePr(phase, { workspace: { path: repo } }),
      /ENOENT/,
    );
    const { stdout } = await run('git', ['ls-remote', '--heads', join(root, 'remote.git'), 'refs/heads/grinions/*'], { cwd: root });
    assert.equal(stdout.trim(), '');
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    await rm(root, { recursive: true, force: true });
  }
});

test('uncertain PR creation adopts the exact open identity on retry', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    await writeFile(join(repo, 'change.txt'), 'real delta\n');
    await run('git', ['add', '.'], { cwd: repo });
    await run('git', ['commit', '-m', 'real delta'], { cwd: repo });
    const services = createShellServices({ repoRoot: repo });

    process.env.GRINIONS_TEST_CREATE_FAIL_AFTER_WRITE = '1';
    await assert.rejects(
      () => services.createOrUpdatePr(phase, { workspace: { path: repo } }),
      /gh exited 1/,
    );
    delete process.env.GRINIONS_TEST_CREATE_FAIL_AFTER_WRITE;

    const recovered = await services.createOrUpdatePr(phase, { workspace: { path: repo } });
    assert.equal(recovered.reused, true);
    assert.equal(recovered.number, 77);
    const [stored] = JSON.parse(await readFile(prs, 'utf8'));
    assert.match(stored.body, /grinions-work-identity/);
    assert.equal(stored.headRefOid, recovered.headSha);
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    delete process.env.GRINIONS_TEST_CREATE_FAIL_AFTER_WRITE;
    await rm(root, { recursive: true, force: true });
  }
});

test('main advancing after the checkpoint makes PR creation fail stale', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  const updater = join(root, 'updater');
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    await writeFile(join(repo, 'change.txt'), 'phase delta\n');
    await run('git', ['add', 'change.txt'], { cwd: repo });
    await run('git', ['commit', '-m', 'phase delta'], { cwd: repo });
    const services = createShellServices({ repoRoot: repo });
    await services.preparePullRequest(phase, { path: repo });

    await run('git', ['clone', join(root, 'remote.git'), updater], { cwd: root });
    await run('git', ['config', 'user.email', 'updater@example.test'], { cwd: updater });
    await run('git', ['config', 'user.name', 'Updater'], { cwd: updater });
    await writeFile(join(updater, 'advance.txt'), 'main advanced\n');
    await run('git', ['add', 'advance.txt'], { cwd: updater });
    await run('git', ['commit', '-m', 'advance main'], { cwd: updater });
    await run('git', ['push', 'origin', 'main'], { cwd: updater });

    await assert.rejects(
      () => services.createOrUpdatePr(phase, { workspace: { path: repo } }),
      /PHASE_BRANCH_BEHIND_MAIN/,
    );
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    await rm(root, { recursive: true, force: true });
  }
});

test('saturated all-state branch history fails closed', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    await writeFile(join(repo, 'change.txt'), 'real delta\n');
    await run('git', ['add', '.'], { cwd: repo });
    await run('git', ['commit', '-m', 'real delta'], { cwd: repo });
    await writeFile(prs, JSON.stringify(Array.from({ length: 100 }, (_, index) => ({
      number: index + 1,
      state: 'CLOSED',
      headRefName: phase.branch,
      baseRefName: 'main',
      body: '',
    }))));
    await assert.rejects(
      () => createShellServices({ repoRoot: repo }).preparePullRequest(phase, { path: repo }),
      /PHASE_PR_HISTORY_LIMIT_EXCEEDED/,
    );
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    await rm(root, { recursive: true, force: true });
  }
});

test('identity reservation blocks concurrent tasks on different branches', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  const competitor = join(root, 'competitor');
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    await writeFile(join(repo, 'change.txt'), 'first task\n');
    await run('git', ['add', '.'], { cwd: repo });
    await run('git', ['commit', '-m', 'first task'], { cwd: repo });
    const first = await createShellServices({ repoRoot: repo }).createOrUpdatePr(phase, { workspace: { path: repo } });
    assert.equal(first.reused, false);

    await run('git', ['clone', join(root, 'remote.git'), competitor], { cwd: root });
    await run('git', ['config', 'user.email', 'competitor@example.test'], { cwd: competitor });
    await run('git', ['config', 'user.name', 'Competitor'], { cwd: competitor });
    const competingPhase = { ...phase, branch: 'agent/competing-identity-task' };
    await run('git', ['switch', '-c', competingPhase.branch], { cwd: competitor });
    await writeFile(join(competitor, 'other.txt'), 'second task\n');
    await run('git', ['add', 'other.txt'], { cwd: competitor });
    await run('git', ['commit', '-m', 'second task'], { cwd: competitor });

    await assert.rejects(
      () => createShellServices({ repoRoot: competitor }).createOrUpdatePr(competingPhase, { workspace: { path: competitor } }),
      /PHASE_IDENTITY_RESERVATION_CONFLICT/,
    );
    assert.equal(JSON.parse(await readFile(prs, 'utf8')).length, 1);
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    await rm(root, { recursive: true, force: true });
  }
});

test('identity reservation cannot be stolen by a fast-forward descendant', async () => {
  const { root, repo, bin, prs } = await fixture();
  const oldPath = process.env.PATH;
  const competitor = join(root, 'descendant-competitor');
  try {
    process.env.PATH = `${bin}:${oldPath}`;
    process.env.GRINIONS_TEST_PRS_FILE = prs;
    await writeFile(join(repo, 'change.txt'), 'first task\n');
    await run('git', ['add', '.'], { cwd: repo });
    await run('git', ['commit', '-m', 'first task'], { cwd: repo });
    const first = await createShellServices({ repoRoot: repo }).createOrUpdatePr(phase, { workspace: { path: repo } });

    const { stdout: reservationOut } = await run('git', ['ls-remote', '--heads', join(root, 'remote.git'), 'refs/heads/grinions/*'], { cwd: root });
    const [reservedSha, reservedRef] = reservationOut.trim().split(/\s+/);
    assert.equal(reservedSha, first.headSha);
    const reservedBranch = reservedRef.replace('refs/heads/', '');

    await run('git', ['clone', join(root, 'remote.git'), competitor], { cwd: root });
    await run('git', ['config', 'user.email', 'descendant@example.test'], { cwd: competitor });
    await run('git', ['config', 'user.name', 'Descendant'], { cwd: competitor });
    const competingPhase = { ...phase, branch: 'agent/descendant-identity-task' };
    await run('git', ['switch', '-c', competingPhase.branch, `origin/${reservedBranch}`], { cwd: competitor });
    await writeFile(join(competitor, 'descendant.txt'), 'fast-forward takeover\n');
    await run('git', ['add', 'descendant.txt'], { cwd: competitor });
    await run('git', ['commit', '-m', 'descendant takeover'], { cwd: competitor });

    await assert.rejects(
      () => createShellServices({ repoRoot: competitor }).createOrUpdatePr(competingPhase, { workspace: { path: competitor } }),
      /PHASE_IDENTITY_RESERVATION_CONFLICT/,
    );
    const { stdout: afterOut } = await run('git', ['ls-remote', '--heads', join(root, 'remote.git'), reservedRef], { cwd: root });
    assert.equal(afterOut.trim().split(/\s+/)[0], reservedSha);
  } finally {
    process.env.PATH = oldPath;
    delete process.env.GRINIONS_TEST_PRS_FILE;
    await rm(root, { recursive: true, force: true });
  }
});
