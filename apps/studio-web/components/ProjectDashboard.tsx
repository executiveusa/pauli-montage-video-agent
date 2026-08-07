"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { ProjectSummary, ServiceError } from "@/lib/studio-api";

function statusCopy(error: ServiceError | null) {
  if (!error) return null;
  if (error.error === "authentication_required") {
    return {
      title: "Sign in required",
      detail: "The studio service is online, but projects stay private until an authenticated session is available.",
    };
  }
  if (error.error === "authentication_not_configured") {
    return {
      title: "Studio sign-in is not connected yet",
      detail: "The interface is live, but secure project sessions still need to be connected before real project data can load.",
    };
  }
  if (error.error === "service_unreachable") {
    return {
      title: "Project service is temporarily unreachable",
      detail: "The studio interface is healthy, but the project service did not respond. Your browser has not created fake local data.",
    };
  }
  return {
    title: "Project service not connected",
    detail: "The product shell is live. Connect the Studio API to turn project creation, persistence, and editing into one continuous workflow.",
  };
}

const steps = [
  ["01", "Create", "Define the outcome and bring in source material."],
  ["02", "Edit", "Work from transcript and timeline state without touching the original."],
  ["03", "Review", "Check captions, crop, audio, rights, cost, and version changes."],
  ["04", "Deliver", "Export approved platform-ready files with evidence."],
] as const;

export function ProjectDashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [error, setError] = useState<ServiceError | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch("/api/studio/projects", { cache: "no-store" })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw payload;
        return payload as ProjectSummary[];
      })
      .then((payload) => active && setProjects(payload))
      .catch((reason: ServiceError) => active && setError(reason))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  const connected = !loading && !error;
  const unavailable = statusCopy(error);

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

      <div className={`service-banner ${connected ? "connected" : ""}`}>
        <span className="status-pill">
          <span className={`status-dot ${connected ? "live" : "warn"}`} />
          {loading ? "Checking project service" : connected ? "Project service connected" : unavailable?.title}
        </span>
        <span className="muted">
          {loading
            ? "Verifying the real backend before showing project state…"
            : connected
              ? "Projects below are coming from the shared Studio service."
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
            {projects.map((project) => (
              <Link
                aria-label={`Open ${project.title}`}
                className="project-row project-row-link"
                href={`/studio/projects/${encodeURIComponent(project.id)}/edit`}
                key={project.id}
              >
                <div>
                  <strong>{project.title}</strong>
                  <div className="project-meta">{project.slug} · {project.status}</div>
                </div>
                <div className="project-row-action">
                  <span className="project-meta">{project.schemaVersion}</span>
                  <span className="open-project">Open project →</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty empty-product">
            <strong>{error ? unavailable?.title : "No projects yet."}</strong>
            <p>{error ? unavailable?.detail : "Create one project and move through the same simple path every time: create, edit, review, deliver."}</p>
            {!error ? <Link className="button secondary" href="/studio/new">Create first project</Link> : null}
          </div>
        )}
      </section>
    </>
  );
}
