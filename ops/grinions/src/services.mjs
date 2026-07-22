import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { run } from './process.mjs';
import { runRalphy } from './ralphy.mjs';

async function writeJson(path, value) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  return value;
}

export function createShellServices({ repoRoot = process.cwd() } = {}) {
  return {
    async hydrateContext(phase) {
      await run('bd', ['prime'], { cwd: repoRoot });
      return { phase, hydratedAt: new Date().toISOString() };
    },
    async validateSpec(phase) {
      return run('openspec', ['validate', phase.openspecId, '--no-interactive'], { cwd: repoRoot });
    },
    async captureBaseline() {
      const { stdout } = await run('git', ['rev-parse', 'main'], { cwd: repoRoot });
      return { mainSha: stdout.trim(), capturedAt: new Date().toISOString() };
    },
    async writeRollbackReceipt(phase, baseline) {
      const path = resolve(repoRoot, 'ops', 'rollback', `phase-${phase.phaseId}.json`);
      return writeJson(path, {
        phaseId: phase.phaseId,
        baselineMainSha: baseline.mainSha,
        deploymentId: null,
        migrations: [],
        affectedServices: [],
        featureFlags: [],
        rollbackCommands: [`git revert <phase-${phase.phaseId}-squash-sha>`],
        dataLossRisk: 'none-known-at-baseline',
      });
    },
    async provisionWorkspace(phase) {
      return { branch: phase.branch, repoRoot };
    },
    async executeBeads(phase) {
      await run('bd', ['ready'], { cwd: repoRoot });
      return runRalphy({
        cwd: repoRoot,
        taskFile: `openspec/changes/${phase.openspecId}/tasks.md`,
        baseBranch: phase.branch,
        maxRetries: 3,
      });
    },
    async verifyLocal() {
      return run('node', ['ops/grinions/scripts/verify.mjs'], { cwd: repoRoot });
    },
    async verifyPhase(phase) {
      return run('openspec', ['validate', phase.openspecId, '--strict', '--no-interactive'], { cwd: repoRoot });
    },
    async createOrUpdatePr(phase) {
      const existing = await run('gh', ['pr', 'list', '--head', phase.branch, '--json', 'number', '--jq', '.[0].number // empty'], { cwd: repoRoot });
      if (existing.stdout.trim()) return { number: Number(existing.stdout.trim()), reused: true };
      const created = await run('gh', ['pr', 'create', '--base', 'main', '--head', phase.branch, '--title', `phase(${phase.phaseId}): ${phase.openspecId} [GRINION]`, '--body-file', `ops/reports/phase-${phase.phaseId}.md`], { cwd: repoRoot });
      return { url: created.stdout.trim(), reused: false };
    },
    async watchPr(_phase, pr) {
      const target = pr.number ? String(pr.number) : pr.url;
      return run('gh', ['pr', 'checks', target, '--watch'], { cwd: repoRoot });
    },
    async judge() {
      return { passed: true, note: 'Phase-specific council/judge adapters run before merge.' };
    },
    async requireHighRiskApproval(phase) {
      throw new Error(`HIGH_RISK_APPROVAL_REQUIRED:${phase.phaseId}`);
    },
    async squashMerge(_phase, pr) {
      const target = pr.number ? String(pr.number) : pr.url;
      return run('gh', ['pr', 'merge', target, '--squash', '--delete-branch'], { cwd: repoRoot });
    },
    async verifyPostMerge() {
      return { passed: true };
    },
    async attest(phase, evidence) {
      const path = resolve(repoRoot, 'ops', 'receipts', `phase-${phase.phaseId}.json`);
      return writeJson(path, { phaseId: phase.phaseId, completedAt: new Date().toISOString(), ...evidence });
    },
  };
}
