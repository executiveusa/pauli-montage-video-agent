// Real integration proof: installed Trail, Montage source, stdio MCP, freshness
// after an edit, and ignored private data. No model/API keys or mock graph.
const assert = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const { readFileSync, writeFileSync, rmSync, mkdirSync, rmdirSync } = require('node:fs');
const { join, resolve } = require('node:path');
const { createInterface } = require('node:readline');
const { randomUUID } = require('node:crypto');
const root = resolve(__dirname, '..');
const launcher = join(root, 'scripts/trail.cjs');
function run(args, json = false) {
  const result = spawnSync(process.execPath, [launcher, ...args], { cwd: root, encoding: 'utf8', timeout: 180000, maxBuffer: 12 * 1024 * 1024 });
  assert.equal(result.status, 0, `${args[0]} failed: ${(result.stderr || result.error || '').toString().slice(-1500)}`);
  return json ? JSON.parse(result.stdout) : result.stdout;
}
function graph() { return JSON.parse(readFileSync(join(root, 'graft/.graph/wiring.json'), 'utf8')); }
async function mcpProof() {
  const config = JSON.parse(readFileSync(join(root, '.mcp.json'), 'utf8')).mcpServers['montage-code-map'];
  const child = spawn(config.command, config.args, { cwd: root, env: { ...process.env, ...config.env }, stdio: ['pipe', 'pipe', 'pipe'] });
  let id = 0; const waiting = new Map(); let stderr = '';
  child.stderr.on('data', (chunk) => { stderr = (stderr + chunk).slice(-2000); });
  const lines = createInterface({ input: child.stdout });
  lines.on('line', (line) => {
    try { const response = JSON.parse(line); const task = waiting.get(response.id);
      if (task) { clearTimeout(task.timer); waiting.delete(response.id); response.error ? task.reject(new Error(JSON.stringify(response.error))) : task.resolve(response.result); }
    } catch { for (const task of waiting.values()) task.reject(new Error('Non-protocol stdout from MCP server')); }
  });
  child.on('error', (error) => { for (const task of waiting.values()) task.reject(error); });
  child.on('exit', () => { for (const task of waiting.values()) task.reject(new Error(`MCP exited before reply: ${stderr}`)); });
  function call(method, params) { return new Promise((resolve, reject) => {
    const requestId = ++id;
    const timer = setTimeout(() => { waiting.delete(requestId); reject(new Error(`MCP ${method} timed out: ${stderr}`)); }, 60000);
    waiting.set(requestId, { resolve, reject, timer });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: requestId, method, params }) + '\n');
  }); }
  try {
    const initialized = await call('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'montage-context-acceptance', version: '1' } });
    assert.equal(initialized.serverInfo.version, '0.23.0');
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
    const listed = await call('tools/list', {});
    assert.deepEqual(listed.tools.map((tool) => tool.name).sort(), ['trail_check_freshness', 'trail_file_api', 'trail_find_all', 'trail_find_code', 'trail_repo_map', 'trail_trace_calls']);
    const api = await call('tools/call', { name: 'trail_file_api', arguments: { file: 'yappy_clipz/rendering.py' } });
    assert.notEqual(api.isError, true); assert.match(api.content[0].text, /RenderService/); assert.match(api.content[0].text, /execute/);
    const lookup = await call('tools/call', { name: 'trail_find_code', arguments: { query: 'replace_timeline', limit: 5, in: 'yappy_clipz' } });
    assert.notEqual(lookup.isError, true); assert.match(lookup.content[0].text, /service\.py/);
    console.log('PASS MCP initialize, six tools, real file API and scoped lookup');
  } finally {
    for (const task of waiting.values()) clearTimeout(task.timer);
    child.stdin.end(); child.kill('SIGTERM'); lines.close();
  }
}
async function main() {
  const nonce = randomUUID().replaceAll('-', '');
  const visible = join(root, `tests/trail_probe_${nonce}.py`);
  const privateDir = join(root, '.yappy-clipz');
  const privateFile = join(privateDir, `trail_private_${nonce}.py`);
  const symbol1 = "montage_context_probe_original", symbol2 = "montage_context_probe_revised";
  mkdirSync(privateDir, { recursive: true });
  try {
    writeFileSync(visible, `def ${symbol1}():\n    return 1\n`, { flag: 'wx' });
    writeFileSync(privateFile, `def private_${nonce}():\n    return 'PRIVATE_CONTEXT_SENTINEL_${nonce}'\n`, { flag: 'wx' });
    run(['build']);
    let indexed = graph();
    assert.ok(indexed.nodes.some((node) => node.name === symbol1));
    assert.ok(!JSON.stringify(indexed).includes(`PRIVATE_CONTEXT_SENTINEL_${nonce}`));
    assert.ok(!indexed.nodes.some((node) => node.path.startsWith('.yappy-clipz/') || node.path.includes('node_modules/')));
    assert.ok(indexed.nodes.some((node) => node.id === 'yappy_clipz/rendering.py#RenderService.execute'));
    const skeleton = run(['skeleton', 'yappy_clipz/rendering.py', '--json'], true);
    assert.ok(skeleton.entries.some((entry) => entry.name === 'execute'));
    const callers = run(['callers', 'RenderService._accept', '--json'], true);
    assert.ok(callers.matches.length > 0);
    assert.ok(callers.matches.some((match) => match.hits.some((hit) => hit.path === 'yappy_clipz/rendering.py' && hit.name === 'submit')));
    assert.ok(callers.matches.some((match) => match.hits.some((hit) => hit.path === 'yappy_clipz/rendering.py' && hit.name === 'retry')));
    console.log(`PASS structural map: ${indexed.meta?.fileCount ?? indexed.nodes.filter((node) => node.kind === 'file').length} files; render/timeline symbols; private data excluded`);
    writeFileSync(visible, `def ${symbol2}():\n    return 200\n`);
    const refreshed = run(['ask', 'montage context probe revised', '--in', `tests/trail_probe_${nonce}.py`, '--json'], true);
    assert.ok(refreshed.hits.some((hit) => hit.title.includes(symbol2)));
    indexed = graph(); assert.ok(!indexed.nodes.some((node) => node.name === symbol1));
    assert.equal(run(['build', '--check', '--json'], true).graph.ok, true);
    console.log('PASS query refresh after uncommitted source edit');
    assert.match(run(['telemetry', 'status']), /off.*DO_NOT_TRACK/);
    for (const args of [['init'], ['build', '--deep'], ['workspace', 'connect'], ['telemetry', 'enable']]) {
      assert.equal(spawnSync(process.execPath, [launcher, ...args], { cwd: root, encoding: 'utf8' }).status, 2);
    }
    await mcpProof();
  } finally {
    rmSync(visible, { force: true }); rmSync(privateFile, { force: true });
    try { rmdirSync(privateDir); } catch { /* existing local state is preserved */ }
    run(['build']);
  }
  console.log('PASS local context integration; no runtime application changes');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
