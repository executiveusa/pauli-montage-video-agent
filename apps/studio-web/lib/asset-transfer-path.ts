/** Resolve a signed, tenant-scoped API transfer path through the existing Studio session proxy. */
export function browserAssetTransferPath(path: string): string {
  const prefix = "/api/v1/assets/transfers/";
  if (!path.startsWith(prefix)) throw new Error("Unexpected asset transfer path.");
  const token = path.slice(prefix.length);
  if (!/^[A-Za-z0-9._~-]{16,8192}$/.test(token)) throw new Error("Invalid asset transfer token path.");
  return "/api/studio/assets/transfers/" + token;
}
