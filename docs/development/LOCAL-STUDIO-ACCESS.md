# Local studio access

`/studio` is a public UI shell. Visitors can create browser-local projects,
import footage, edit and save without an account. A missing hosted session
(`authentication_required`) uses the existing local project creation path.
The sidebar offers Hosted sign-in for server projects.

The API boundary is unchanged: `studio-proxy.ts` requires a signed hosted
session for project requests and media transfers. Public HTML contains no
hosted project data. Local project IDs only read this browser's local store.
A private project URL alone does not authorize a read or render.

Rollback: revert this change to restore the page-level sign-in gate.
