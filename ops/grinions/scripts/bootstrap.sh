#!/usr/bin/env bash
set -euo pipefail

if ! command -v bd >/dev/null 2>&1; then
  echo "ERROR: Beads CLI 'bd' is required. Install from the official beads project." >&2
  exit 1
fi

if [ ! -d .beads ]; then
  bd init --quiet
fi

RALPHY_CMD="${RALPHY_BIN:-ralphy}"
if ! command -v "$RALPHY_CMD" >/dev/null 2>&1 && [ ! -x "$RALPHY_CMD" ]; then
  echo "ERROR: Ralphy CLI is required. Install ralphy-cli or set RALPHY_BIN to an executable path." >&2
  exit 1
fi

: "${ABSURD_DATABASE_URL:?Set ABSURD_DATABASE_URL to the dedicated GRINIONS Postgres database}"

if command -v absurdctl >/dev/null 2>&1; then
  absurdctl init -d "$ABSURD_DATABASE_URL"
  absurdctl create-queue -d "$ABSURD_DATABASE_URL" grinions || true
else
  echo "ERROR: absurdctl is required to initialize the durable control-plane schema." >&2
  exit 1
fi

export RALPHY_BIN="$RALPHY_CMD"
npm install --prefix ops/grinions
npm test --prefix ops/grinions
node ops/grinions/scripts/verify.mjs

echo "GRINIONS control-plane bootstrap passed."
