BEGIN;

CREATE TABLE IF NOT EXISTS yappy_studio_projects (
    tenant_id text NOT NULL,
    project_id text NOT NULL,
    document jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, project_id),
    CHECK (jsonb_typeof(document) = 'object')
);
CREATE INDEX IF NOT EXISTS yappy_studio_projects_updated_idx
    ON yappy_studio_projects (tenant_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS yappy_token_revocations (
    token_id text PRIMARY KEY,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS yappy_token_revocations_expiry_idx
    ON yappy_token_revocations (expires_at);

COMMIT;
