import Link from "next/link";

const capabilities = [
  {
    kicker: "Real footage",
    title: "Find the story inside the footage.",
    copy: "Import interviews and source media, work from transcript-aware project state, and keep every editorial decision traceable.",
  },
  {
    kicker: "Short-form",
    title: "Turn one master into many cuts.",
    copy: "Create vertical versions, captions, hooks, reframes, and campaign derivatives without rebuilding the project from scratch.",
  },
  {
    kicker: "AI production",
    title: "Generate without losing continuity.",
    copy: "Use replaceable image, video, avatar, and voice engines while the project keeps ownership of canon, assets, approvals, and versions.",
  },
  {
    kicker: "Local-first",
    title: "Use the best engine. Keep the project.",
    copy: "Run deterministic editing and finishing through owner-controlled tools, with cloud providers available when they actually add value.",
  },
];

export default function HomePage() {
  return (
    <main className="site-shell landing-light">
      <header className="topbar product-topbar">
        <Link className="brand product-brand" href="/">MONTAGE</Link>
        <nav className="nav product-nav" aria-label="Primary">
          <a href="#product">Product</a>
          <a href="#workflow">Workflow</a>
          <a href="#control">Control</a>
        </nav>
        <Link className="button ink" href="/studio">Open Studio</Link>
      </header>

      <section className="hero product-hero">
        <div className="eyebrow dark-eyebrow">AI-native video production, without the software maze</div>
        <h1>From footage to finished story.</h1>
        <div className="hero-copy">
          <p>
            Montage gives creators one calm workspace to bring in footage, shape the edit,
            review changes, and deliver platform-ready video while keeping the project portable.
          </p>
          <div className="hero-actions">
            <Link className="button accent" href="/studio/new">Start a project</Link>
            <Link className="button ink-outline" href="/studio">See the studio</Link>
          </div>
        </div>
      </section>

      <section className="product-marquee" aria-label="Core promise">
        <span>CREATE</span><span>EDIT</span><span>REVIEW</span><span>DELIVER</span>
      </section>

      <section className="section product-section" id="product">
        <div className="section-header product-section-header">
          <h2>One project.<br />Every production engine.</h2>
          <p>
            The interface stays understandable even when the production stack underneath it is sophisticated.
            Engines can change. Project history, approvals, and ownership do not.
          </p>
        </div>
        <div className="lane-grid product-card-grid">
          {capabilities.map((item) => (
            <article className="lane-card product-card" key={item.title}>
              <small>{item.kicker}</small>
              <h3>{item.title}</h3>
              <p>{item.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section product-section workflow-section" id="workflow">
        <div className="section-header product-section-header">
          <h2>A workflow people can remember.</h2>
          <p>No architecture vocabulary required. Every project follows the same four visible stages.</p>
        </div>
        <div className="workflow-large">
          <div><span>01</span><strong>Create</strong><p>Outcome, source material, audience, constraints.</p></div>
          <div><span>02</span><strong>Edit</strong><p>Transcript, timeline, captions, crop, sound.</p></div>
          <div><span>03</span><strong>Review</strong><p>Version changes, quality checks, approvals.</p></div>
          <div><span>04</span><strong>Deliver</strong><p>Verified exports, manifests, reusable assets.</p></div>
        </div>
      </section>

      <section className="section product-section control-section" id="control">
        <div className="control-card">
          <div>
            <div className="eyebrow dark-eyebrow">Built to stay yours</div>
            <h2>Keep the project. Swap the engine.</h2>
          </div>
          <p>
            Montage is designed so local editors, FFmpeg workers, generation providers, transcription engines,
            and specialist agents can plug in without becoming the owner of your project.
          </p>
        </div>
      </section>

      <footer className="footer product-footer">
        <span>MONTAGE / Yappyverse Studio</span>
        <span>Portable project truth. Replaceable engines.</span>
      </footer>
    </main>
  );
}
