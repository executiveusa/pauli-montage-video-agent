# Design: Upgrade architecture and evidence contract

## Authority precedence

1. Current `main` Git tree and canonical GitHub history establish repository reality.
2. `ops/upgrade/roadmap.json` defines initiative identity, order, titles, and immutable OpenSpec IDs.
3. The accepted OpenSpec for one Slice defines that Slice's implementation.
4. `ops/upgrade/evidence/*.json` may corroborate only completed canonical merges.
5. The generated progress page is a projection and never an input.

Existing master plans provide product context; historical Phase records describe earlier work. Neither can override this upgrade authority chain.

Because the roadmap does not exist on the pre-Slice-01 baseline, its initial hash is necessarily accepted by external review rather than self-proven by that baseline. CODEOWNERS and independent Gauntlet review are the bootstrap anchor. Once merged, validation compares roadmap bytes to fetched `origin/main`; changing a nearby constant cannot authorize redefinition.

## Completion projection

The renderer validates exactly 15 unique ordered tasks. A completion record must bind the initiative and Slice to a canonical PR number, URL, 40-character head/merge/tree/main SHAs, independent `OURS WINS` judgment, zero unresolved threads, successful post-merge commands, and rollback evidence. Invalid or duplicate evidence stops generation.

The renderer fails closed unless the canonical GitHub API confirms the PR is merged to `main`, its head and merge SHA match, its immutable GRINIONS identity marker matches, and its required GRINIONS workflow completed successfully on that head. Git independently compares the recorded PR head with the canonical remote pull-request ref and proves remote `main` matches the fetched tracking ref. GRINIONS remains the release authority; the stored record is a reviewable corroborating index.

The local projection additionally requires the recorded merge to be an ancestor of fetched `origin/main`, its tree to match the canonical remote PR head tree, its first parent to equal the rollback baseline, and the Slice's exact OpenSpec proposal to appear for the first time in that merge. `postMerge.mainSha` is proved by the canonical remote-main checks; `treeChecks` are required-check evidence bound to the exact PR head and corroborate the byte-identical squash tree without pretending the workflow ran on the squash commit. PR numbers, PR heads, and merge SHAs are globally unique across Slice evidence.

## External sources

The register is pinned to exact upstream commits. License files are evidence for the audited pin, not perpetual permission. Each implementing Slice must repeat admission checks for any actual extraction and record the destination and modifications. Missing licenses prohibit copying.

## Boundaries

- PopeBot: interaction reference only; dispatches canonical typed actions.
- Composio: scoped source authentication/tool access only.
- Owned storage: canonical media and provenance authority.
- StudioProject/StudioService: durable state and business authority.
- OmniRouter/adapters: provider isolation.
- GRINIONS/GitHub: release and completion authority.
- Ralphy: bounded executor only.
- Gauntlet: independent quality judgment only.

Ralphy 4.7.2 YAML contains only fields its parser recognizes. Runtime safety is supplied by the tested GRINIONS argument builder: one iteration, no parallel mode, branch per task, no merge, exact phase base branch, bounded retries, and explicit browser enable/disable.
