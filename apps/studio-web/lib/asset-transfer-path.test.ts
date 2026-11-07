import assert from "node:assert/strict";
import test from "node:test";
import { browserAssetTransferPath } from "./asset-transfer-path";

test("hosted media uses the authenticated Studio proxy without changing a signed token", () => {
  const token = "a".repeat(24) + "." + "b".repeat(24);
  assert.equal(browserAssetTransferPath("/api/v1/assets/transfers/" + token),
    "/api/studio/assets/transfers/" + token);
});
test("reject external, malformed and unsigned media URLs", () => {
  for (const path of [
    "https://example.com/api/v1/assets/transfers/" + "a".repeat(32),
    "//evil.example/media/" + "a".repeat(32),
    "/api/v1/assets/transfers/short",
    "/api/v1/assets/transfers/" + "a".repeat(24) + "?redirect=evil",
    "/api/v1/assets/transfers/" + "a".repeat(24) + "/../x",
  ]) assert.throws(() => browserAssetTransferPath(path));
});
