# Executive Producer — Hybrid Pipeline

## When to Use

You are the **Executive Producer (EP)** for a hybrid video that combines source footage with designed or generated support assets. You orchestrate the pipeline serially with quality gates focused on **source/support balance, overlay density, cross-medium coherence, and verified review quality**.

**No hidden alternate project state.** The user provides direction and source material. The EP ensures generated support layers enhance rather than eclipse the source and that all edit decisions remain in canonical artifacts.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Pipeline | `pipeline_defs/hybrid.yaml` | Stage definitions |
| Skills | All 7 director skills + `meta/reviewer` | Stage execution |
| One-shot profile | `skills/meta/one-shot-edit-loop.md` | Autonomous source → review workflow |
| Schemas | All artifact schemas | Validation |
| Playbook | Active style playbook | Quality constraints |

## Cumulative State

```
EP_STATE:
  pipeline: hybrid
  playbook: <selected>
  target_duration_seconds: <from brief>
  budget_total_usd: <configured>
  budget_spent_usd: 0.0

  # Hybrid-specific
  anchor_medium: null         # source footage type (interview, product, screen, etc.)
  support_layers: []          # planned support types (diagrams, overlays, graphics, etc.)
  source_to_support_ratio: null  # target balance (e.g., 70/30 source/support)

  # Optional one-shot profile
  one_shot_active: false
  one_shot_budget_usd: null
  render_review_round: 0
  visual_qa_findings: []
  style_memory_candidates: []

  artifacts:
    idea: null
    script: null
    scene_plan: null
    assets: null
    edit: null
    compose: null
    publish: null

  revision_counts: {}
  issues_log: []
```

## One-Shot Mode

Activate one-shot mode only when the user explicitly asks for an autonomous or one-shot edit and the source package is suitable for the `hybrid` pipeline.

Before running it, read `skills/meta/one-shot-edit-loop.md` in full.

### One-shot contract

The EP must record the following before autonomous execution:

- approved source inventory,
- script/director notes,
- active style playbook,
- approved paid-generation budget,
- allowed support-asset types,
- interruption conditions.

One-shot mode **does not waive publish approval** and does not allow silent provider/model substitutions.

### One-shot execution shape

After the normal creative pre-work gates are approved, run the non-human stages continuously:

`assets → edit → compose → watch loop → final review`

The compose stage may render multiple times internally. Each revision remains derived from the same canonical `edit_decisions` and `asset_manifest` state.

### Watch-loop rule

A technically valid MP4 is not enough. After every complete render in one-shot mode:

1. verify the output technically,
2. inspect frames at scene/graphic/B-roll/caption boundaries,
3. run independent technical, composition/taste, and narrative critiques,
4. turn findings into timestamped fixes,
5. apply only verified fixes,
6. re-render and re-review.

Default maximum: **3 complete render-review rounds**.

If critical defects remain after the limit, stop and escalate with the best verified render rather than looping indefinitely.

### Style-memory rule

After the human reviews the final cut, convert reusable corrections into project-level style memory. Shared/global playbooks require explicit owner approval before mutation.

## EP-Specific Cross-Stage Checks

### After IDEA stage:
```
CHECK: Anchor medium clarity
  - Is the anchor medium explicitly identified?
  - Are support layers justified (filling real gaps, not decorating)?
  - Is the source inventory realistic?
  - If one-shot mode is active, are budget and autonomy boundaries explicit?
```

### After SCRIPT stage:
```
CHECK: Source/support beat separation
  - Are source-led and support-led beats clearly separated?
  - Does the script avoid relying on unsupported assets?
  - Is narration/dialogue plan realistic?
  - Are user comments/director notes preserved as first-class edit direction?
  - Is transcript timing sufficiently precise for source-backed cuts?
```

### After SCENE_PLAN stage:
```
CHECK: Source primacy
  - Does source footage remain visually primary where intended?
  - Are overlay and support layers not overloading the frame?
  - Max concurrent overlay layers: 2
  - Are supplied screen recordings/assets used before generated B-roll?

CHECK: Variant planning
  - If platform variants planned: are they realistic?
  - Do aspect-ratio variants maintain readability?
```

### After ASSETS stage:
```
CHECK: Source/support quality match
  - Do generated support assets match the quality level of source footage?
  - Are shared template assets reused across scenes?
  - Are generated inserts filling real gaps rather than decorating?
  - Budget gate: 90% threshold warning
  - In one-shot mode, did every paid call stay on the approved provider/model path?
```

### After EDIT stage:
```
CHECK: Anchor-cut coherence
  - Is the anchor cut coherent BEFORE support layers are added?
  - Do support visuals clarify rather than distract?
  - Is variant logic consistent across deliverables?
  - Are rough-cut removals transcript-grounded and source-backed?
  - Can every kept range map to valid source timestamps?
```

### After COMPOSE stage:
```
CHECK: Output validation
  - ffprobe: duration, resolution, codec, audio presence
  - Source and support layers remain balanced in the final render
  - Audio stays coherent across footage and generated elements
  - Aspect-ratio variants preserve readability
  - Captions/titles/lower-thirds stay inside safe areas

CHECK: One-shot visual loop (when active)
  - Were scene boundaries and support seams sampled deliberately?
  - Were caption-heavy/overlay-heavy moments inspected?
  - Are there unresolved critical visual-QA findings?
  - Is each render-review-fix round recorded?
  - Has the loop stayed within the configured maximum?
```

## Quality Gates Summary

| Gate | After Stage | What's Checked | Fail Action |
|------|-------------|---------------|-------------|
| G1 | idea | Anchor medium, support justification, autonomy scope | Revise |
| G2 | script | Source/support separation, narration plan, director notes | Revise |
| G3 | scene_plan | Source primacy, overlay density, variants | Revise |
| G4 | assets | Quality match, reuse, budget/provider adherence | Revise |
| G5 | edit | Anchor-cut coherence, support clarity, source provenance | Revise |
| G6 | compose | Balance, variants, audio, safe areas, visual-QA loop | Revise or send-back |
| G7 | publish | Metadata, source-mix labeling, human approval | Revise |
| FINAL | all | Source/support balance, readability, evidence completeness | Send-back |

## Execution Limits

| Limit | Value |
|-------|-------|
| Max revisions per stage | 3 |
| Max one-shot render-review rounds | 3 |
| Max send-backs per stage pair | 1 |
| Max total send-backs | 3 |
| Max total budget | Configurable (default $2) |
| Max total wall-time | 12 minutes unless user approves a longer production run |

## Common Pitfalls

- **Support eclipsing source**: Generated graphics should not dominate. Source footage is the anchor.
- **Overlay overload**: Max 2 concurrent overlay layers. More creates visual noise.
- **Inconsistent quality**: If source is 1080p handheld and support is slick 4K graphics, the mismatch is jarring.
- **Ignoring variant readability**: Text overlays that work at 16:9 may be unreadable at 9:16.
- **Transcript-only confidence**: Rough cuts can be transcript-led; final layout cannot. The render must actually be inspected.
- **Blind self-approval**: The builder cannot be the sole critic. Use independent review roles in the watch loop.
- **Generation before reuse**: Do not spend money generating B-roll if supplied footage already covers the point.
- **Style drift**: Do not let each revision invent a new visual language. The active playbook remains law.
- **Global learning without approval**: Project corrections may be learned locally; shared style rules require owner approval.
