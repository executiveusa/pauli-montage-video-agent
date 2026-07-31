# Phase 10 Design

Every media request follows: validate project and references → compile prompt/workflow → route and estimate → explicit durable approval → reserve budget → create idempotent job → provider submit → status/result reconciliation → generated Asset v1 provenance → actual-cost commit. Provider-specific fields remain behind manifests and adapters. Unknown-cost requests cannot execute under a hard ceiling.
