/**
 * Browser-only source-media persistence for an MVP test workspace.
 * This is device-local IndexedDB, never uploaded to Montage or any third party.
 */
const DB_NAME = "montage.local-source-media.v1";
const STORE = "sources";
const MAX_BYTES = 250 * 1024 * 1024;

function openDatabase(): Promise<IDBDatabase> {
  if (typeof indexedDB === "undefined") return Promise.reject(new Error("IndexedDB is unavailable in this browser."));
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) request.result.createObjectStore(STORE);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Could not open browser media storage."));
  });
}

function key(projectId: string, assetId: string): string {
  return JSON.stringify([projectId, assetId]);
}

export async function saveBrowserSource(projectId: string, assetId: string, file: File): Promise<void> {
  if (file.size <= 0 || file.size > MAX_BYTES) {
    throw new Error("For the browser-only MVP, choose a source file between 1 byte and 250 MB.");
  }
  if (!file.type.startsWith("video/")) throw new Error("Browser rendering requires a supported video file.");
  const db = await openDatabase();
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction(STORE, "readwrite");
      transaction.objectStore(STORE).put(file, key(projectId, assetId));
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error || new Error("Browser source storage failed."));
      transaction.onabort = () => reject(transaction.error || new Error("Browser source storage was aborted."));
    });
  } finally {
    db.close();
  }
}

export async function getBrowserSource(projectId: string, assetId: string): Promise<Blob | null> {
  const db = await openDatabase();
  try {
    return await new Promise<Blob | null>((resolve, reject) => {
      const transaction = db.transaction(STORE, "readonly");
      const request = transaction.objectStore(STORE).get(key(projectId, assetId));
      request.onsuccess = () => resolve(request.result instanceof Blob ? request.result : null);
      request.onerror = () => reject(request.error || new Error("Browser source retrieval failed."));
    });
  } finally {
    db.close();
  }
}

export async function browserSourceUrl(projectId: string, assetId: string): Promise<string | null> {
  const source = await getBrowserSource(projectId, assetId);
  return source ? URL.createObjectURL(source) : null;
}
