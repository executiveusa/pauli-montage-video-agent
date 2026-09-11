"use client";

import { FormEvent, useState } from "react";

function encodeForm(form: HTMLFormElement): string {
  const data = new FormData(form);
  const params = new URLSearchParams();
  for (const [key, value] of data.entries()) {
    params.append(key, String(value));
  }
  return params.toString();
}

export function BetaWaitlistForm() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: encodeForm(event.currentTarget),
      });

      if (!response.ok) {
        throw new Error(`Beta request failed with status ${response.status}`);
      }

      window.location.assign("/thanks");
    } catch {
      setError("We couldn't send your beta request. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <form
      className="waitlist-form"
      name="montage-waitlist"
      method="POST"
      data-netlify="true"
      data-netlify-honeypot="bot-field"
      action="/"
      onSubmit={handleSubmit}
    >
      <input type="hidden" name="form-name" value="montage-waitlist" />
      <p className="waitlist-honeypot" aria-hidden="true">
        <label>Do not fill this out: <input name="bot-field" tabIndex={-1} autoComplete="off" /></label>
      </p>
      <label>
        <span>Name</span>
        <input name="name" type="text" autoComplete="name" placeholder="Your name" required disabled={submitting} />
      </label>
      <label>
        <span>Email</span>
        <input name="email" type="email" autoComplete="email" placeholder="you@company.com" required disabled={submitting} />
      </label>
      <label>
        <span>What do you want to make?</span>
        <select name="use-case" defaultValue="social" disabled={submitting}>
          <option value="social">Social clips / reels</option>
          <option value="documentary">Documentary / long-form</option>
          <option value="walkthrough">Walkthrough / product demo</option>
          <option value="brand">Brand / campaign content</option>
          <option value="other">Something else</option>
        </select>
      </label>
      <button className="offer-button waitlist-submit" type="submit" disabled={submitting} aria-busy={submitting}>
        {submitting ? "Sending request…" : "Request beta access"} <span aria-hidden="true">→</span>
      </button>
      {error ? <p className="waitlist-error" role="alert">{error}</p> : null}
      <small className="waitlist-note">Early beta invites are reviewed in small batches. No spam.</small>
    </form>
  );
}
