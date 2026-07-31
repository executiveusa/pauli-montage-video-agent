import Link from "next/link";

const lanes = [
  {
    kicker: "01 — Anime",
    title: "Character-first worlds",
    copy: "Design repeatable characters, canon, visual references, scenes, and multi-shot continuity before generation spend begins.",
    status: "Foundation ready",
  },
  {
    kicker: "02 — Avatars",
    title: "Performance, not puppets",
    copy: "A future-ready production lane for voice, identity consent, lip sync, dialogue, multilingual performance, and reusable avatar Elements.",
    status: "Adapter phase ahead",
  },
  {
    kicker: "03 — Documentary",
    title: "Real footage stays real",
    copy: "Organize interviews, archives, transcripts, b-roll, evidence, and edit decisions without forcing documentary work through a synthetic-video workflow.",
    status: "OpenMontage core",
  },
  {
    kicker: "04 — Clip Factory",
    title: "One master. Many outputs.",
    copy: "Turn approved long-form work into platform variants, captions, hooks, localized cuts, and campaign assets through one canonical project.",
    status: "Pipeline foundation",
  },
];

export default function HomePage() {
  return (
    <main className="site-shell">
      <header className="topbar">
        <Link className="brand" href="/">YAPPY<span>-CLIPZ</span></Link>
        <nav className="nav" aria-label="Primary">
          <a href="#studio">Studio</a>
          <a href="#lanes">Production lanes</a>
          <a href="#sovereign">Sovereign stack</a>
        </nav>
        <Link className="button secondary" href="/studio">Enter Studio</Link>
      </header>

      <section className="hero">
        <div className="eyebrow">Yappyverse Studio System / Production OS</div>
        <h1>Direct. Animate. Edit. <em>Ship.</em></h1>
        <div className="hero-copy">
          <p>
            An AI-native production studio built for anime, consistent characters, avatars,
            documentary footage, campaigns, and clips—without handing project truth to one model,
            editor, or SaaS vendor.
          </p>
          <div className="hero-actions">
            <Link className="button purple" href="/studio/new">Start a project</Link>
            <Link className="button secondary" href="/studio">Open Studio</Link>
          </div>
        </div>
      </section>

      <section className="proof-strip" aria-label="Architecture proof">
        <div className="proof-cell"><strong>StudioProject v1</strong><span>Neutral, portable project truth</span></div>
        <div className="proof-cell"><strong>CLI + API + MCP</strong><span>One shared service layer</span></div>
        <div className="proof-cell"><strong>ICM</strong><span>Context compression without canon loss</span></div>
        <div className="proof-cell"><strong>Owner-controlled</strong><span>Replace models, workers, and interfaces</span></div>
      </section>

      <section className="section" id="studio">
        <div className="section-header">
          <h2>A studio, not a prompt box.</h2>
          <p>
            Projects move through durable briefs, Elements, scenes, shots, approvals, jobs,
            timelines, renders, and exports. Agents and humans work on the same project contract.
          </p>
        </div>
        <div className="lane-grid" id="lanes">
          {lanes.map((lane) => (
            <article className="lane-card" key={lane.title}>
              <div>
                <small>{lane.kicker}</small>
                <h3>{lane.title}</h3>
                <p>{lane.copy}</p>
              </div>
              <div className="lane-footer">
                <span>{lane.status}</span>
                <span>YAPPY-CLIPZ →</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section" id="sovereign">
        <div className="section-header">
          <h2>Keep the brain. Swap the engines.</h2>
          <p>
            OpenMontage remains the production brain. StudioProject remains the project truth.
            Provider models, GPU workers, editors, and specialist agents plug in behind replaceable contracts.
          </p>
        </div>
        <div className="panel">
          <div className="proof-strip" style={{ margin: 0 }}>
            <div className="proof-cell"><strong>OpenMontage</strong><span>Production orchestration</span></div>
            <div className="proof-cell"><strong>OmniRouter</strong><span>Model/provider policy layer</span></div>
            <div className="proof-cell"><strong>GRINIONS</strong><span>Build and release control</span></div>
            <div className="proof-cell"><strong>ICM</strong><span>Durable context handoffs</span></div>
          </div>
        </div>
      </section>

      <footer className="footer">
        <span>YAPPY-CLIPZ / Yappyverse Studio</span>
        <span>Built to keep project truth portable.</span>
      </footer>
    </main>
  );
}
