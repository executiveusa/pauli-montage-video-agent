import { validatePhaseReceipt } from './receipt.mjs';

const IDENTITY_PREFIX = 'grinions-work-identity:';

function required(value, name) {
  if (typeof value !== 'string' || !value.trim()) throw new TypeError(`work identity requires ${name}`);
  return value.trim();
}

export function workIdentity({ repository, initiativeId, openspecId }) {
  return {
    repository: required(repository, 'repository').toLowerCase(),
    initiativeId: required(initiativeId, 'initiativeId'),
    openspecId: required(openspecId, 'openspecId'),
  };
}

export function workIdentityMarker(identity) {
  return `<!-- ${IDENTITY_PREFIX} ${JSON.stringify(workIdentity(identity))} -->`;
}

export function parseWorkIdentity(body) {
  if (typeof body !== 'string') return null;
  const match = body.match(/<!--\s*grinions-work-identity:\s*(\{[^\n]*\})\s*-->/);
  if (!match) return null;
  try {
    return workIdentity(JSON.parse(match[1]));
  } catch {
    return { malformed: true };
  }
}

export function sameWorkIdentity(left, right) {
  return left?.repository === right.repository
    && left?.initiativeId === right.initiativeId
    && left?.openspecId === right.openspecId;
}

function inconsistent(reason, evidence = {}) {
  return { status: 'inconsistent', reason, ...evidence };
}

export function classifyCompletionEvidence({
  identity,
  branch,
  canonicalBranch = branch,
  pullRequests,
  receipt = null,
  receiptGitEvidence = null,
}) {
  const requestedPhaseId = identity?.phaseId;
  const requested = workIdentity(identity);
  if (!Array.isArray(pullRequests)) return inconsistent('pull_request_history_not_array');

  const enriched = pullRequests.map((pr) => ({ ...pr, workIdentity: parseWorkIdentity(pr.body) }));
  const relevantBranches = new Set([branch, canonicalBranch].filter(Boolean));
  const malformed = enriched.filter((pr) => relevantBranches.has(pr.headRefName) && pr.workIdentity?.malformed);
  if (malformed.length) return inconsistent('malformed_work_identity', { pullRequests: malformed });

  const exact = enriched.filter((pr) => (
    pr.headRefName === canonicalBranch && sameWorkIdentity(pr.workIdentity, requested)
  ));
  const branchConflicts = enriched.filter((pr) => (
    relevantBranches.has(pr.headRefName) && !sameWorkIdentity(pr.workIdentity, requested)
  ));
  const identityConflicts = enriched.filter((pr) => (
    relevantBranches.has(pr.headRefName)
    &&
    pr.workIdentity
    && pr.workIdentity.initiativeId === requested.initiativeId
    && pr.workIdentity.openspecId === requested.openspecId
    && pr.workIdentity.repository !== requested.repository
  ));

  if (branchConflicts.length || identityConflicts.length) {
    return inconsistent('conflicting_pull_request_identity', {
      pullRequests: [...branchConflicts, ...identityConflicts],
    });
  }
  if (exact.length > 1) return inconsistent('ambiguous_completion_history', { pullRequests: exact });

  if (receipt) {
    try {
      validatePhaseReceipt(receipt);
    } catch (error) {
      return inconsistent('receipt_invalid', { receipt, receiptError: error.message });
    }
    if (requestedPhaseId !== undefined && receipt.phaseId !== requestedPhaseId) {
      return inconsistent('receipt_phase_mismatch', { receipt });
    }
    if (receipt.openspecId !== requested.openspecId) {
      return inconsistent('receipt_identity_mismatch', { receipt });
    }
    if (!exact.length) return inconsistent('receipt_without_canonical_pull_request', { receipt });
    const [matchingPr] = exact;
    if (Number.isInteger(receipt.pullRequest?.number) && receipt.pullRequest.number !== matchingPr.number) {
      return inconsistent('receipt_pull_request_mismatch', { receipt, pullRequests: exact });
    }
    if (receipt.pullRequest.headSha !== matchingPr.headRefOid) {
      return inconsistent('receipt_head_sha_mismatch', { receipt, pullRequests: exact });
    }
    if (receipt.merge?.sha && matchingPr.mergeCommit?.oid && receipt.merge.sha !== matchingPr.mergeCommit.oid) {
      return inconsistent('receipt_merge_sha_mismatch', { receipt, pullRequests: exact });
    }
    if (!receiptGitEvidence?.postMergeShaValid) {
      return inconsistent('receipt_post_merge_sha_invalid', { receipt });
    }
    if (receiptGitEvidence.mergeIntegratedAtPostMerge !== true) {
      return inconsistent('receipt_post_merge_does_not_contain_merge', { receipt });
    }
    if (receiptGitEvidence.postMergeIntegratedIntoMain !== true) {
      return inconsistent('receipt_post_merge_not_integrated_into_main', { receipt });
    }
  }

  if (!exact.length) return { status: 'not_completed', identity: requested };

  const [pr] = exact;
  if (!pr.mergedAt) {
    if (receipt) {
      return inconsistent('receipt_with_unmerged_pull_request', { receipt, pullRequest: pr, pullRequests: exact });
    }
    return inconsistent(pr.state === 'OPEN' ? 'matching_pull_request_open' : 'matching_pull_request_not_merged', {
      pullRequest: pr,
      pullRequests: exact,
    });
  }
  if (!pr.mergeCommit?.oid) return inconsistent('matching_pull_request_missing_merge_sha', { pullRequests: exact });
  if (pr.integratedIntoMain !== true) {
    return inconsistent('merge_not_integrated_into_main', { pullRequests: exact });
  }

  return {
    status: 'already_completed',
    identity: requested,
    pullRequest: pr,
    mergeSha: pr.mergeCommit.oid,
  };
}
