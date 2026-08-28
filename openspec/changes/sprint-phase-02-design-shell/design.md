# Design

`StudioFrame` remains the single application shell. A late-loaded `design-system.css` layer supplies tokens and accessibility overrides without destabilizing specialized timeline, footage, or generation styles. `StudioUI.tsx` owns reusable notice, loading, empty, error, and native-dialog patterns. Dashboard state is migrated first so the primitives are exercised by a production route.

Breakpoints are explicit: desktop above 1000px, tablet at or below 1000px, and compact mobile at or below 620px. All interactive shell controls retain a 44px minimum target and visible keyboard focus. Reduced-motion preferences collapse nonessential animation and transitions.
