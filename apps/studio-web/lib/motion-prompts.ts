import "server-only";
import { readFileSync } from "node:fs";
import path from "node:path";

export type MotionPrompt = {
  slug: string;
  author: string;
  author_url: string;
  post_url: string;
  category: string;
  tech_tags: string[];
  prompt: string;
  prompt_partial: boolean;
  added: string;
};

export type MotionPromptQuery = { q?: string; category?: string; limit?: number; offset?: number };

let cache: MotionPrompt[] | null = null;

function load(): MotionPrompt[] {
  if (cache) return cache;
  const file = path.join(process.cwd(), "data", "motion-prompts", "videos.json");
  const parsed: unknown = JSON.parse(readFileSync(file, "utf8"));
  if (!Array.isArray(parsed)) throw new Error("motion prompt data is not a list");
  cache = parsed.filter((item): item is MotionPrompt => Boolean(item) && typeof item.slug === "string" && typeof item.prompt === "string");
  return cache;
}

export function motionPromptCategories(): { category: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const item of load()) counts.set(item.category, (counts.get(item.category) || 0) + 1);
  return [...counts.entries()].map(([category, count]) => ({ category, count })).sort((a, b) => b.count - a.count);
}

export function searchMotionPrompts({ q = "", category = "", limit = 24, offset = 0 }: MotionPromptQuery) {
  const needle = q.trim().toLowerCase();
  const safeLimit = Math.min(Math.max(Math.trunc(limit) || 24, 1), 60);
  const safeOffset = Math.max(Math.trunc(offset) || 0, 0);
  const matches = load().filter((item) => {
    if (category && item.category !== category) return false;
    if (!needle) return true;
    return item.prompt.toLowerCase().includes(needle) || item.author.toLowerCase().includes(needle) || item.tech_tags.some((tag) => tag.toLowerCase().includes(needle));
  });
  return { total: matches.length, offset: safeOffset, limit: safeLimit, items: matches.slice(safeOffset, safeOffset + safeLimit) };
}
