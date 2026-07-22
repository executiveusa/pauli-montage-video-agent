# YAPPY-CLIPZ License Boundaries

This is an engineering/commercial boundary document, not legal advice. Re-check exact versions and model terms before release.

## 1. OpenMontage / canonical repository — AGPLv3

The canonical repository carries GNU AGPLv3. The license is specifically designed for network-server use and requires source availability for modified covered work used over a network.

### Product rule

Treat the OpenMontage-derived production core as an open-core boundary. Do not move proprietary customer secrets, billing rules, private tenant data, or unrelated closed-source services into the covered code merely for convenience.

### Required later work

- document source-offer/compliance behavior for network users;
- keep independently written commercial services separated through stable APIs where legally appropriate;
- obtain legal review before a closed-source SaaS launch if derivative-work boundaries are uncertain.

## 2. Twick fork — Sustainable Use License 1.0

The repository license permits use, modification, distribution, and certain commercial bundling, but explicitly states that using the software/backend as a hosted SaaS, video-editing backend, automation service, or substantial-revenue offering requires a separate commercial agreement.

### Product rule

- Private/owner/internal use: permitted subject to license conditions.
- Public YAPPY-CLIPZ SaaS: **do not ship Twick as a mandatory hosted editor/backend without commercial rights**.
- Use the fork as architecture/UX reference and as a private integration while building a YAPPY-owned Studio Editor contract.
- If commercial rights are obtained, the implementation can be swapped behind the same contract.

This corrects the earlier provisional assumption that Twick was freely usable for a hosted SaaS.

## 3. ViMax — MIT

The root `LICENSE` grants standard MIT rights including use, modification, distribution, sublicensing, and sale, with preservation of the copyright/license notice.

### Product rule

ViMax may be adapted commercially, but third-party model/API terms remain separate. Integrate its planning/continuity capabilities through an adapter rather than adopting its UI/project runtime.

## 4. VideoAgent — root MIT license; metadata consistency check required

The root `LICENSE` is MIT. Its Python project metadata has previously used inconsistent license text.

### Product rule

- Treat the root MIT license as the repository code license while recording the metadata inconsistency.
- Audit bundled/third-party models and datasets separately before commercial distribution.
- Selectively adapt capabilities; do not automatically redistribute the entire large ML stack.

## 5. LTX-2 — LTX-2 Community License Agreement

Current LTX-2 is not Apache-2.0.

Key engineering implications from the repository license:

- remote hosting/SaaS is contemplated and permitted subject to the agreement;
- use restrictions and acceptable-use conditions apply;
- attribution requirements apply to licensed-product distribution/use as specified by the agreement;
- entities meeting the stated annual-revenue threshold (USD $10M in the audited license) require a paid commercial license.

### Product rule

Place LTX-2 behind a license-aware worker adapter. OmniRouter must be able to disable it by organization/commercial eligibility without breaking the product.

Model weights/checkpoints and later releases must be re-checked independently.

## 6. ClipCannon — Business Source License 1.1

The audited license allows use/modification/self-hosting but adds a use limitation preventing the licensed work from being offered as a competing commercial `Video Production Service` to third parties until the change date/license, absent separate commercial rights.

### Product rule

- `OWNER_PRIVATE`: enabled where owner use is permitted.
- `CUSTOMER_SAAS`: disabled unless separate commercial rights are obtained or the applicable version has converted to its change license.
- Never make ClipCannon required for a customer project to open/render/export.

## 7. Open-clipz — no root license found

The repo is a private-marked Vite/React/Gemini prototype and no root `LICENSE` was found during the audit.

### Product rule

Do not copy or redistribute source based on an assumption. Behavioral/provider patterns may be independently reimplemented. Archive the prototype after feature parity.

## 8. AI YouTube Shorts Generator — README claim is not enough

The README states that the project is MIT licensed and white-label/embeddable, but no root `LICENSE` file was found during this audit.

### Product rule

Until the repository license artifact is resolved:

- do not vendor its source;
- use its public algorithm description as benchmarking/reference material;
- independently implement equivalent scoring/chunking/dedupe behavior inside the canonical Clip Factory.

## 9. Sovereign Video Agent artifact

The locally created skill is MIT and explicitly owner-controlled. It is inspired by Pexo's MIT public skills but removes dependency on Pexo hosted orchestration.

### Product rule

Use it as a behavioral specification and skill source. Fold its brief/storyboard/cost-approval/provider-direct/local-post/verification behavior into OpenMontage rather than maintaining a second backend.

## 10. Models and provider APIs

Code license never automatically grants rights to a model checkpoint, training artifact, API output, voice identity, likeness, copyrighted reference, or data source.

Every model/provider adapter must track separately:

- code/SDK license;
- model/checkpoint license;
- commercial-output rights;
- training/reference restrictions where known;
- content/use policy;
- geographic restrictions;
- attribution requirements;
- pricing/credit exposure;
- retention/privacy behavior;
- identity/voice consent requirements.

## Commercial activation policy

A capability may be enabled in customer SaaS only when its policy record evaluates `commercial_eligible=true` for the current organization, version, model, and intended use.

`OWNER-ONLY`, unclear-license, expired-rights, or threshold-restricted capabilities must fail closed and route to an eligible alternative through OmniRouter.
