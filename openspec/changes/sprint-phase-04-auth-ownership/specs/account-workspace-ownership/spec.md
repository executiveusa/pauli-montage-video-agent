## ADDED Requirements

### Requirement: Durable account and workspace ownership
The hosted service SHALL persist each registered user, owned workspace membership, and tenant-bound session across process reconstruction.

#### Scenario: User creates an account
- **WHEN** a visitor submits a valid unique email, display name, and password
- **THEN** the service creates a durable user and owner membership
- **AND** the issued session is bound to that workspace tenant

### Requirement: Cross-workspace isolation
Every authenticated project operation SHALL use the workspace tenant from the verified session rather than a caller-selected tenant.

#### Scenario: One user requests another user's project
- **WHEN** a signed user requests a project owned by a different workspace
- **THEN** the service responds as though the project does not exist
- **AND** no project document from the other workspace is disclosed

### Requirement: Non-enumerating password recovery
Password recovery SHALL use an explicitly configured delivery channel, store only a digest of a 30-minute one-use token, and return the same accepted response for known and unknown valid addresses.

#### Scenario: Recovery is requested
- **WHEN** a valid email address is submitted while delivery is configured
- **THEN** the API returns an accepted response without a recovery token
- **AND** a matching account receives a one-use recovery link through the configured channel

### Requirement: Account export and identity deletion
An authenticated user SHALL be able to export profile, membership, and canonical workspace project data without password material and delete their identity.

#### Scenario: User deletes an identity with multiple sessions
- **WHEN** the user deletes the account using one active session
- **THEN** every outstanding signed user session becomes inactive
- **AND** subsequent login with that identity fails

