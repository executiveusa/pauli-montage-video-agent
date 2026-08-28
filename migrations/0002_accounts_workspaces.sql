BEGIN;

CREATE TABLE IF NOT EXISTS yappy_users (
    user_id text PRIMARY KEY,
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    profile jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);

CREATE TABLE IF NOT EXISTS yappy_workspaces (
    workspace_id text PRIMARY KEY,
    tenant_id text NOT NULL UNIQUE,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS yappy_workspace_memberships (
    workspace_id text NOT NULL REFERENCES yappy_workspaces(workspace_id) ON DELETE CASCADE,
    user_id text NOT NULL REFERENCES yappy_users(user_id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS yappy_password_recovery (
    token_hash text PRIMARY KEY,
    user_id text NOT NULL REFERENCES yappy_users(user_id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS yappy_memberships_user_idx ON yappy_workspace_memberships(user_id);
CREATE INDEX IF NOT EXISTS yappy_recovery_expiry_idx ON yappy_password_recovery(expires_at);

ALTER TABLE yappy_studio_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE yappy_studio_projects FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS yappy_projects_tenant_policy ON yappy_studio_projects;
CREATE POLICY yappy_projects_tenant_policy ON yappy_studio_projects
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
