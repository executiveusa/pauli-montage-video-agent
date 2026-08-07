"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { ProjectSummary, ServiceError } from "@/lib/studio-api";
import { listLocalProjects } from "@/lib/local-studio-store";

function statusCopy(error: ServiceError | null, hasLocalProjects: boolean) {
  if (!error) return null;
  if (error.error === "authentication_required") {
    return {
      title: "Hosted projects need sign-in",
      detail: hasLocalProjects
        ? "Your browser-local projects are available below. Hosted projects remain private until a session is available."
        : "The hosted studio service is online, but its projects stay private until an authenticated session is available.",
    };
  }
  if (error.error === "authentication_not_configured") {
    return {
      title: "Local workspace ready",
      detail: "Hosted sessions are not configured yet, so Montage is using the browser-local StudioProject workspace instead of blocking the editing flow.",
    };
  }
  if (error.error === "service_unreachable") {
    return {
      title: "Local workspace ready",
      detail: "The hosted project service did not respond. Browser-local projects remain available and preserve their timeline state on this device.",
    };
  }
  return {
    title: "Local workspace ready",
    detail: "The hosted Studio API is not connected, so Montage is using real browser-local StudioProject persistence rather than showing fake server data.",
  };
}

const steps = [
  ["01", "Create", "Define the outcome and bring in source material."],
  ["02", "Edit", "Work from transcript and timeline state without touching the original."],
  ["03", "Review", "Check captions, crop, audio, rights, cost, and version changes."],
  ["04", "Deliver", "Export approved platform-ready files with evidence."],
] as const;

function mergeProjects(hosted: ProjectSummary[], local: ProjectSummary[]): ProjectSummary[] {
  const byId = new Map<string, ProjectSummary>();
  [...hosted, ...local].forEach((project) => byId.set(project.id, project));
  return [...byId.values()].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function ProjectDashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [error, setError] = useState<ServiceError | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const local = listLocalProjects();
    fetch("/api/studio/projects", { cache: "no-store" })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw payload;
        return payload as ProjectSummary[];
      })
      .then((payload) => {
        if (!active) return;
        setProjects(mergeProjects(payload, local));
        setError(null);
      })
      .catch((reason: ServiceError) => {
        if (!active) return;
        setProjects(local);
        setError(reason);
      })
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  const hostedConnected = !loading && !error;
  const hasLocalProjects = projects.some((project) => project.id.startsWith("local_"));
  const unavailable = statusCopy(error, hasLocalProjects);

  return (
    <>
      <div className="studio-head studio-head-product">
        <div>
          <div className="eyebrow">Montage Studio</div>
          <h1>Make the story. Keep control.</h1>
          <p className="muted">Bring footage in, shape the cut, review every change, and export without handing the project to one vendor.</p>
        </div>
        <Link className="button accent" href="/studio/new">New project</Link>
      </div>

      <div className="workflow-strip" aria-label="Production workflow">
        {steps.map(([number, title, detail]) => (
          <div className="workflow-step" key={number}>
            <span>{number}</span>
            <strong>{title}</strong>
            <p>{detail}</p>
          </div>
        ))}
      </div>

      <div className={`service-banner ${hostedConnected ? "connected" : ""}`}>
        <span className="status-pill">
          <span className={`status-dot ${hostedConnected || !loading ? "live" : "warn"}`} />
          {loading ? "Checking project service" : hostedConnected ? "Hosted + local workspace ready" : unavailable?.title}
        </span>
        <span className="muted">
          {loading
            ? "Checking hosted project state and this device's local workspace…"
            : hostedConnected
              ? "Hosted projects and browser-local projects are available in one list."
              : unavailable?.detail}
        </span>
      </div>

      <section className="panel project-panel">
        <div className="panel-head">
          <div>
            <div className="section-label">Projects</div>
            <h2>Continue where you left off.</h2>
          </div>
          <span className="status-pill">{projects.length} {projects.length === 1 ? "project" : "projects"}</span>
        </div>

        {loading ? (
          <div className="empty"><strong>Loading your projects…</strong></div>
        ) : projects.length ? (
          <div className="project-list">
            {projects.map((project) => {
              const local = project.id.startsWith("local_");
              return (
                <Link
                  aria-label={`Open ${project.title}`}
                  className="project-row project-row-link"
                  href={`/studio/projects/${encodeURIComponent(project.id)}/edit`}
                  key={project.id}
                >
                  <div>
                    <strong>{project.title}</strong>
                    <div className="project-meta">{project.slug} · {local ? "local on this device" : project.status}</div>
                  </div>
                  <div className="project-row-action">
                    <span className="project-meta">{local ? "LOCAL" : project.schemaVersion}</span>
                    <span className="open-project">Open project →</span>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="empty empty-product">
            <strong>No projects yet.</strong>
            <p>Create one project and move through the same simple path every time: create, edit, review, deliver. A hosted API is optional for the local-first workflow.</p>
            <Link className="button secondary" href="/studio/new">Create first project</Link>
          </div>
        )}
      </section>
    </>
  );
}
