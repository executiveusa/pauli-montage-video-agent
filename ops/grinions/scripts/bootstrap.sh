#!/usr/bin/env bash
set -euo pipefail

if ! command -v bd >/dev/null 2>&1; then
  echo "ERROR: Beads CLI 'bd' is required. Install from the official beads project." >&2
  exit 1
fi

if [ ! -d .beads ]; then
  bd init --quiet
fi

if ! command -v ralphy >/dev/null 2>&1; then
  echo "ERROR: Ralphy CLI is required. Install ralphy-cli or set RALPHY_BIN." >&2
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

npm install --prefix ops/grinions
npm test --prefix ops/grinions
node ops/grinions/scripts/verify.mjs

echo "GRINIONS control-plane bootstrap passed."
