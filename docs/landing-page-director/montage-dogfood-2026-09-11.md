# Montage Landing Page Director Dogfood — 2026-09-11

## PROJECT LOCK

- **Mode:** BROWNFIELD
- **Product:** Montage — AI-assisted, source-first video editing and storytelling system
- **Audience:** creators, small teams, nonprofits, documentary/story-driven operators, and marketers with substantial real footage who need to find moments and turn them into finished versions
- **Awareness stage:** problem-aware / solution-aware; visitors know editing is slow and fragmented but may not know Montage
- **Visitor trigger:** hours of footage, too much timeline scrubbing, scattered tools, pressure to produce multiple finished formats
- **Problem:** finding the useful moments and carrying them through a trustworthy edit is slower and more fragmented than it should be
- **Desired outcome:** understand the product immediately, believe the protected-source workflow is real, and request beta access
- **Offer:** private beta access to Montage
- **Commercial value:** qualified beta demand, product validation, future paid conversion, evidence for broader launch
- **Primary CTA:** Request beta access
- **Post-click result:** valid waitlist submission followed by `/thanks`
- **Existing proof:** searchable/transcribed footage architecture; Google Drive + OneDrive + local sources; protected source masters; canonical reversible editing state; deterministic/verified rendering; local Sage reasoning path
- **Primary objections:** "Is this another AI generator?"; "Will it overwrite source footage?"; "Is it real or a concept?"; "Can I use my existing footage/storage?"; "Can I retain creative control?"
- **Brand assets to preserve:** Montage name and mark; cinematic multi-source visual system; "Many moments. One story."; editorial serif + restrained interface language; paper/ink/slate/signal palette
- **Technical constraints:** existing Next.js Studio app; do not break editor/runtime routes, authentication, forms, SEO, or cloud-source architecture
- **Things that must not change:** source-master protection, owner control, current application architecture, existing working product routes
- **Primary KPI:** successful qualified beta access requests
- **Definition of success:** two-second comprehension + one clear CTA + credible product proof + verified mobile behavior + working Netlify form + production smoke test

## BASELINE / INSPECTION

Current public hero leads with the brand name, pronunciation, and dictionary definition before the concrete product promise. The current primary CTA is "Join the private beta." The underlying page contains stronger product truth than the hero exposes: searchable scenes/transcripts, protected masters, reversible editing, Google Drive/OneDrive/local sources, local Sage reasoning, and verified rendering.

Netlify project `montage-beta` exists and Forms is enabled, but Netlify currently reports zero detected forms. The repository already includes a hidden static form definition at `apps/studio-web/public/waitlist.html`, so the next production proof step is exact-deploy verification rather than duplicating form markup.

Current canonical baseline when this dogfood branch was created: `d691ddfa9099c6dbcbfafd55a9c263562564f2cf`.

## CLAIMS / EVIDENCE LEDGER

| Claim | Status | Public use |
| --- | --- | --- |
| Montage works with real source footage | VERIFIED in repository architecture and prior runtime evidence | Yes |
| Google Drive and OneDrive are supported source paths | VERIFIED | Yes, with private-beta qualification |
| Source masters are protected / editing uses derivatives | VERIFIED architecture contract | Yes |
| Footage can be searched through transcript/scene evidence | VERIFIED architecture | Yes |
| Editing is reversible through canonical timeline state | VERIFIED architecture/runtime evidence | Yes |
| Exports can be verified before completion | VERIFIED runtime architecture | Yes |
| Full hosted SaaS runtime is universally production-ready | NOT VERIFIED | No |
| Beta access is open to everyone immediately | NOT VERIFIED | No |
| Specific time-savings percentage | MISSING PROOF | No |
| Customer/user counts or logos | MISSING PROOF | No |

## REFERENCE LEDGER

### Descript
- **Useful principle:** category clarity and immediate direct action; explains a differentiated editing mechanic instead of leading with brand mythology
- **Do not copy:** text-based-editor visual expression or copy
- **Application:** Montage must state what kind of editor it is and expose the mechanism immediately

### OpusClip
- **Useful principle:** concrete input → output promise with a value-oriented CTA
- **Do not copy:** viral-clips positioning or creator-count social proof
- **Application:** make the desired visitor outcome concrete, but keep Montage broader and source-first

### Adobe Premiere / Media Intelligence
- **Useful principle:** "find footage by describing it" is a clear, high-value editing mechanic
- **Do not copy:** Adobe visual system, feature density, or professional-suite framing
- **Application:** make searchable speech + visual scenes a central proof point

### Montage current brand system
- **Useful principle:** multi-image composition directly expresses "many moments → one story"
- **Preserve:** cinematic source collage and editorial identity
- **Repair:** information hierarchy and CTA language

## CONVERSION CONTRACT

**VISITOR → UNDERSTANDS → BELIEVES → ACTS → CONFIRMATION**

- **Understands:** Montage is an AI-assisted video editor for people with real footage; it helps find moments and turn them into finished stories.
- **Believes:** the page demonstrates searchable scenes/transcripts, protected masters, reversible edit state, real sources, and verified outputs.
- **Acts:** Request beta access.
- **Confirmation:** `/thanks` confirms successful submission and explains what happens next.

## TWO-SECOND MESSAGE

**Category:** AI-assisted video editor for real footage.

**Promise:** Turn hours of raw footage into one finished story.

**Mechanism:** Search what was said and seen, build selects, edit reversibly, and export verified versions without touching source masters.

**Action:** Request beta access.

## CREATIVE TERRITORIES

### A — Cut Room / restrained
A split editorial composition: product interface proof dominates, with quiet monochrome typography and source/proxy/export evidence. Strongest clarity, but risks discarding the existing memorable Montage collage.

### B — Many Moments / expressive — CHOSEN
Preserve the five-scene cinematic collage and editorial identity, but remove dictionary-first hierarchy. Brand name remains large; concrete product promise appears immediately beneath it; proof mechanics and a single beta-access CTA are visible in the first screen. Best balance of originality, preservation, clarity, and blast radius.

### C — Assembly Timeline / experimental
Animate separated source frames into a single composited timeline/output frame as the user scrolls. Strong concept, but higher accessibility/performance risk and unnecessary for the first proven slice.

## DESIGN LOCK

### Creative
- **Chosen territory:** B — Many Moments / expressive
- **Governing idea:** separate real moments become one coherent story
- **Emotional tone:** cinematic, editorial, calm, competent
- **Signature behavior:** source frames remain the hero visual; motion suggests assembly rather than generic AI magic

### Content
- **Hero hierarchy:** category/private-beta kicker → Montage brand → concrete outcome headline → mechanism/proof sentence → primary CTA → supporting editorial brand definition
- **Primary promise:** Turn hours of raw footage into one finished story.
- **Supporting explanation:** Search what was said and seen. Build selects, edit reversibly, and export verified versions while source masters stay protected.
- **Product proof:** protected source workflow; searchable scenes/transcripts; reversible timeline; verified outputs
- **Trust sequence:** real product path → objections/FAQ → beta request
- **CTA wording:** Request beta access
- **Confirmation state:** existing `/thanks`, verified in production before release

### Visual system
- Preserve current collage, mark, palette, serif display, and restrained UI type.
- Replace dictionary-first block with a product-first hierarchy.
- Keep motion restrained and reduced-motion compatible.
- Do not introduce gradients, glass-card systems, bento grids, fake dashboard mockups, or decorative AI visuals.

### Mobile contract
- Category + brand + outcome visible without requiring scroll decoding.
- CTA full-width when appropriate.
- No hover dependency.
- Source collage may reduce visible panels on small screens, but the governing idea must survive.
- Avoid giant brand type crowding the promise.
- Workflow rail may stack; primary CTA remains visually dominant.

### Quality / hard gates
- Two-second test PASS
- One primary conversion PASS
- CTA functional
- Success state functional
- Unsupported claims 0
- P0 0 / P1 0
- Mobile overflow 0
- Critical accessibility failures 0
- Slop/taste review PASS
- Production/mobile evidence PASS
- Rollback documented

## ROLLBACK

Restore canonical `main` baseline or revert the isolated dogfood PR/squash commit. No source media, database data, provider credentials, or editor state should be mutated by this landing-page slice.
