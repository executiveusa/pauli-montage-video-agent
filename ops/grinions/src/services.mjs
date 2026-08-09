import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import {
  belongsToPhase,
  boundedBead,
  compileBeadTaskPacket,
  isClosed,
  normalizeBdItems,
} from './beads.mjs';
import {
  classifyCompletionEvidence,
  parseWorkIdentity,
  sameWorkIdentity,
  workIdentity,
  workIdentityMarker,
} from './completion.mjs';
import { run } from './process.mjs';
import { runRalphy } from './ralphy.mjs';
import { validatePhaseReceipt } from './receipt.mjs';

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

async function bdItems(args, cwd) {
  const { stdout } = await run('bd', [...args, '--json'], { cwd });
  return normalizeBdItems(parseJson(stdout, `bd ${args.join(' ')}`));
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

async function repositoryName(repoRoot) {
  const { stdout } = await run('gh', ['repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner'], { cwd: repoRoot });
  return stdout.trim().toLowerCase();
}

async function allPullRequests(repoRoot) {
  const { stdout } = await run('gh', [
    'pr', 'list', '--state', 'all', '--limit', '1000',
    '--json', 'number,url,state,mergedAt,mergeCommit,headRefName,headRefOid,baseRefName,title,body,closedAt',
  ], { cwd: repoRoot });
  const pullRequests = parseJson(stdout, 'gh pr list --state all');
  if (!Array.isArray(pullRequests)) throw new Error('GitHub pull request history was not an array');
  if (pullRequests.length >= 1000) throw new Error('PHASE_PR_HISTORY_LIMIT_EXCEEDED');
  return pullRequests;
}

async function pullRequestsForBranch(repoRoot, branch) {
  const { stdout } = await run('gh', [
    'pr', 'list', '--state', 'all', '--head', branch, '--limit', '100',
    '--json', 'number,url,state,mergedAt,mergeCommit,headRefName,headRefOid,baseRefName,title,body,closedAt',
  ], { cwd: repoRoot });
  const pullRequests = parseJson(stdout, 'gh pr list --state all --head');
  if (!Array.isArray(pullRequests)) throw new Error('GitHub branch pull request history was not an array');
  if (pullRequests.length >= 100) throw new Error('PHASE_PR_HISTORY_LIMIT_EXCEEDED');
  return pullRequests;
}

async function inspectPrCreationState(repoRoot, cwd, phase) {
  await run('git', ['fetch', 'origin', 'main'], { cwd });
  const current = await runResult('git', ['merge-base', '--is-ancestor', 'origin/main', 'HEAD'], { cwd });
  if (current.code !== 0) throw new Error(`PHASE_BRANCH_BEHIND_MAIN:${phase.phaseId}`);

  const [{ stdout: headTree }, { stdout: mainTree }, { stdout: headSha }, { stdout: branch }] = await Promise.all([
    run('git', ['rev-parse', 'HEAD^{tree}'], { cwd }),
    run('git', ['rev-parse', 'origin/main^{tree}'], { cwd }),
    run('git', ['rev-parse', 'HEAD'], { cwd }),
    run('git', ['branch', '--show-current'], { cwd }),
  ]);
  if (branch.trim() !== phase.branch) throw new Error(`PHASE_BRANCH_MISMATCH:${phase.phaseId}:${branch.trim()}`);
  if (headTree.trim() === mainTree.trim()) throw new Error(`PHASE_NO_TREE_DELTA:${phase.phaseId}`);

  return {
    headTree: headTree.trim(),
    mainTree: mainTree.trim(),
    headSha: headSha.trim(),
    branch: branch.trim(),
    pullRequests: await pullRequestsForBranch(repoRoot, phase.branch),
  };
}

function adoptableOpenPullRequest(pullRequests, identity, phase, headSha) {
  if (pullRequests.length !== 1) return null;
  const [pr] = pullRequests;
  return pr.state === 'OPEN'
    && !pr.mergedAt
    && pr.headRefName === phase.branch
    && pr.baseRefName === 'main'
    && pr.headRefOid === headSha
    && sameWorkIdentity(parseWorkIdentity(pr.body), identity)
    ? pr
    : null;
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

function executionSummary(result) {
  return {
    code: result.code,
    stdoutTail: result.stdout.slice(-4000),
    stderrTail: result.stderr.slice(-4000),
  };
}

async function installGrinionsDependencies(cwd) {
  const cache = join(tmpdir(), 'grinions-npm-cache-v1');
  return run('npm', ['--cache', cache, 'ci', '--prefix', 'ops/grinions', '--ignore-scripts'], { cwd });
}

export function canonicalPrBranch(identity) {
  const digest = createHash('sha256').update(JSON.stringify(identity)).digest('hex').slice(0, 16);
  return `grinions/${safeSegment(identity.initiativeId).slice(0, 40)}/${safeSegment(identity.openspecId).slice(0, 60)}-${digest}`;
}

async function reserveIdentityBranch(cwd, phase, identity, headSha) {
  const branch = canonicalPrBranch(identity);
  const pushed = await runResult('git', [
    'push', `--force-with-lease=refs/heads/${branch}:`, 'origin', `HEAD:refs/heads/${branch}`,
  ], { cwd });
  if (pushed.code !== 0) {
    const fetched = await runResult('git', ['fetch', 'origin', `refs/heads/${branch}:refs/remotes/origin/${branch}`], { cwd });
    if (fetched.code !== 0) throw new Error(`PHASE_IDENTITY_RESERVATION_UNAVAILABLE:${phase.phaseId}`);
    const { stdout } = await run('git', ['rev-parse', `refs/remotes/origin/${branch}`], { cwd });
    if (stdout.trim() !== headSha) throw new Error(`PHASE_IDENTITY_RESERVATION_CONFLICT:${phase.phaseId}:${branch}`);
  }
  return branch;
}

async function canonicalCompletion(repoRoot, phase, identity) {
  await run('git', ['fetch', 'origin', 'main'], { cwd: repoRoot });
  const pullRequests = await allPullRequests(repoRoot);
  for (const pr of pullRequests) {
    const parsed = parseWorkIdentity(pr.body);
    if (
      parsed
      && !parsed.malformed
      && parsed.repository === identity.repository
      && parsed.initiativeId === identity.initiativeId
      && parsed.openspecId === identity.openspecId
      && pr.mergeCommit?.oid
    ) {
      const ancestry = await runResult('git', ['merge-base', '--is-ancestor', pr.mergeCommit.oid, 'origin/main'], { cwd: repoRoot });
      if (ancestry.code === 0) pr.integratedIntoMain = true;
      else if (ancestry.code === 1) pr.integratedIntoMain = false;
      else throw new Error(`git ancestry inspection failed with exit ${ancestry.code}: ${ancestry.stderr}`);
    }
  }
  const receiptRelativePath = `ops/receipts/phase-${phase.phaseId}.json`;
  const receiptPath = resolve(repoRoot, receiptRelativePath);
  const localReceipt = await readJsonIfExists(receiptPath, null);
  const { stdout: listedReceipt } = await run('git', [
    'ls-tree', '-r', '--name-only', 'origin/main', '--', receiptRelativePath,
  ], { cwd: repoRoot });
  let canonicalReceipt = null;
  if (listedReceipt.trim() === receiptRelativePath) {
    const { stdout } = await run('git', ['show', `origin/main:${receiptRelativePath}`], { cwd: repoRoot });
    canonicalReceipt = parseJson(stdout, `canonical phase receipt ${receiptRelativePath}`);
  }
  if (localReceipt && canonicalReceipt && !isDeepStrictEqual(localReceipt, canonicalReceipt)) {
    throw new Error(`PHASE_RECEIPT_CONFLICT:${phase.phaseId}`);
  }
  const receipt = canonicalReceipt || localReceipt;
  let receiptGitEvidence = null;
  if (receipt) {
    let receiptValid = true;
    try {
      validatePhaseReceipt(receipt);
    } catch {
      receiptValid = false;
    }
    if (receiptValid) {
      const [postMergeResolved, mergeResolved] = await Promise.all([
        runResult('git', ['rev-parse', '--verify', `${receipt.postMerge.mainSha}^{commit}`], { cwd: repoRoot }),
        runResult('git', ['rev-parse', '--verify', `${receipt.merge.sha}^{commit}`], { cwd: repoRoot }),
      ]);
      receiptGitEvidence = {
        postMergeShaValid: postMergeResolved.code === 0,
        mergeIntegratedAtPostMerge: false,
        postMergeIntegratedIntoMain: false,
      };
      if (postMergeResolved.code !== 0 || mergeResolved.code !== 0) {
        return classifyCompletionEvidence({
          identity: { ...identity, phaseId: phase.phaseId },
          branch: phase.branch,
          canonicalBranch: canonicalPrBranch(identity),
          pullRequests,
          receipt,
          receiptGitEvidence,
        });
      }
      const mergeAtPostMerge = await runResult('git', [
        'merge-base', '--is-ancestor', receipt.merge?.sha, receipt.postMerge.mainSha,
      ], { cwd: repoRoot });
      const postMergeOnMain = await runResult('git', [
        'merge-base', '--is-ancestor', receipt.postMerge.mainSha, 'origin/main',
      ], { cwd: repoRoot });
      for (const result of [mergeAtPostMerge, postMergeOnMain]) {
        if (![0, 1].includes(result.code)) {
          throw new Error(`receipt git ancestry inspection failed with exit ${result.code}: ${result.stderr}`);
        }
      }
      receiptGitEvidence.mergeIntegratedAtPostMerge = mergeAtPostMerge.code === 0;
      receiptGitEvidence.postMergeIntegratedIntoMain = postMergeOnMain.code === 0;
    }
  }
  return classifyCompletionEvidence({
    identity: { ...identity, phaseId: phase.phaseId },
    branch: phase.branch,
    canonicalBranch: canonicalPrBranch(identity),
    pullRequests,
    receipt,
    receiptGitEvidence,
  });
}

export function selectRalphyTaskBranch(before, after, beadId) {
  const created = [...after].filter((branch) => !before.has(branch) && branch.startsWith('ralphy/'));
  if (created.length !== 1) throw new Error(`RALPHY_TASK_BRANCH_AMBIGUOUS:${beadId}:${created.length}`);
  const token = String(beadId).toLowerCase();
  const normalized = created[0].toLowerCase();
  const exactPrefix = `ralphy/bead-${token}`;
  if (normalized !== exactPrefix && !normalized.startsWith(`${exactPrefix}-`) && !normalized.startsWith(`${exactPrefix}/`)) {
    throw new Error(`RALPHY_TASK_BRANCH_IDENTITY_MISMATCH:${beadId}`);
  }
  return created[0];
}

export function createShellServices({ repoRoot = process.cwd() } = {}) {
  return {
    async classifyPhaseCompletion(phase) {
      try {
        const repository = await repositoryName(repoRoot);
        const identity = workIdentity({ repository, ...phase });
        return await canonicalCompletion(repoRoot, phase, identity);
      } catch (error) {
        if (String(error.message).startsWith('PHASE_PR_HISTORY_LIMIT_EXCEEDED')) throw error;
        throw new Error(`PHASE_COMPLETION_EVIDENCE_UNAVAILABLE:${phase.phaseId}:${error.message}`);
      }
    },

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

    async selectReadyBead(phase, workspace) {
      const ready = await bdItems(['ready'], workspace.path);
      return ready.find((issue) => belongsToPhase(issue, phase)) || null;
    },

    async phaseBeadStatus(phase, workspace) {
      const open = (await bdItems(['list'], workspace.path)).filter((issue) => belongsToPhase(issue, phase) && !isClosed(issue));
      const closed = (await bdItems(['list', '--status', 'closed'], workspace.path)).filter((issue) => belongsToPhase(issue, phase));
      const ids = new Set([...open, ...closed].map((issue) => issue.id).filter(Boolean));
      return { total: ids.size, open: open.length, closed: closed.length };
    },

    async claimBead(phase, workspace, ready) {
      const agentId = process.env.GRINIONS_AGENT_ID || 'grinions';
      const before = (await bdItems(['show', ready.id], workspace.path))[0] || ready;
      const status = String(before.status || '').toLowerCase();
      const assignee = before.assignee || before.owner || before.assigned_to || null;

      if (status === 'in_progress') {
        if (assignee && assignee !== agentId) throw new Error(`BEAD_ALREADY_CLAIMED:${ready.id}:${assignee}`);
      } else {
        await run('bd', ['update', ready.id, '--claim', '--assignee', agentId, '--json'], { cwd: workspace.path });
      }

      const claimed = (await bdItems(['show', ready.id], workspace.path))[0];
      if (!claimed) throw new Error(`BEAD_NOT_FOUND_AFTER_CLAIM:${ready.id}`);
      return boundedBead(claimed, phase);
    },

    async compileBead(phase, _workspace, bead) {
      const taskFile = join(tmpdir(), 'grinions-bead-packets', safeSegment(phase.phaseId), `${safeSegment(bead.id)}.md`);
      await mkdir(dirname(taskFile), { recursive: true });
      await writeFile(taskFile, compileBeadTaskPacket(bead, phase), 'utf8');
      return { beadId: bead.id, taskFile };
    },

    async executeBead(phase, workspace, bead, packet) {
      const before = await listBranches(workspace.path);
      const { stdout: baseOut } = await run('git', ['rev-parse', phase.branch], { cwd: workspace.path });
      const baseHeadSha = baseOut.trim();
      const result = await runRalphy({
        cwd: workspace.path,
        taskFile: packet.taskFile,
        baseBranch: phase.branch,
        maxRetries: 3,
      });
      const after = await listBranches(workspace.path);
      const taskBranch = selectRalphyTaskBranch(before, after, bead.id);
      const ancestry = await runResult('git', ['merge-base', '--is-ancestor', baseHeadSha, taskBranch], { cwd: workspace.path });
      if (ancestry.code !== 0) throw new Error(`RALPHY_TASK_BRANCH_NOT_DESCENDANT:${bead.id}`);
      const { stdout: taskOut } = await run('git', ['rev-parse', taskBranch], { cwd: workspace.path });
      const taskHeadSha = taskOut.trim();
      if (taskHeadSha === baseHeadSha) throw new Error(`RALPHY_TASK_BRANCH_EMPTY:${bead.id}`);
      return { ...executionSummary(result), taskBranches: [taskBranch], taskBranch, baseHeadSha, taskHeadSha };
    },

    async integrateBead(phase, workspace, bead, execution) {
      if (!execution?.taskBranch || execution.taskBranches?.length !== 1 || execution.taskBranches[0] !== execution.taskBranch) {
        throw new Error(`RALPHY_TASK_BRANCH_EVIDENCE_INVALID:${bead.id}`);
      }
      const [{ stdout: baseOut }, { stdout: taskOut }] = await Promise.all([
        run('git', ['rev-parse', phase.branch], { cwd: workspace.path }),
        run('git', ['rev-parse', execution.taskBranch], { cwd: workspace.path }),
      ]);
      if (baseOut.trim() !== execution.baseHeadSha || taskOut.trim() !== execution.taskHeadSha) {
        throw new Error(`RALPHY_TASK_BRANCH_MOVED:${bead.id}`);
      }
      const ancestry = await runResult('git', [
        'merge-base', '--is-ancestor', execution.baseHeadSha, execution.taskHeadSha,
      ], { cwd: workspace.path });
      if (ancestry.code !== 0) throw new Error(`RALPHY_TASK_BRANCH_NOT_DESCENDANT:${bead.id}`);
      await run('git', ['checkout', phase.branch], { cwd: workspace.path });
      await run('git', ['merge', '--no-ff', '--no-edit', execution.taskBranch], { cwd: workspace.path });
      await run('git', ['push', '--set-upstream', 'origin', phase.branch], { cwd: workspace.path });
      const { stdout } = await run('git', ['rev-parse', 'HEAD'], { cwd: workspace.path });
      return { beadId: bead.id, branch: phase.branch, headSha: stdout.trim(), integratedBranches: [execution.taskBranch] };
    },

    async verifyBead(_phase, workspace, bead, integration) {
      const commands = [];
      for (const verification of bead.verificationCommands) {
        const result = await run(verification.command, verification.args, {
          cwd: workspace.path,
          timeoutMs: 20 * 60 * 1000,
          maxOutputBytes: 10 * 1024 * 1024,
        });
        commands.push({ command: verification.command, args: verification.args, ...executionSummary(result) });
      }
      return {
        beadId: bead.id,
        headSha: integration.headSha,
        contract: bead.verification,
        requiredEvidence: bead.evidence,
        commands,
        passed: true,
      };
    },

    async closeBead(_phase, workspace, bead, integration, verification) {
      const evidence = verification.requiredEvidence.join('; ');
      const reason = `Verified on ${integration.headSha}. Evidence contract: ${evidence}`;
      await run('bd', ['close', bead.id, '--reason', reason, '--json'], { cwd: workspace.path });
      const closed = (await bdItems(['show', bead.id], workspace.path))[0];
      if (!closed || !isClosed(closed)) throw new Error(`BEAD_CLOSE_NOT_CONFIRMED:${bead.id}`);
      return { id: bead.id, status: closed.status, reason };
    },

    async verifyLocal(_phase, workspace) {
      await run('node', ['ops/grinions/scripts/verify.mjs'], { cwd: workspace.path });
      await installGrinionsDependencies(workspace.path);
      return run('npm', ['test', '--prefix', 'ops/grinions'], { cwd: workspace.path });
    },

    async verifyPhase(phase, workspace) {
      return run('openspec', ['validate', phase.openspecId, '--strict', '--no-interactive'], { cwd: workspace.path });
    },

    async preparePullRequest(phase, workspace) {
      const cwd = workspace?.path || repoRoot;
      const state = await inspectPrCreationState(repoRoot, cwd, phase);
      if (state.pullRequests.length) {
        throw new Error(`PHASE_PR_STATE_CONFLICT:${phase.phaseId}:${state.pullRequests.map((pr) => `${pr.number}:${pr.state}`).join(',')}`);
      }
      return { passed: true, headTree: state.headTree, mainTree: state.mainTree, headSha: state.headSha };
    },

    async createOrUpdatePr(phase, meta = {}) {
      const cwd = meta.workspace?.path || repoRoot;
      const repository = await repositoryName(repoRoot);
      const identity = workIdentity({ repository, ...phase });
      const initialCompletion = await canonicalCompletion(repoRoot, phase, identity);
      if (initialCompletion.status === 'already_completed') {
        return {
          alreadyCompleted: true,
          completion: initialCompletion,
          reused: true,
          headSha: initialCompletion.pullRequest?.headRefOid || null,
        };
      }
      if (initialCompletion.status !== 'not_completed' && initialCompletion.reason !== 'matching_pull_request_open') {
        throw new Error(`PHASE_COMPLETION_INCONSISTENT:${phase.phaseId}:${initialCompletion.reason}`);
      }
      const state = await inspectPrCreationState(repoRoot, cwd, phase);
      if (state.pullRequests.length) {
        throw new Error(`PHASE_PR_STATE_CONFLICT:${phase.phaseId}:${state.pullRequests.map((pr) => `${pr.number}:${pr.state}`).join(',')}`);
      }

      const prBranch = await reserveIdentityBranch(cwd, phase, identity, state.headSha);
      const completion = await canonicalCompletion(repoRoot, phase, identity);
      if (completion.status === 'already_completed') {
        return { alreadyCompleted: true, completion, reused: true, headSha: state.headSha };
      }

      const identityPrs = await pullRequestsForBranch(repoRoot, prBranch);
      const adoptable = adoptableOpenPullRequest(identityPrs, identity, { ...phase, branch: prBranch }, state.headSha);
      if (adoptable) {
        const recoveryEvidence = await canonicalCompletion(repoRoot, phase, identity);
        if (recoveryEvidence.reason !== 'matching_pull_request_open') {
          throw new Error(`PHASE_COMPLETION_INCONSISTENT:${phase.phaseId}:${recoveryEvidence.reason || recoveryEvidence.status}`);
        }
        const refreshed = adoptableOpenPullRequest(
          [recoveryEvidence.pullRequest], identity, { ...phase, branch: prBranch }, state.headSha,
        );
        if (!refreshed) throw new Error(`PHASE_PR_RECOVERY_UNVERIFIED:${phase.phaseId}`);
        return {
          number: refreshed.number,
          url: refreshed.url,
          reused: true,
          headSha: state.headSha,
          headRefName: refreshed.headRefName,
          baseRefName: refreshed.baseRefName,
          identity,
        };
      }
      if (completion.status !== 'not_completed' || identityPrs.length) {
        const reason = completion.reason || identityPrs.map((pr) => `${pr.number}:${pr.state}`).join(',');
        throw new Error(`PHASE_COMPLETION_INCONSISTENT:${phase.phaseId}:${reason}`);
      }

      const reportPath = resolve(cwd, 'ops', 'reports', `phase-${phase.phaseId}.md`);
      const report = await readFile(reportPath, 'utf8');
      const bodyPath = join(tmpdir(), 'grinions-pr-bodies', `${safeSegment(phase.phaseId)}-${safeSegment(phase.openspecId)}.md`);
      await mkdir(dirname(bodyPath), { recursive: true });
      await writeFile(bodyPath, `${workIdentityMarker({ repository, ...phase })}\n\n${report}`, 'utf8');
      const created = await run('gh', ['pr', 'create', '--base', 'main', '--head', prBranch, '--title', `phase(${phase.phaseId}): ${phase.openspecId} [GRINION]`, '--body-file', bodyPath], { cwd });
      const after = await pullRequestsForBranch(repoRoot, prBranch);
      const verified = adoptableOpenPullRequest(after, identity, { ...phase, branch: prBranch }, state.headSha);
      if (!verified) throw new Error(`PHASE_PR_CREATE_UNVERIFIED:${phase.phaseId}`);
      const createdEvidence = await canonicalCompletion(repoRoot, phase, identity);
      if (createdEvidence.reason !== 'matching_pull_request_open') {
        throw new Error(`PHASE_COMPLETION_INCONSISTENT:${phase.phaseId}:${createdEvidence.reason || createdEvidence.status}`);
      }
      const finalPr = adoptableOpenPullRequest(
        [createdEvidence.pullRequest], identity, { ...phase, branch: prBranch }, state.headSha,
      );
      if (!finalPr) throw new Error(`PHASE_PR_CREATE_UNVERIFIED:${phase.phaseId}`);
      return {
        number: finalPr.number,
        url: finalPr.url || created.stdout.trim(),
        reused: false,
        headSha: state.headSha,
        headRefName: finalPr.headRefName,
        baseRefName: finalPr.baseRefName,
        identity,
      };
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

    async squashMerge(phase, pr, { judgment } = {}) {
      const repository = await repositoryName(repoRoot);
      const identity = workIdentity({ repository, ...phase });
      const completion = await canonicalCompletion(repoRoot, phase, identity);
      if (completion.reason !== 'matching_pull_request_open') {
        throw new Error(`PHASE_COMPLETION_INCONSISTENT:${phase.phaseId}:${completion.reason || completion.status}`);
      }
      const canonical = adoptableOpenPullRequest(
        [completion.pullRequest],
        identity,
        { ...phase, branch: canonicalPrBranch(identity) },
        completion.pullRequest?.headRefOid,
      );
      if (
        !canonical
        || Number(pr?.number) !== canonical.number
        || pr.headSha !== canonical.headRefOid
        || pr.headRefName !== canonical.headRefName
        || pr.baseRefName !== canonical.baseRefName
        || !sameWorkIdentity(pr.identity, identity)
      ) {
        throw new Error(`PHASE_MERGE_TARGET_MISMATCH:${phase.phaseId}`);
      }
      if (judgment?.headRefOid && judgment.headRefOid !== canonical.headRefOid) {
        throw new Error(`PHASE_MERGE_HEAD_MISMATCH:${phase.phaseId}`);
      }
      const target = String(canonical.number);
      const { stdout: viewOut } = await run('gh', [
        'pr', 'view', target, '--json', 'number,state,mergedAt,body,headRefOid,headRefName,baseRefName',
      ], { cwd: repoRoot });
      const viewed = parseJson(viewOut, 'gh pr view');
      if (
        viewed.number !== canonical.number
        || viewed.state !== 'OPEN'
        || viewed.mergedAt
        || !sameWorkIdentity(parseWorkIdentity(viewed.body), identity)
        || viewed.headRefOid !== canonical.headRefOid
        || viewed.headRefName !== canonical.headRefName
        || viewed.baseRefName !== canonical.baseRefName
      ) {
        throw new Error(`PHASE_MERGE_TARGET_MOVED:${phase.phaseId}`);
      }
      const headRefOid = canonical.headRefOid;

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
        await installGrinionsDependencies(verifyPath);
        await run('npm', ['test', '--prefix', 'ops/grinions'], { cwd: verifyPath });
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
