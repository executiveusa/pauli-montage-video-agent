# Phase 11 Design

StudioProject and Timeline v1 remain canonical. A render job captures input refs, checksums, timeline digest, preset, exact argv, engine, warnings, and manifest digest. Preview may use warning-bearing inputs; final render requires verified checksums. Workers run argv arrays without a shell and store output through the Phase 08 asset boundary. Remotion execution is not enabled automatically.
