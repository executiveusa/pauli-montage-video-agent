import assert from 'node:assert/strict';
import test from 'node:test';
import {
  belongsToPhase,
  boundedBead,
  compileBeadTaskPacket,
  normalizeBdItems,
} from '../src/beads.mjs';

const phase = {
  phaseId: '01',
  openspecId: 'phase-01-repo-truth',
  branch: 'phase/01-repo-truth',
};

function validIssue(overrides = {}) {
  return {
    id: 'bd-a1b2',
    title: 'Audit source repositories',
    description: 'Inspect the approved source repositories and produce the capability matrix.',
    design: 'Use targeted repository inspection and record one canonical owner per capability.',
    acceptance: 'Capability, duplication, license, and migration matrices exist and have no unresolved duplicate owners.',
    status: 'open',
    labels: ['phase:01'],
    dependencies: [{ id: 'bd-root' }],
    metadata: {
      openspec_id: 'phase-01-repo-truth',
      grinions: {
        scope: ['docs/capability-matrix.md', 'docs/license-boundaries.md'],
        verification: 'Validate the generated matrices and repository links.',
        verification_commands: [
          { command: 'node', args: ['ops/grinions/scripts/verify.mjs'] },
        ],
        evidence: ['matrix file paths', 'source repository references'],
        prohibited_changes: ['Do not vendor external source code', 'Do not change product runtime'],
        rollback: 'Revert the Bead integration commit from the phase branch.',
      },
    },
    ...overrides,
  };
}

test('normalizes plain and enveloped Beads JSON', () => {
  const issue = validIssue();
  assert.equal(normalizeBdItems([issue])[0].id, issue.id);
  assert.equal(normalizeBdItems({ issues: [issue] })[0].id, issue.id);
  assert.equal(normalizeBdItems({ data: [issue] })[0].id, issue.id);
});

test('phase matching accepts structured metadata or explicit phase labels', () => {
  assert.equal(belongsToPhase(validIssue(), phase), true);
  const labelOnly = validIssue({ metadata: {}, labels: ['phase:01'] });
  assert.equal(belongsToPhase(labelOnly, phase), true);
  assert.equal(belongsToPhase(validIssue({ metadata: {}, labels: ['phase:02'] }), phase), false);
});

test('bounded Bead requires scope, verification, evidence, prohibited changes, rollback and commands', () => {
  const bead = boundedBead(validIssue(), phase);
  assert.equal(bead.id, 'bd-a1b2');
  assert.deepEqual(bead.dependencies, ['bd-root']);
  assert.equal(bead.verificationCommands[0].command, 'node');

  const invalid = validIssue();
  delete invalid.metadata.grinions.rollback;
  assert.throws(() => boundedBead(invalid, phase), /BEAD_CONTRACT_INVALID:bd-a1b2:rollback/);
});

test('compiled Ralphy packet contains one claimed Bead and explicit safety contract', () => {
  const bead = boundedBead(validIssue(), phase);
  const packet = compileBeadTaskPacket(bead, phase);
  assert.match(packet, /Bead: `bd-a1b2`/);
  assert.match(packet, /Do not expand scope silently/);
  assert.match(packet, /BEAD-bd-a1b2: Audit source repositories/);
  assert.match(packet, /Do not vendor external source code/);
  assert.match(packet, /node ops\/grinions\/scripts\/verify\.mjs/);
  assert.equal((packet.match(/- \[ \]/g) || []).length, 1);
});
