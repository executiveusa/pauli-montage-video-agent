"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import type { CreateProjectInput, ServiceError } from "@/lib/studio-api";
import { createLocalProject } from "@/lib/local-studio-store";

const LOCAL_FALLBACK_ERRORS = new Set([
  "service_not_connected",
  "authentication_not_configured",
  "service_unreachable",
]);

export function CreateProjectForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setSubmitting(true);
    setMessage(null);
    setIsError(false);
    const form = new FormData(formElement);
    const payload: CreateProjectInput = {
      slug: String(form.get("slug") || ""),
      title: String(form.get("title") || ""),
      objective: String(form.get("objective") || ""),
      deliverables: [String(form.get("deliverable") || "16:9 master")],
      quality_lane: String(form.get("quality_lane") || "premium") as CreateProjectInput["quality_lane"],
    };

    try {
      const response = await fetch("/api/studio/projects", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        const error = result as ServiceError;
        if (LOCAL_FALLBACK_ERRORS.has(error.error)) {
          const local = createLocalProject(payload);
          router.push(`/studio/projects/${encodeURIComponent(local.project.id)}/edit`);
          router.refresh();
          return;
        }
        throw new Error(error.message || "Project could not be created.");
      }
      const projectId = result.project?.id;
      if (!projectId) throw new Error("Project was created without a canonical ID.");
      setMessage(`Project created: ${result.project?.title || projectId}`);
      router.push(`/studio/projects/${encodeURIComponent(projectId)}/create`);
      router.refresh();
    } catch (error) {
      setIsError(true);
      setMessage(error instanceof Error ? error.message : "Project could not be created.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <div className="field"><label htmlFor="title">Project title</label><input id="title" name="title" placeholder="A name humans recognize" required /></div>
      <div className="field"><label htmlFor="slug">Project slug</label><input id="slug" name="slug" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="asc3nd-founder-story" required /></div>
      <div className="field"><label htmlFor="objective">What are we making?</label><textarea id="objective" name="objective" placeholder="Describe the outcome, audience, story, footage, references, or campaign goal." required /></div>
      <div className="field"><label htmlFor="deliverable">Primary deliverable</label><select id="deliverable" name="deliverable" defaultValue="9:16 vertical master"><option>16:9 master</option><option>9:16 vertical master</option><option>1:1 campaign master</option><option>Documentary rough cut</option><option>Character / avatar proof</option></select></div>
      <div className="field"><label htmlFor="quality_lane">Quality lane</label><select id="quality_lane" name="quality_lane" defaultValue="sovereign"><option value="economy">Economy — optimize cost</option><option value="premium">Premium — optimize quality</option><option value="sovereign">Sovereign — prefer owner-controlled compute</option><option value="owner_private">Owner private — private/restricted tools allowed</option></select></div>
      {message ? <div className={`notice ${isError ? "error" : ""}`}>{message}</div> : null}
      <div className="form-actions"><button className="generation-primary" disabled={submitting} type="submit">{submitting ? "Creating…" : "Create project"}</button><Link className="button secondary" href="/studio">Cancel</Link></div>
      <p className="muted" style={{ fontSize: ".78rem", lineHeight: 1.5 }}>Montage uses the hosted Studio API when it is connected. If that service is unavailable, the project is created in a browser-local StudioProject workspace so you can keep working without inventing server state or paying for an editor agent.</p>
    </form>
  );
}
