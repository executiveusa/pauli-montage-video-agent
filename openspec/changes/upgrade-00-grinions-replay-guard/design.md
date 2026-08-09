# Design: Durable GRINIONS completion guard

## Immutable identity

Canonical work identity is:

```text
repository + initiativeId + openspecId
```

`phaseId` remains display and ordering metadata. New GRINIONS pull requests carry a machine-readable HTML comment containing the immutable identity.

## Completion classification

Before `hydrate-context`, GRINIONS fetches `origin/main`, resolves the canonical GitHub repository, and lists pull requests across open and closed states.

- `not_completed`: no matching or conflicting canonical evidence exists.
- `already_completed`: exactly one identity-matching PR is merged and its merge SHA is an ancestor of `origin/main`.
- `inconsistent`: evidence is open, closed-unmerged, duplicated, malformed, identity-mismatched, absent from `main`, receipt-only, or otherwise contradictory.

GitHub or git inspection failure raises `PHASE_COMPLETION_EVIDENCE_UNAVAILABLE`; the workflow never assumes work is incomplete when canonical evidence cannot be queried.

## Receipt role

Runner-local and repository receipts can corroborate GitHub history. They cannot independently establish completion. A receipt without a canonical matching PR is inconsistent.

Repository receipt evidence is read from fetched `origin/main`, not the worker's possibly stale checkout. A runner-local receipt may supplement it only when canonical receipt evidence is absent or byte-equivalent in parsed content; disagreement fails closed.

Uncertain-create recovery may adopt an exact open canonical PR only when no completion receipt exists. Any completion receipt paired with an open or otherwise unmerged PR is contradictory and fails closed. Canonical completion evidence itself is the final return evidence for an adopted or newly created PR and is refreshed again at the merge boundary. Merge authority is bound to that canonical PR's exact number, identity, branch, base, and head SHA in both checkpointed caller evidence and a live GitHub read; a caller-supplied or live mismatch cannot redirect the merge.

Only a PR whose head is the deterministic identity reservation branch is canonical. An identity marker copied onto any other branch is ignored as completion evidence. Corroborating receipts must contain a valid risk, verified and closed Beads, PR number and head SHA, zero unresolved review threads, merge and post-merge SHAs, and captured rollback evidence. Git must resolve the receipt's merge and post-merge SHAs, prove the merge is an ancestor of the post-merge SHA, and prove that post-merge SHA is an ancestor of current `origin/main`.

Ralphy integration accepts exactly one `ralphy/*` branch created during the bounded invocation. Its name must use the Bead-identity prefix `ralphy/bead-<exact-bead-id>`, its recorded head must descend from the captured phase head, and both refs are rechecked immediately before the single merge.

## Pre-PR safety

Immediately before the PR side effect, the workflow:

1. fetches `origin/main`;
2. proves the phase branch contains it;
3. compares the direct branch tree with `origin/main` and rejects equality with `PHASE_NO_TREE_DELTA`;
4. queries all PR states for the head branch and rejects any unexpected state;
5. repeats the all-state branch query inside PR creation to reduce time-of-check/time-of-use risk.

Identity reservation occurs only after the last canonical completion fetch is followed by a fresh ancestry/tree/head/branch-history inspection. Merge ancestry is inspected only for the deterministic canonical identity branch; copied markers on other branches are ignored before object lookup.

Same-task checkpoint restart remains valid because PR/merge side effects are checkpointed under that task, while the read-only completion classification is deliberately refreshed on every resume. Every task must reclassify against canonical evidence before hydration.

## Cross-task identity reservation

Inside the PR side effect, GRINIONS validates and serializes all local PR inputs before deriving one remote head branch from the immutable identity. It pushes the inspected immutable head SHA with an empty expected lease, which permits creation only when the remote ref does not exist, then fetches and verifies the remote ref even after a successful push. A competing descendant cannot fast-forward or otherwise replace that reservation. On rejection, GRINIONS fetches the reservation and permits only an exact-head retry; every other head fails with `PHASE_IDENTITY_RESERVATION_CONFLICT`. Same-head retries may adopt only the exact open PR whose marker, canonical head branch, base, and head SHA match.
