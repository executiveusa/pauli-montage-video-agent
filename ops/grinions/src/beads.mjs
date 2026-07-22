function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value == null) return [];
  return [value];
}

export function normalizeBdItems(payload) {
  if (Array.isArray(payload)) return payload;
  for (const key of ['issues', 'items', 'data', 'results']) {
    if (Array.isArray(payload?.[key])) return payload[key];
  }
  return payload && typeof payload === 'object' ? [payload] : [];
}

function normalizedLabels(issue) {
  return asArray(issue?.labels)
    .flatMap((label) => typeof label === 'string' ? [label] : [label?.name])
    .filter(Boolean)
    .map((label) => String(label).toLowerCase());
}

function metadata(issue) {
  return issue?.metadata && typeof issue.metadata === 'object' && !Array.isArray(issue.metadata)
    ? issue.metadata
    : {};
}

export function belongsToPhase(issue, phase) {
  const meta = metadata(issue);
  const labels = new Set(normalizedLabels(issue));
  return meta.openspec_id === phase.openspecId
    || meta.phase_id === phase.phaseId
    || labels.has(`openspec:${String(phase.openspecId).toLowerCase()}`)
    || labels.has(`phase:${String(phase.phaseId).toLowerCase()}`);
}

export function isClosed(issue) {
  const status = String(issue?.status || '').toLowerCase();
  return ['closed', 'done', 'completed', 'resolved'].includes(status);
}

function requireText(value, name, beadId) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`BEAD_CONTRACT_INVALID:${beadId}:${name}`);
  }
  return value.trim();
}

function requireStringArray(value, name, beadId) {
  if (!Array.isArray(value) || value.length === 0 || value.some((entry) => typeof entry !== 'string' || !entry.trim())) {
    throw new Error(`BEAD_CONTRACT_INVALID:${beadId}:${name}`);
  }
  return value.map((entry) => entry.trim());
}

function requireVerificationCommands(value, beadId) {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`BEAD_CONTRACT_INVALID:${beadId}:verification_commands`);
  }
  return value.map((entry, index) => {
    if (!entry || typeof entry !== 'object' || typeof entry.command !== 'string' || !entry.command.trim()) {
      throw new Error(`BEAD_CONTRACT_INVALID:${beadId}:verification_commands[${index}]`);
    }
    if (entry.args != null && (!Array.isArray(entry.args) || entry.args.some((arg) => typeof arg !== 'string'))) {
      throw new Error(`BEAD_CONTRACT_INVALID:${beadId}:verification_commands[${index}].args`);
    }
    return { command: entry.command.trim(), args: entry.args || [] };
  });
}

export function boundedBead(issue, phase) {
  const id = requireText(issue?.id, 'id', 'unknown');
  if (!belongsToPhase(issue, phase)) throw new Error(`BEAD_PHASE_MISMATCH:${id}:${phase.phaseId}`);

  const meta = metadata(issue);
  const contract = meta.grinions && typeof meta.grinions === 'object' && !Array.isArray(meta.grinions)
    ? meta.grinions
    : {};

  return {
    id,
    title: requireText(issue?.title, 'title', id),
    description: requireText(issue?.description, 'description', id),
    design: requireText(issue?.design, 'design', id),
    acceptance: requireText(issue?.acceptance || issue?.acceptance_criteria, 'acceptance', id),
    scope: requireStringArray(contract.scope, 'scope', id),
    verification: requireText(contract.verification, 'verification', id),
    verificationCommands: requireVerificationCommands(contract.verification_commands, id),
    evidence: requireStringArray(contract.evidence, 'evidence', id),
    prohibitedChanges: requireStringArray(contract.prohibited_changes, 'prohibited_changes', id),
    rollback: requireText(contract.rollback, 'rollback', id),
    dependencies: asArray(issue?.dependencies).map((dependency) => {
      if (typeof dependency === 'string') return dependency;
      return dependency?.id || dependency?.issue_id || dependency?.depends_on_id;
    }).filter(Boolean),
    notes: typeof issue?.notes === 'string' ? issue.notes.trim() : '',
    raw: issue,
  };
}

function section(title, lines) {
  return `## ${title}\n\n${lines.map((line) => `- ${line}`).join('\n')}`;
}

export function compileBeadTaskPacket(bead, phase) {
  const dependencies = bead.dependencies.length ? bead.dependencies : ['None reported by Beads'];
  const verificationCommands = bead.verificationCommands.map(({ command, args }) => `\`${[command, ...args].join(' ')}\``);

  return `# GRINIONS bounded Bead task\n\n- Bead: \`${bead.id}\`\n- Phase: \`${phase.phaseId}\`\n- OpenSpec: \`${phase.openspecId}\`\n- Phase branch: \`${phase.branch}\`\n\n> Execute only this claimed Bead. Do not expand scope silently. Discovered work must be created as a linked Bead using the current Bead as the discovery source. Do not merge main, deploy production, change accepted OpenSpec requirements, weaken tests, or perform undeclared destructive actions.\n\n## Objective\n\n${bead.title}\n\n## Description\n\n${bead.description}\n\n## Design\n\n${bead.design}\n\n## Acceptance criteria\n\n${bead.acceptance}\n\n${section('Allowed scope', bead.scope)}\n\n${section('Dependencies', dependencies)}\n\n## Verification contract\n\n${bead.verification}\n\n${section('Verification commands', verificationCommands)}\n\n${section('Required evidence', bead.evidence)}\n\n${section('Prohibited changes', bead.prohibitedChanges)}\n\n## Rollback\n\n${bead.rollback}\n\n## Durable notes\n\n${bead.notes || 'None.'}\n\n## Ralphy task\n\n- [ ] BEAD-${bead.id}: ${bead.title}\n`;
}
