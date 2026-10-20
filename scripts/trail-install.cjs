#!/usr/bin/env node
const { spawn } = require('node:child_process');
const { resolve } = require('node:path');
const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const child = spawn(npm, ['ci', '--prefix', resolve(__dirname, '../tooling/trail'), '--ignore-scripts', '--no-fund'], {
  env: { ...process.env, DO_NOT_TRACK: '1' }, stdio: 'inherit', shell: process.platform === 'win32',
});
child.on('error', () => { console.error('npm could not install the pinned code-map tool.'); process.exitCode = 1; });
child.on('exit', (code) => { process.exitCode = code ?? 1; });
