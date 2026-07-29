# Persistent Authenticated API Specification

## ADDED Requirements

### Requirement: Hosted tenant identity is authenticated
The hosted API SHALL derive tenant identity from a verified signed principal and SHALL ignore caller-provided tenant headers.

#### Scenario: A caller attempts tenant override
- **WHEN** a valid tenant-A bearer token is sent with an `X-Yappy-Tenant: tenant-B` header
- **THEN** all project access SHALL remain scoped to tenant A.

### Requirement: StudioProject persistence is replaceable and durable
The application SHALL preserve the existing repository contract and SHALL provide a PostgreSQL implementation that stores validated complete canonical StudioProject documents.

#### Scenario: The API process restarts
- **WHEN** a project is created before repository reconstruction
- **THEN** the reconstructed service SHALL reopen the same validated project from PostgreSQL.

### Requirement: Service tokens are least privilege
A principal SHALL create service tokens only with a non-empty subset of its own scopes, and revocation SHALL invalidate the token by token ID.

#### Scenario: A token requests elevated scope
- **WHEN** a project-read principal requests `budget:spend`
- **THEN** issuance SHALL fail without creating a token.

### Requirement: Hosted deployment fails closed
The hosted API SHALL not accept project traffic when signing secrets, owner credentials, or required database configuration are absent.

#### Scenario: Authentication is not configured
- **WHEN** a hosted request reaches a protected route without valid server configuration
- **THEN** the route SHALL return an authentication/configuration error and SHALL not trust tenant headers.
