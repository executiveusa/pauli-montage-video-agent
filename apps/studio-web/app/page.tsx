import Link from "next/link";

const problems = [
  {
    n: "01",
    title: "Hours of footage. No map.",
    copy: "Montage turns source media into searchable scenes so you can find the moment instead of scrubbing the timeline blind.",
  },
  {
    n: "02",
    title: "Every edit starts over.",
    copy: "Keep one project truth for long cuts, shorts, captions, reframes, versions, and approvals instead of rebuilding from exports.",
  },
  {
    n: "03",
    title: "AI tools create more tabs, not less work.",
    copy: "Use AI where it helps — transcription, visual search, selects, cleanup, B-roll, captions — inside one understandable production flow.",
  },
  {
    n: "04",
    title: "The software owns the workflow.",
    copy: "Montage keeps source media, edit decisions, versions, and evidence portable while engines remain replaceable.",
  },
];

const flow = [
  ["01", "Bring it in", "Footage, interviews, screen recordings, audio, images, references."],
  ["02", "Find the story", "Search what was said and what was seen. Build selects from real moments."],
  ["03", "Shape the cut", "Edit the timeline, captions, framing, sound, graphics, and generated support media."],
  ["04", "Ship versions", "Review, verify, export, repurpose, and keep the project ready for the next cut."],
];

export default function HomePage() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Link className="landing-logo" href="/">MONTAGE</Link>
        <nav className="landing-nav-center" aria-label="Primary">
          <a href="#why">Why Montage</a>
          <a href="#flow">Workflow</a>
          <a href="#studio">Studio</a>
        </nav>
        <div className="landing-nav-actions">
          <Link href="/sign-in">Sign in</Link>
          <Link className="nav-pill" href="/studio/new">Start a project</Link>
        </div>
      </header>

      <section className="masthead">
        <div className="masthead-kicker">
          <span>AI video studio for real footage</span>
          <span>Search · Edit · Repurpose · Deliver</span>
        </div>
        <h1 className="masthead-word">MONTAGE</h1>
        <div className="masthead-bottom">
          <p className="masthead-copy">
            Find the right moment. Shape the story. Turn one body of footage into finished work without living in six different apps.
          </p>
          <div className="masthead-cta">
            <p>
              A calm production workspace for documentary footage, interviews, podcasts, campaigns, social clips, and AI-assisted finishing.
            </p>
            <Link className="hero-button" href="/studio/new"><span>Start with your footage</span><span>↗</span></Link>
          </div>
        </div>
      </section>

      <section className="motion-stage" id="studio" aria-label="Animated Montage editor preview">
        <div className="motion-top"><span>One workspace</span><span>Footage → story</span></div>
        <div className="motion-canvas">
          <div className="editor-window">
            <div className="editor-bar"><i className="editor-dot"/><i className="editor-dot"/><i className="editor-dot"/></div>
            <div className="editor-body">
              <aside className="editor-sidebar">
                <div className="editor-thumb"/><div className="editor-thumb"/><div className="editor-thumb"/>
              </aside>
              <div className="editor-main">
                <div className="preview"><div className="preview-copy">THE MOMENT<br/>YOU WERE LOOKING FOR.</div></div>
                <div className="timeline">
                  <div className="track"><i className="clip"/><i className="clip accent"/><i className="clip"/><i className="clip"/></div>
                  <div className="track"><i className="clip"/><i className="clip"/><i className="clip accent"/></div>
                  <i className="playhead"/>
                </div>
              </div>
            </div>
          </div>
          <div className="floating-card card-search"><span><i/>Visual search</span><strong>“waterfront at dusk”</strong></div>
          <div className="floating-card card-cut"><span><i/>Montage indexed</span><strong>Scene-level moments</strong></div>
        </div>
      </section>

      <section className="problem-section" id="why">
        <div className="section-rule"><span>The problem</span><span>Less software. More finished work.</span></div>
        <div className="problem-grid">
          <h2>Stop<br/>hunting.<br/>Start<br/>editing.</h2>
          <div className="problem-list">
            {problems.map((item) => (
              <article className="problem-row" key={item.n}>
                <b>{item.n}</b>
                <div><h3>{item.title}</h3><p>{item.copy}</p></div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="flow-section" id="flow">
        <div className="section-rule"><span>The workflow</span><span>Built to be remembered</span></div>
        <h2 className="flow-title">One flow from source to story.</h2>
        <div className="flow-steps">
          {flow.map(([n, title, copy]) => (
            <article className="flow-step" key={n}><span>{n}</span><h3>{title}</h3><p>{copy}</p></article>
          ))}
        </div>
      </section>

      <section className="final-cta">
        <div>
          <h2>MAKE<br/>THE CUT.</h2>
          <p>Bring the footage. Montage helps you understand it, find the best moments, shape the edit, and deliver the versions.</p>
          <Link href="/studio/new">Start a project →</Link>
        </div>
      </section>

      <footer className="landing-footer">
        <span>MONTAGE / Yappyverse Studio</span>
        <span>Owner-controlled video production</span>
      </footer>
    </main>
  );
}
