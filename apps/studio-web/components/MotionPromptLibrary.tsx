"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type MotionPromptPick = { slug: string; author: string; post_url: string; prompt: string; category: string; prompt_partial: boolean };
type Item = MotionPromptPick & { author_url: string; tech_tags: string[]; added: string };
type Page = { total: number; items: Item[]; categories: { category: string; count: number }[] };

const PAGE = 24;

export function MotionPromptLibraryButton({ onPick }: { onPick: (pick: MotionPromptPick) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState<Page | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [opened, setOpened] = useState(false);

  const load = useCallback(async (offset: number, q: string, cat: string) => {
    setBusy(true);
    setError("");
    try {
      const url = `/api/studio/motion-prompts?limit=${PAGE}&offset=${offset}&q=${encodeURIComponent(q)}&category=${encodeURIComponent(cat)}`;
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not load the prompt library.");
      setPage(payload);
      setItems((current) => (offset === 0 ? payload.items : [...current, ...payload.items]));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load the prompt library.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!opened) return;
    const timer = setTimeout(() => void load(0, query, category), 200);
    return () => clearTimeout(timer);
  }, [opened, query, category, load]);

  function open() {
    setOpened(true);
    dialog.current?.showModal();
  }

  function pick(item: Item) {
    onPick({ slug: item.slug, author: item.author, post_url: item.post_url, prompt: item.prompt, category: item.category, prompt_partial: item.prompt_partial });
    dialog.current?.close();
  }

  return (
    <>
      <button className="motion-library-open" onClick={open} type="button">Motion prompt library</button>
      <dialog aria-label="Motion prompt library" className="motion-library" ref={dialog}>
        <div className="motion-library-head">
          <div>
            <strong>Motion prompt library</strong>
            <p>Prompts people shared for Claude-written motion graphics, explainers, 3D scenes and interactive pieces. Picking one only fills the prompt box. Nothing is generated or paid until you preview and approve.</p>
          </div>
          <button className="motion-library-close" onClick={() => dialog.current?.close()} type="button">Close</button>
        </div>
        <div className="motion-library-filters">
          <input aria-label="Search prompts" onChange={(event) => setQuery(event.target.value)} placeholder="Search prompt text, creator or tech" type="search" value={query} />
          <select aria-label="Category" onChange={(event) => setCategory(event.target.value)} value={category}>
            <option value="">All categories{page ? ` (${page.categories.reduce((sum, c) => sum + c.count, 0)})` : ""}</option>
            {page?.categories.map((c) => <option key={c.category} value={c.category}>{c.category} ({c.count})</option>)}
          </select>
        </div>
        {error && <div className="generation-error">{error}</div>}
        <ul className="motion-library-list">
          {items.map((item) => (
            <li key={item.slug}>
              <div className="motion-library-meta">
                <span>{item.category}{item.tech_tags.length ? ` · ${item.tech_tags.join(", ")}` : ""}</span>
                <span>by <a href={item.author_url} rel="noopener noreferrer" target="_blank">@{item.author}</a> · <a href={item.post_url} rel="noopener noreferrer" target="_blank">original post</a></span>
              </div>
              <p>{item.prompt.length > 360 ? `${item.prompt.slice(0, 360)}…` : item.prompt}</p>
              {item.prompt_partial && <em>Only part of this prompt was published.</em>}
              <button className="generation-primary" onClick={() => pick(item)} type="button">Use this prompt</button>
            </li>
          ))}
        </ul>
        {!busy && page && items.length === 0 && <div className="generation-empty">No prompts match.</div>}
        {page && items.length < page.total && <button className="motion-library-more" disabled={busy} onClick={() => void load(items.length, query, category)} type="button">{busy ? "Loading…" : `Load more (${items.length} of ${page.total})`}</button>}
        <p className="motion-library-credit">Prompts belong to their creators. Collection from yihui-dev/awesome-opus5-5-videos (MIT).</p>
      </dialog>
    </>
  );
}
