// Compile with the existing TypeScript dependency; no test-runner dependency.
const { mkdtempSync, rmSync, writeFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const { spawnSync } = require('node:child_process');
const root = resolve(__dirname, '..');
const output = mkdtempSync(join(tmpdir(), 'montage-timeline-tests-'));
try {
  const config = join(output, 'tsconfig.json');
  const compiledDir = join(output, 'compiled');
  const names = ['human-timeline-bridge', 'local-studio-store', 'hosted-review-render', 'montage-mcp', 'browser-review-plan'];
  writeFileSync(config, JSON.stringify({
    extends: join(root, 'apps/studio-web/tsconfig.json'),
    compilerOptions: { module: 'commonjs', moduleResolution: 'node', target: 'ES2022', outDir: compiledDir, noEmit: false, incremental: false, typeRoots: [join(root, 'node_modules/@types')], types: ['node'] },
    include: names.map((name) => join(root, `apps/studio-web/lib/${name}.test.ts`)),
    exclude: [],
  }));
  const compiled = spawnSync(process.execPath, [require.resolve('typescript/bin/tsc'), '--project', config], { cwd: root, stdio: 'inherit' });
  if (compiled.error) throw compiled.error;
  if (compiled.status !== 0) process.exitCode = compiled.status || 1;
  else {
    const tested = spawnSync(process.execPath, ['--test', ...names.map((name) => join(compiledDir, `${name}.test.js`))], { cwd: root, stdio: 'inherit', env: { ...process.env, NODE_PATH: join(root, 'node_modules') } });
    if (tested.error) throw tested.error;
    process.exitCode = tested.status ?? 1;
  }
} finally {
  rmSync(output, { recursive: true, force: true });
}
