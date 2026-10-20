// Zero-dependency MCP server (stdio, JSON-RPC 2.0) for motionvideo.xyz.
// Implements the subset clients use: initialize, tools/list, tools/call, ping.
import readline from 'node:readline';
import { whoami, getBookmarks, getCatalog, loadSession } from './client.js';

const TOOLS = [
  {
    name: 'motionvideo_whoami',
    description: 'Show which motionvideo.xyz account the saved session belongs to.',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'motionvideo_list_bookmarks',
    description: "List the signed-in user's saved bookmarks (videos, tools, creatives, skills, extras). Video bookmarks are joined with catalog details (title, creator, prompt).",
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'motionvideo_catalog',
    description: 'Browse the public MotionVideo catalog: every gallery video with its prompt, model, stack, and media URLs. Optionally filter by a search term.',
    inputSchema: {
      type: 'object',
      properties: { search: { type: 'string', description: 'Optional search term matched against title, creator, prompt and tags.' } },
    },
  },
  {
    name: 'motionvideo_get_video',
    description: 'Get one catalog video by slug, including its full prompt and media URLs.',
    inputSchema: {
      type: 'object',
      properties: { slug: { type: 'string', description: 'Video slug, e.g. "jacksonfall-54b2ac".' } },
      required: ['slug'],
    },
  },
];

const PROTOCOL_VERSION = '2024-11-05';

function result(id, value) {
  return JSON.stringify({ jsonrpc: '2.0', id, result: value });
}
function error(id, code, message) {
  return JSON.stringify({ jsonrpc: '2.0', id, error: { code, message } });
}
function toolText(value) {
  return { content: [{ type: 'text', text: typeof value === 'string' ? value : JSON.stringify(value, null, 2) }] };
}

async function callTool(name, args = {}) {
  switch (name) {
    case 'motionvideo_whoami': {
      const me = await whoami();
      if (!me) return toolText('No valid saved session. Run: motionvideo login --email <email>');
      return toolText(me.user);
    }
    case 'motionvideo_list_bookmarks': {
      const refs = await getBookmarks();
      if (!refs.length) return toolText('No bookmarks saved yet.');
      const catalog = await getCatalog();
      const bySlug = new Map(catalog.videos.map((v) => [v.slug, v]));
      return toolText(refs.map((r) => ({ ...r, ...(r.kind === 'video' ? bySlug.get(r.id) || {} : {}) })));
    }
    case 'motionvideo_catalog': {
      const catalog = await getCatalog();
      const q = (args.search || '').toLowerCase();
      const videos = q
        ? catalog.videos.filter((v) =>
            [v.title, v.handle, v.prompt, ...(v.tags || []), ...(v.contentTags || [])]
              .filter(Boolean).join(' ').toLowerCase().includes(q))
        : catalog.videos;
      return toolText({ count: videos.length, videos });
    }
    case 'motionvideo_get_video': {
      const catalog = await getCatalog();
      const v = catalog.videos.find((x) => x.slug === args.slug);
      return toolText(v || `No video with slug "${args.slug}".`);
    }
    default:
      throw Object.assign(new Error(`unknown tool ${name}`), { code: -32602 });
  }
}

async function handle(msg) {
  const { id, method, params } = msg;
  switch (method) {
    case 'initialize':
      return result(id, {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: { tools: {} },
        serverInfo: { name: 'motionvideo', version: '0.1.0' },
      });
    case 'ping':
      return result(id, {});
    case 'tools/list':
      return result(id, { tools: TOOLS });
    case 'tools/call':
      try {
        const value = await callTool(params?.name, params?.arguments);
        return result(id, value);
      } catch (e) {
        return result(id, { content: [{ type: 'text', text: `Error: ${e.message}` }], isError: true });
      }
    case 'notifications/initialized':
    case 'notifications/cancelled':
      return null; // notifications need no response
    default:
      return id !== undefined ? error(id, -32601, `method not found: ${method}`) : null;
  }
}

const rl = readline.createInterface({ input: process.stdin });
rl.on('line', async (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;
  let msg;
  try { msg = JSON.parse(trimmed); } catch { return; }
  try {
    const response = await handle(msg);
    if (response) process.stdout.write(response + '\n');
  } catch (e) {
    if (msg.id !== undefined) process.stdout.write(error(msg.id, -32603, e.message) + '\n');
  }
});

if (!loadSession()) {
  console.error('[motionvideo-mcp] warning: no saved session; run "motionvideo login" first (bookmarks/whoami will fail until then)');
}
