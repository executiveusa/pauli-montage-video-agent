// Minimal decoder for the seroval JSON envelope TanStack Start server
// functions return. Handles the tags motionvideo.xyz actually emits:
// 1 string, 2 constant (s:1 = undefined, s:2 = null), 9 array, 10/11 object,
// plus plain numbers. Unknown tags throw so we notice format changes.
export function decodeSeroval(node) {
  if (node == null || typeof node !== 'object') return node;
  switch (node.t) {
    case 0: return node.s;            // number (serialized as string)
    case 1: return node.s;            // string
    case 2: return node.s === 2 ? null : undefined; // constants
    case 9: return (node.a || []).map(decodeSeroval); // array
    case 10: {                        // object with keys
      const out = {};
      const keys = node.p?.k || [];
      const vals = node.p?.v || [];
      keys.forEach((k, i) => { out[k] = decodeSeroval(vals[i]); });
      return out;
    }
    case 11: return {};               // empty object
    default:
      throw new Error(`seroval: unsupported tag ${node.t} (format may have changed)`);
  }
}

// Server-fn responses are { result, error, context }; unwrap or throw.
export function unwrapServerFn(payload) {
  const decoded = decodeSeroval(payload);
  if (decoded && decoded.error) {
    throw new Error(typeof decoded.error === 'string' ? decoded.error : 'server function error');
  }
  return decoded?.result;
}
