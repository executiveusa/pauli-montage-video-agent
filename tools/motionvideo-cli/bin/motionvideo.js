#!/usr/bin/env node
import { sendCode, verifyCode, whoami, getBookmarks, signOut, getCatalog, loadSession } from '../src/client.js';

const args = process.argv.slice(2);
const json = args.includes('--json');
const flag = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const cmd = args[0];

const out = (data, human) => {
  if (json) console.log(JSON.stringify(data, null, 2));
  else human(data);
};

function videoLine(v) {
  const parts = [v.slug, '-', v.title];
  if (v.handle) parts.push(`by @${v.handle}`);
  if (v.promptShared && v.prompt) parts.push('| prompt available');
  return parts.join(' ');
}

async function main() {
  switch (cmd) {
    case 'login': {
      const email = flag('--email');
      const code = flag('--code');
      if (!email) {
        console.error('Usage: motionvideo login --email you@example.com [--code 123456]');
        process.exit(1);
      }
      if (!code) {
        let sent = false;
        try {
          await sendCode(email);
          sent = true;
        } catch (e) {
          if (e.code !== 'MISSING_RESPONSE') throw e;
        }
        if (sent) {
          console.log(`Code sent to ${email}. Check your email, then run:`);
        } else {
          console.log(`The site only sends sign-in codes from a real browser (anti-spam check).`);
          console.log(`1. Open https://motionvideo.xyz/sign-in`);
          console.log(`2. Enter ${email} and click "Send code"`);
          console.log(`3. Check the email for the 6-digit code, then run:`);
        }
        console.log(`   motionvideo login --email ${email} --code <6-digit code>`);
        return;
      }
      const session = await verifyCode(email, code);
      out(session, (s) => {
        console.log(`Signed in as ${s.name || s.email}.`);
        console.log(`Session saved to ~/.config/motionvideo/session.json (expires ${s.expiresAt || 'in 7 days'}).`);
      });
      return;
    }
    case 'whoami': {
      const me = await whoami();
      if (!me) { console.error('Session is no longer valid. Run motionvideo login again.'); process.exit(1); }
      out(me.user, (u) => console.log(`${u.name} <${u.email}>`));
      return;
    }
    case 'bookmarks': {
      const refs = await getBookmarks();
      if (!refs.length) return out([], () => console.log('No bookmarks saved yet.'));
      const catalog = await getCatalog();
      const bySlug = new Map(catalog.videos.map((v) => [v.slug, v]));
      const items = refs.map((r) => ({ ...r, ...(r.kind === 'video' ? bySlug.get(r.id) || {} : {}) }));
      out(items, (list) => {
        for (const item of list) {
          if (item.kind === 'video' && item.title) console.log(videoLine(item));
          else console.log(`${item.kind}: ${item.id}`);
        }
      });
      return;
    }
    case 'catalog': {
      const q = flag('--search')?.toLowerCase();
      const catalog = await getCatalog();
      let videos = catalog.videos;
      if (q) {
        videos = videos.filter((v) =>
          [v.title, v.handle, v.prompt, ...(v.tags || []), ...(v.contentTags || [])]
            .filter(Boolean).join(' ').toLowerCase().includes(q));
      }
      out(videos, (list) => {
        console.log(`${list.length} videos${q ? ` matching "${q}"` : ''}:`);
        for (const v of list) console.log(videoLine(v));
      });
      return;
    }
    case 'video': {
      const slug = args[1];
      if (!slug) { console.error('Usage: motionvideo video <slug>'); process.exit(1); }
      const catalog = await getCatalog();
      const v = catalog.videos.find((x) => x.slug === slug);
      if (!v) { console.error(`No video with slug "${slug}".`); process.exit(1); }
      out(v, (video) => {
        console.log(`${video.title} (${video.slug})`);
        if (video.handle) console.log(`Creator: @${video.handle}`);
        if (video.date) console.log(`Date: ${video.date}`);
        if (video.prompt) console.log(`\nPrompt:\n${video.prompt}`);
      });
      return;
    }
    case 'logout': {
      await signOut();
      console.log('Signed out; local session deleted.');
      return;
    }
    case 'session': {
      const s = loadSession();
      if (!s) { console.log('No saved session.'); return; }
      const { cookie, ...rest } = s;
      out(rest, (r) => console.log(`Signed in as ${r.email} since ${r.createdAt}${r.expiresAt ? `, expires ${r.expiresAt}` : ''}.`));
      return;
    }
    default:
      console.log(`motionvideo - CLI for your motionvideo.xyz account

Usage:
  motionvideo login --email <email> [--code <6-digit code>]   Sign in (email code)
  motionvideo whoami                                          Show the signed-in account
  motionvideo bookmarks [--json]                              List your saved bookmarks
  motionvideo catalog [--search <term>] [--json]              Browse the public video catalog
  motionvideo video <slug> [--json]                           Show a video with its prompt
  motionvideo session                                         Show local session info
  motionvideo logout                                          Sign out and delete the local session

MCP server: run "motionvideo-mcp" and register it in your MCP client.`);
  }
}

main().catch((e) => { console.error(`Error: ${e.message}`); process.exit(1); });
