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

ALTER TABLE yappy_source_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE yappy_source_connections FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS yappy_source_connections_tenant_policy ON yappy_source_connections;
CREATE POLICY yappy_source_connections_tenant_policy ON yappy_source_connections
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Credentials are encrypted in application code before they reach PostgreSQL.
-- RLS is also forced so application bugs cannot silently cross tenant boundaries.
-- No plaintext Microsoft access or refresh token belongs in this table.
