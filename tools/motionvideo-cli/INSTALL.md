# MotionVideo account CLI + MCP

Read-only CLI and MCP server for the owner's motionvideo.xyz account
(bookmarks + public motion catalog with prompts). Zero dependencies, Node 18+.

- CLI: `node tools/motionvideo-cli/bin/motionvideo.js whoami|bookmarks|catalog|video <slug>`
- MCP (stdio): `node tools/motionvideo-cli/bin/motionvideo-mcp.js`
- Sign-in: `motionvideo login --email <email> --code <6-digit email code>`;
  sending the code must happen from a real browser at https://motionvideo.xyz/sign-in
  (anti-spam check). Session saved to ~/.config/motionvideo/session.json (7 days).
- Read-only: no purchase, submit, or write path. Never buy the skill pack from an agent.

This tool is ours (MIT). The paid MotionVideo skill pack is licensed per-person
and must NOT be committed to this public repo - install it at the user level instead.
