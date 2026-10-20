#!/usr/bin/env node
// Repo-local, pinned Trail-Code launcher. No automatic init/global host changes.
const { existsSync, readFileSync } = require('node:fs');
const { resolve, join } = require('node:path');
const { spawn } = require('node:child_process');

const root = resolve(__dirname, '..');
const toolRoot = join(root, 'tooling', 'trail');
const packageRoot = join(toolRoot, 'node_modules', '@trailhq', 'trail-code');
const entry = join(packageRoot, 'dist', 'bin', 'trail.js');
const args = process.argv.slice(2);
const allowed = new Set(['build', 'ask', 'map', 'callers', 'skeleton', 'grep', 'mcp', 'telemetry', '--version']);
const prohibited = /^(--deep|--api-key|--provider|--model|--base-url|--dir|--lsp|--follow-submodules|--follow-nested-repos|--include-dir|--only-dir)(=|$)/;

function stop(message, code = 1) { console.error(message); process.exit(code); }
if (!allowed.has(args[0]) || args.some((arg) => prohibited.test(arg))) {
  stop('Use the local code-map commands: build, ask, map, callers, skeleton, grep, mcp, telemetry status, --version. Deep/cloud/global setup is outside this integration.', 2);
}
if (args[0] === 'telemetry' && (args.length !== 2 || args[1] !== 'status')) stop('Only telemetry status is exposed.', 2);
if (!existsSync(entry)) stop('Install the pinned tool first: npm run context:install');
const expected = JSON.parse(readFileSync(join(toolRoot, 'package.json'), 'utf8')).dependencies['@trailhq/trail-code'];
const installed = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));
if (installed.name !== '@trailhq/trail-code' || installed.version !== expected) stop('Trail version differs from the reviewed pin. Run npm run context:install.');

const env = {
  ...process.env,
  DO_NOT_TRACK: '1',
  TRAIL_HOME: join(root, 'graft', '.trail-home'),
  // Never load Montage's application/provider .env into this developer tool.
  DOTENV_CONFIG_PATH: join(toolRoot, 'disabled-env'),
  DOTENV_CONFIG_QUIET: 'true',
  GRAFT_NO_GITIGNORE: '1',
  GRAFT_NO_IGNORE: '1',
  GRAFT_NO_TRAIL_SWITCH: '1',
};
for (const key of ['GRAFT_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY', 'TRAIL_API_KEY', 'TRAIL_TOKEN']) delete env[key];
// Pin both the working directory and positional repository to this checkout,
// including when launched from a nested agent directory.
const needsRepo = !['telemetry', '--version'].includes(args[0]);
const child = spawn(process.execPath, [entry, '--dir', join(root, 'graft'), ...args, ...(needsRepo ? [root] : [])], { cwd: root, env, stdio: 'inherit', shell: false });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('error', () => stop('Could not start the local code-map process.'));
child.on('exit', (code, signal) => {
  if (signal) { process.exitCode = 1; return; }
  process.exitCode = code ?? 1;
});
