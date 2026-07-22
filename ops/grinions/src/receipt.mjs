export const PHASE_RECEIPT_SCHEMA_VERSION = 1;

function requiredString(value, name) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new TypeError(`phase receipt requires ${name}`);
  }
  return value.trim();
}

function optionalString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function beadReceipt(bead) {
  return {
    id: requiredString(bead?.id, 'beads[].id'),
    headSha: optionalString(bead?.integration?.headSha),
    verified: bead?.verification?.passed === true,
    closedStatus: optionalString(bead?.closed?.status),
  };
}

export function buildPhaseReceipt(phase, evidence, completedAt = new Date().toISOString()) {
  const receipt = {
    schemaVersion: PHASE_RECEIPT_SCHEMA_VERSION,
    phaseId: requiredString(phase?.phaseId, 'phaseId'),
    openspecId: requiredString(phase?.openspecId, 'openspecId'),
    risk: requiredString(phase?.risk, 'risk'),
    completedAt: requiredString(completedAt, 'completedAt'),
    baselineMainSha: requiredString(evidence?.baseline?.mainSha, 'baselineMainSha'),
    beads: (evidence?.beads || []).map(beadReceipt),
    pullRequest: {
      number: Number.isInteger(evidence?.pr?.number) ? evidence.pr.number : null,
      url: optionalString(evidence?.pr?.url),
      headSha: optionalString(evidence?.judgment?.headRefOid),
    },
    judgment: {
      passed: evidence?.judgment?.passed === true,
      unresolvedReviewThreads: Number.isInteger(evidence?.judgment?.unresolvedReviewThreads)
        ? evidence.judgment.unresolvedReviewThreads
        : null,
    },
    merge: {
      sha: requiredString(evidence?.merge?.sha, 'merge.sha'),
      mergedAt: optionalString(evidence?.merge?.mergedAt),
    },
    postMerge: {
      passed: evidence?.postMerge?.passed === true,
      mainSha: requiredString(evidence?.postMerge?.mainSha, 'postMerge.mainSha'),
    },
    rollback: {
      baselineCaptured: Boolean(evidence?.rollback),
      receiptPath: `ops/rollback/phase-${requiredString(phase?.phaseId, 'phaseId')}.json`,
    },
  };

  return validatePhaseReceipt(receipt);
}

export function validatePhaseReceipt(receipt) {
  if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)) {
    throw new TypeError('phase receipt must be an object');
  }
  if (receipt.schemaVersion !== PHASE_RECEIPT_SCHEMA_VERSION) {
    throw new TypeError(`unsupported phase receipt schemaVersion: ${receipt.schemaVersion}`);
  }
  requiredString(receipt.phaseId, 'phaseId');
  requiredString(receipt.openspecId, 'openspecId');
  requiredString(receipt.risk, 'risk');
  requiredString(receipt.completedAt, 'completedAt');
  requiredString(receipt.baselineMainSha, 'baselineMainSha');
  if (!Array.isArray(receipt.beads)) throw new TypeError('phase receipt requires beads array');
  if (receipt.judgment?.passed !== true) throw new TypeError('phase receipt requires a passed judgment');
  if (receipt.postMerge?.passed !== true) throw new TypeError('phase receipt requires passed postMerge verification');
  requiredString(receipt.merge?.sha, 'merge.sha');
  requiredString(receipt.postMerge?.mainSha, 'postMerge.mainSha');
  return receipt;
}
