# OpenSpec agent instructions

For every YAPPY-CLIPZ phase:

1. Treat the accepted OpenSpec change as implementation truth.
2. Do not expand scope silently; discovered work becomes a linked Bead and, when required, a new OpenSpec change.
3. Keep one phase per final PR.
4. Validate changes with `openspec validate <change> --strict --no-interactive` before merge.
5. Archive completed changes after post-merge verification.
6. Do not weaken acceptance criteria to make implementation pass.
