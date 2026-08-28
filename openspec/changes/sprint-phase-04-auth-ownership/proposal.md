# Proposal: Sprint Phase 4 authentication and ownership

## Why

The existing hosted login represents one configured owner and cannot establish durable user/workspace ownership or prove isolation between independent accounts.

## What changes

- add durable signup, login, logout, recovery, export, and identity-deletion paths
- create explicit user, workspace, and membership records
- bind signed user sessions to one workspace tenant
- use PostgreSQL account persistence and forced project RLS in PostgreSQL mode
- protect Studio routes with the hosted session while preserving local-owner compatibility

## Impact

This adds an account persistence surface and migration. Project documents retain their existing canonical tenant identity. Recovery requires an explicit file or SMTP delivery configuration and otherwise fails closed.

