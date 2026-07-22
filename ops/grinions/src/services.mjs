import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { run } from './process.mjs';
import { runRalphy } from './ralphy.mjs';

const sleep = (ms) => new Promise((resolveSleep) => setTimeout(resolveSleep, ms));

async function runResult(command, args = [], options = {}) {
  try {
    return await run(command, args, options);
  } catch (error) {
    return {
      code: Number.isInteger(error.code) ? error.code : 1,
      stdout: error.stdout || '',
      stderr: error.stderr || error.message || '',
    };
  }
}

async function readJsonIfExists(path, fallback = {}) {
  try {
    return JSON.parse(await readFile(path, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return fallback;
    throw error;
  }
}

async function writeJson(path, value) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  return value;
}

function parseJson(text, label) {
  try {
    return JSON.parse(text || 'null');
  } catch (error) {
    throw new Error(`${label} returned invalid JSON: ${error.message}`);
  }
}

function safeSegment(value) {
  return String(value).replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'phase';
}

function prTarget(pr) {
  if (pr?.number) return String(pr.number);
  if (pr?.url) return pr.url;
  throw new TypeError('pull request number or URL is required');
}

async function listBranches(cwd) {
  const { stdout } = await run('git', ['for-each-ref', '--format=%(refname:short)', 'refs/heads'], { cwd });
  return new Set(stdout.split('\n').map((item) => item.trim()).filter(Boolean));
}

async function existingWorktreeForBranch(repoRoot, branch) {
  const { stdout } = await run('git', ['worktree', 'list', '--porcelain'], { cwd: repoRoot });
  let path = null;
  for (const line of stdout.split('\n')) {
    if (line.startsWith('worktree ')) path = line.slice('worktree '.length).trim();
    if (line === `branch refs/heads/${branch}`) return path;
    if (!line.trim()) path = null;
  }
  return null;
}

async function refExists(repoRoot, ref) {
  const result = await runResult('git', ['show-ref', '--verify', '--quiet', ref], { cwd: repoRoot });
  return result.code === 0;
}

async function remoteBranchExists(repoRoot, branch) {
  const result = await runResult('git', ['ls-remote', '--exit-code', '--heads', 'origin', branch], { cwd: repoRoot });
  return result.code === 0 && Boolean(result.stdout.trim());
}

async function removeWorktree(repoRoot, path) {
  await runResult('git', ['worktree', 'remove', '--force', path], { cwd: repoRoot });
  await rm(path, { recursive: true, force: true });
}

async function readPrChecks(repoRoot, target, required = false) {
  const args = ['pr', 'checks', target];
  if (required) args.push('--required');
  args.push('--json', 'name,state,bucket,workflow');
  const result = await runResult('gh', args, { cwd: repoRoot });
  if (!result.stdout.trim()) return [];
  const checks = parseJson(result.stdout, 'gh pr checks');
  if (!Array.isArray(checks)) throw new Error('gh pr checks did not return an array');
  return checks;
}

function selectedGateChecks(allChecks, requiredChecks, phase) {
  const requiredWorkflows = new Set(['GRINIONS phase gates', ...(phase.requiredWorkflows || [])]);
  const byKey = new Map();
  for (const check of [...requiredChecks, ...allChecks.filter((item) => requiredWorkflows.has(item.workflow))]) {
    byKey.set(`${check.workflow || ''}:${check.name || ''}`, check);
  }
  return [...byKey.values()];
}

function assertChecksPass(checks) {
  if (!checks.length) return { pending: [], passed: false, missing: true };
  const failed = checks.filter((check) => ['fail', 'cancel'].includes(check.bucket));
  const pending = checks.filter((check) => !['pass', 'skipping'].includes(check.bucket));
  if (failed.length) throw new Error(`GATE_CHECK_FAILED:${failed.map((item) => item.name).join(',')}`);
  return { pending, passed: pending.length === 0, missing: false };
}

async function unresolvedReviewThreads(repoRoot, prNumber) {
  const { stdout: repoName } = await run('gh', ['repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner'], { cwd: repoRoot });
  const [owner, name] = repoName.trim().split('/');
  if (!owner || !name) throw new Error('Could not resolve GitHub repository owner/name');

  const query = `query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100){nodes{isResolved isOutdated} pageInfo{hasNextPage}}}}}`;
  const { stdout } = await run('gh', ['api', 'graphql', '-f', `query=${query}`, '-f', `owner=${owner}`, '-f', `name=${name}`, '-F', `number=${prNumber}`], { cwd: repoRoot });
  const payload = parseJson(stdout, 'GitHub reviewThreads query');
  const connection = payload?.data?.repository?.pullRequest?.reviewThreads;
  if (!connection) throw new Error('GitHub reviewThreads query returned no connection');
  if (connection.pageInfo?.hasNextPage) throw new Error('REVIEW_THREAD_PAGE_LIMIT_EXCEEDED');
  return connection.nodes.filter((thread) => !thread.isResolved);
}

export function createShellServices({ repoRoot = process.cwd() } = {}) {
  return {
    async hydrateContext(phase) {
      await run('bd', ['prime'], { cwd: repoRoot });
      return { phase, hydratedAt: new Date().toISOString(), repoRoot };
    },

    async validateSpec(phase) {
      const existing = await existingWorktreeForBranch(repoRoot, phase.branch);
      if (existing) return run('openspec', ['validate', phase.openspecId, '--no-interactive'], { cwd: existing });

      if (await remoteBranchExists(repoRoot, phase.branch)) {
        await run('git', ['fetch', 'origin', phase.branch], { cwd: repoRoot });
        const validationPath = join(tmpdir(), 'grinions-spec-validation', `${safeSegment(phase.phaseId)}-${safeSegment(phase.branch)}`);
        await mkdir(dirname(validationPath), { recursive: true });
        await removeWorktree(repoRoot, validationPath);
        await run('git', ['worktree', 'add', '--detach', validationPath, `origin/${phase.branch}`], { cwd: repoRoot });
        try {
          return await run('openspec', ['validate', phase.openspecId, '--no-interactive'], { cwd: validationPath });
        } finally {
          await removeWorktree(repoRoot, validationPath);
        }
      }

      return run('openspec', ['validate', phase.openspecId, '--no-interactive'], { cwd: repoRoot });
    },

    async captureBaseline() {
      await run('git', ['fetch', 'origin', 'main'], { cwd: repoRoot });
      const { stdout } = await run('git', ['rev-parse', 'origin/main'], { cwd: repoRoot });
      return { mainSha: stdout.trim(), capturedAt: new Date().toISOString() };
    },

    async writeRollbackReceipt(phase, baseline) {
      const path = resolve(repoRoot, 'ops', 'rollback', `phase-${phase.phaseId}.json`);
      const existing = await readJsonIfExists(path);
      return writeJson(path, {
        ...existing,
        phaseId: phase.phaseId,
        openspecId: existing.openspecId || phase.openspecId,
        baselineMainSha: baseline.mainSha,
        deploymentId: existing.deploymentId ?? null,
        deploymentStateAtBaseline: existing.deploymentStateAtBaseline ?? null,
        migrations: existing.migrations || [],
        backups: existing.backups || [],
        affectedServices: existing.affectedServices || [],
        featureFlags: existing.featureFlags || [],
        rollbackCommands: (existing.rollbackCommands || []).filter((command) => !String(command).includes('<phase-')),
        dataLossRisk: existing.dataLossRisk || 'none-known-at-baseline',
        notes: existing.notes || null,
        capturedAt: baseline.capturedAt,
      });
    },

    async provisionWorkspace(phase) {
      await run('git', ['fetch', 'origin', 'main'], { cwd: repoRoot });
      await runResult('git', ['fetch', 'origin', phase.branch], { cwd: repoRoot });

      const existing = await existingWorktreeForBranch(repoRoot, phase.branch);
      if (existing) return { branch: phase.branch, path: existing, repoRoot, reused: true };

      const workspacePath = join(tmpdir(), 'grinions-worktrees', `${safeSegment(phase.phaseId)}-${safeSegment(phase.branch)}`);
      await mkdir(dirname(workspacePath), { recursive: true });
      await removeWorktree(repoRoot, workspacePath);

      if (await refExists(repoRoot, `refs/heads/${phase.branch}`)) {
        await run('git', ['worktree', 'add', workspacePath, phase.branch], { cwd: repoRoot });
      } else if (await remoteBranchExists(repoRoot, phase.branch)) {
        await run('git', ['worktree', 'add', '-b', phase.branch, workspacePath, `origin/${phase.branch}`], { cwd: repoRoot });
      } else {
        await run('git', ['worktree', 'add', '-b', phase.branch, workspacePath, 'origin/main'], { cwd: repoRoot });
      }

      return { branch: phase.branch, path: workspacePath, repoRoot, reused: false };
    },

    async requireDestructiveApproval(phase, action) {
      const actionId = action?.id || action?.name || String(action);
      throw new Error(`DESTRUCTIVE_ACTION_APPROVAL_REQUIRED:${phase.phaseId}:${actionId}`);
    },

    async executeBeads(phase, workspace) {
      await run('bd', ['ready'], { cwd: workspace.path });
      const before = await listBranches(workspace.path);
      const result = await runRalphy({
        cwd: workspace.path,
        taskFile: `openspec/changes/${phase.openspecId}/tasks.md`,
        baseBranch: phase.branch,
        maxRetries: 3,
      });
      const after = await listBranches(workspace.path);
      const taskBranches = [...after].filter((branch) => !before.has(branch) && branch.startsWith('ralphy/')).sort();
      return { ...result, taskBranches };
    },

    async integrateBeads(phase, workspace, execution) {
      await run('git', ['checkout', phase.branch], { cwd: workspace.path });
      const integratedBranches = [];
      for (const taskBranch of execution.taskBranches || []) {
        await run('git', ['merge', '--no-ff', '--no-edit', taskBranch], { cwd: workspace.path });
        integratedBranches.push(taskBranch);
      }
      await run('git', ['push', '--set-upstream', 'origin', phase.branch], { cwd: workspace.path });
      const { stdout } = await run('git', ['rev-parse', 'HEAD'], { cwd: workspace.path });
      return { branch: phase.branch, headSha: stdout.trim(), integratedBranches };
    },

    async verifyLocal(_phase, workspace) {
      await run('node', ['ops/grinions/scripts/verify.mjs'], { cwd: workspace.path });
      return run('node', ['--test', 'ops/grinions/test/idempotency.test.mjs', 'ops/grinions/test/ralphy.test.mjs', 'ops/grinions/test/process.test.mjs'], { cwd: workspace.path });
    },

    async verifyPhase(phase, workspace) {
      return run('openspec', ['validate', phase.openspecId, '--strict', '--no-interactive'], { cwd: workspace.path });
    },

    async createOrUpdatePr(phase, meta = {}) {
      const existing = await run('gh', ['pr', 'list', '--head', phase.branch, '--json', 'number', '--jq', '.[0].number // empty'], { cwd: repoRoot });
      if (existing.stdout.trim()) return { number: Number(existing.stdout.trim()), reused: true };
      const cwd = meta.workspace?.path || repoRoot;
      const created = await run('gh', ['pr', 'create', '--base', 'main', '--head', phase.branch, '--title', `phase(${phase.phaseId}): ${phase.openspecId} [GRINION]`, '--body-file', `ops/reports/phase-${phase.phaseId}.md`], { cwd });
      return { url: created.stdout.trim(), reused: false };
    },

    async watchPr(phase, pr) {
      const target = prTarget(pr);
      const timeoutMs = Number(process.env.GRINIONS_PR_WATCH_TIMEOUT_MS || 20 * 60 * 1000);
      const deadline = Date.now() + timeoutMs;
      while (Date.now() < deadline) {
        const allChecks = await readPrChecks(repoRoot, target, false);
        const requiredChecks = await readPrChecks(repoRoot, target, true);
        const gates = selectedGateChecks(allChecks, requiredChecks, phase);
        const state = assertChecksPass(gates);
        if (state.passed) return { passed: true, checks: gates };
        await sleep(10000);
      }
      throw new Error(`PR_CHECK_TIMEOUT:${target}`);
    },

    async judge(phase, pr) {
      const target = prTarget(pr);
      const { stdout } = await run('gh', ['pr', 'view', target, '--json', 'mergeable,reviewDecision,headRefOid,number'], { cwd: repoRoot });
      const details = parseJson(stdout, 'gh pr view');
      if (details.mergeable !== 'MERGEABLE') throw new Error(`PR_NOT_MERGEABLE:${details.mergeable}`);
      if (['CHANGES_REQUESTED', 'REVIEW_REQUIRED'].includes(details.reviewDecision)) {
        throw new Error(`PR_REVIEW_BLOCKED:${details.reviewDecision}`);
      }

      const allChecks = await readPrChecks(repoRoot, target, false);
      const requiredChecks = await readPrChecks(repoRoot, target, true);
      const gates = selectedGateChecks(allChecks, requiredChecks, phase);
      const state = assertChecksPass(gates);
      if (!state.passed) throw new Error(state.missing ? 'NO_GATE_CHECKS_FOUND' : 'PR_CHECKS_PENDING');

      const unresolved = await unresolvedReviewThreads(repoRoot, Number(details.number));
      if (unresolved.length) throw new Error(`UNRESOLVED_REVIEW_THREADS:${unresolved.length}`);

      return {
        passed: true,
        headRefOid: details.headRefOid,
        reviewDecision: details.reviewDecision || null,
        checks: gates,
        unresolvedReviewThreads: 0,
      };
    },

    async requireHighRiskApproval(phase) {
      throw new Error(`HIGH_RISK_APPROVAL_REQUIRED:${phase.phaseId}`);
    },

    async squashMerge(_phase, pr, { judgment } = {}) {
      const target = prTarget(pr);
      const { stdout: viewOut } = await run('gh', ['pr', 'view', target, '--json', 'headRefOid'], { cwd: repoRoot });
      const headRefOid = judgment?.headRefOid || parseJson(viewOut, 'gh pr view').headRefOid;
      if (!headRefOid) throw new Error('Missing PR head SHA before merge');

      await run('gh', ['pr', 'merge', target, '--squash', '--match-head-commit', headRefOid], { cwd: repoRoot });
      const { stdout } = await run('gh', ['pr', 'view', target, '--json', 'mergedAt,mergeCommit'], { cwd: repoRoot });
      const merged = parseJson(stdout, 'gh pr view after merge');
      const sha = merged?.mergeCommit?.oid;
      if (!merged?.mergedAt || !sha) throw new Error('Squash merge completed without verifiable merge commit');
      return { sha, mergedAt: merged.mergedAt, headRefOid };
    },

    async verifyPostMerge(phase, merge) {
      if (!merge?.sha) throw new TypeError('merge SHA is required for post-merge verification');
      await run('git', ['fetch', 'origin', 'main'], { cwd: repoRoot });
      await run('git', ['merge-base', '--is-ancestor', merge.sha, 'origin/main'], { cwd: repoRoot });
      const { stdout: mainOut } = await run('git', ['rev-parse', 'origin/main'], { cwd: repoRoot });

      const verifyPath = join(tmpdir(), 'grinions-post-merge', `${safeSegment(phase.phaseId)}-${merge.sha.slice(0, 12)}`);
      await mkdir(dirname(verifyPath), { recursive: true });
      await removeWorktree(repoRoot, verifyPath);
      await run('git', ['worktree', 'add', '--detach', verifyPath, 'origin/main'], { cwd: repoRoot });

      try {
        await run('node', ['ops/grinions/scripts/verify.mjs'], { cwd: verifyPath });
        await run('node', ['--test', 'ops/grinions/test/idempotency.test.mjs', 'ops/grinions/test/ralphy.test.mjs', 'ops/grinions/test/process.test.mjs'], { cwd: verifyPath });
        await run('openspec', ['validate', phase.openspecId, '--strict', '--no-interactive'], { cwd: verifyPath });
      } finally {
        await removeWorktree(repoRoot, verifyPath);
      }

      return { passed: true, mergeSha: merge.sha, mainSha: mainOut.trim() };
    },

    async attest(phase, evidence) {
      const rollbackPath = resolve(repoRoot, 'ops', 'rollback', `phase-${phase.phaseId}.json`);
      const rollback = await readJsonIfExists(rollbackPath);
      await writeJson(rollbackPath, {
        ...rollback,
        mergeSha: evidence.merge?.sha || null,
        verifiedMainSha: evidence.postMerge?.mainSha || null,
        rollbackCommands: evidence.merge?.sha ? [`git revert ${evidence.merge.sha}`] : rollback.rollbackCommands || [],
        updatedAt: new Date().toISOString(),
      });

      const path = resolve(repoRoot, 'ops', 'receipts', `phase-${phase.phaseId}.json`);
      return writeJson(path, { phaseId: phase.phaseId, completedAt: new Date().toISOString(), ...evidence });
    },
  };
}
