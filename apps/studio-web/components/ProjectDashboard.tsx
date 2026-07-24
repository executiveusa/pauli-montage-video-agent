"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { ProjectSummary, ServiceError } from "@/lib/studio-api";

const lanes = [
  ["Anime", "Canon + character continuity"],
  ["Avatars", "Voice + performance pipeline"],
  ["Documentary", "Real footage + evidence"],
  ["Clip Factory", "Long-form to campaign assets"],
] as const;

function statusCopy(error: ServiceError | null) {
  if (!error) return null;
  if (error.error === "authentication_required") {
    return {
      title: "Studio session required",
      detail: "The backend is available, but project data stays locked until you have an authenticated YAPPY Studio session.",
    };
  }
  if (error.error === "authentication_not_configured") {
    return {
      title: "Authentication not connected",
      detail: "The backend is configured, but project access remains locked until secure studio sessions are enabled.",
    };
  }
  if (error.error === "service_unreachable") {
    return {
      title: "Studio API unreachable",
      detail: "The web studio is healthy, but the configured project service did not respond inside the allowed request window.",
    };
  }
  return {
    title: "Studio API not connected",
    detail: "The visual studio is deployed, but it will not invent local project state. Connect the shared Studio API and authenticated session layer to persist real projects.",
  };
}

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
      <div className="studio-head">
        <div>
          <div className="eyebrow">Production workspace</div>
          <h1>Your studio.</h1>
          <p className="muted">One project contract. Many production engines.</p>
        </div>
        <Link className="button purple" href="/studio/new">New project</Link>
      </div>

      <div className={`service-banner ${connected ? "connected" : ""}`}>
        <div>
          <span className="status-pill">
            <span className={`status-dot ${connected ? "live" : "warn"}`} />
            {loading ? "Checking Studio API" : connected ? "Studio API connected" : unavailable?.title}
          </span>
        </div>
        <span className="muted">
          {loading
            ? "Reading service state…"
            : connected
              ? "Project operations are using the shared Phase 03 StudioService."
              : unavailable?.detail}
        </span>
      </div>

      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Projects</h2>
              <span className="muted">Canonical StudioProject workspaces</span>
            </div>
            <span className="status-pill">{projects.length} total</span>
          </div>

          {loading ? (
            <div className="empty"><strong>Loading projects…</strong></div>
          ) : projects.length ? (
            <div className="project-list">
              {projects.map((project) => (
                <div className="project-row" key={project.id}>
                  <div>
                    <strong>{project.title}</strong>
                    <div className="project-meta">{project.slug} · {project.status}</div>
                  </div>
                  <div className="project-meta">{project.schemaVersion}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">
              <strong>{error ? unavailable?.title : "No projects yet."}</strong>
              <p>
                {error
                  ? unavailable?.detail
                  : "Start with a brief. YAPPY-CLIPZ will keep characters, assets, decisions, jobs, timelines, and exports under one project contract."}
              </p>
              <Link className="button secondary" href="/studio/new">Create first project</Link>
            </div>
          )}
        </section>

        <aside className="panel">
          <div className="panel-head">
            <div><h2>Production lanes</h2><span className="muted">Built on the same project truth</span></div>
          </div>
          <div className="mini-lanes">
            {lanes.map(([name, description]) => (
              <div className="mini-lane" key={name}>
                <strong>{name}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </>
  );
}
