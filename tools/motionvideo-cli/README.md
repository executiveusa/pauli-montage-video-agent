# motionvideo-cli

CLI and MCP server for your motionvideo.xyz account: read your bookmarks and the
public motion catalog (every video with its prompt, model, and media URLs).

Zero dependencies. Node 18+.

## Install

```sh
cd motionvideo-cli
npm link        # puts `motionvideo` and `motionvideo-mcp` on your PATH
# or run directly: node bin/motionvideo.js ...
```

## Sign in

MotionVideo signs in with a 6-digit email code. Sending the code is protected
by an anti-spam browser check (Cloudflare Turnstile), so the send step happens
in a real browser; the CLI does the rest over plain HTTP.

1. Open https://motionvideo.xyz/sign-in
2. Enter your email, click "Send code"
3. Check your email for the 6-digit code, then:

```sh
motionvideo login --email you@example.com --code 123456
```

The session cookie is stored in `~/.config/motionvideo/session.json`
(mode 600) and lasts 7 days. Run `motionvideo session` to check expiry,
`motionvideo logout` to revoke and delete it.

## Commands

```
motionvideo login --email <email> [--code <code>]   Sign in
motionvideo whoami                                  Show the signed-in account
motionvideo bookmarks [--json]                      List your saved bookmarks
motionvideo catalog [--search <term>] [--json]      Browse the public catalog
motionvideo video <slug> [--json]                   One video with its full prompt
motionvideo session                                 Local session info
motionvideo logout                                  Sign out, delete local session
```

## MCP server

`motionvideo-mcp` speaks MCP over stdio. Register it in your MCP client:

```json
{
  "mcpServers": {
    "motionvideo": {
      "command": "motionvideo-mcp"
    }
  }
}
```

Tools: `motionvideo_whoami`, `motionvideo_list_bookmarks`,
`motionvideo_catalog` (optional `search`), `motionvideo_get_video` (`slug`).

## Notes

- Read-only. Nothing here can buy the skill pack, submit work, or change the
  account; there is no write path in the tool.
- The catalog endpoints (`/api/catalog`, `/api/catalog/directories`) are the
  site's own public JSON for "MCP servers, scripts, and other integrations".
- Bookmarks come from the same session-cookie server function the dashboard
  uses; there is no official per-user API token. If the site ships a new build,
  the bookmark function id may change and `motionvideo bookmarks` will need the
  new id (see `SERVER_FN` in `src/client.js`).
