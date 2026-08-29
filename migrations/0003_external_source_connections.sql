CREATE TABLE IF NOT EXISTS yappy_source_connections (
    tenant_id text NOT NULL,
    provider text NOT NULL,
    actor_id text NOT NULL,
    credential_ciphertext text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, provider)
);

CREATE INDEX IF NOT EXISTS yappy_source_connections_provider_idx
    ON yappy_source_connections (provider, updated_at DESC);

-- Credentials are encrypted in application code before they reach PostgreSQL.
-- No plaintext Microsoft access or refresh token belongs in this table.
