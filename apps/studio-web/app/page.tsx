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

const proof = [
  ["01", "Bring real footage", "Upload source media into an owner-controlled project and keep the original immutable."],
  ["02", "Transcribe locally", "Create time-coded transcript evidence with the local engine—no cloud transcription key required."],
  ["03", "Edit reversibly", "Cut, split, undo, redo, reopen, and keep captions synchronized with the canonical timeline."],
  ["04", "Verify delivery", "Render a source-backed 9:16 review and validate the resulting media before calling it finished."],
] as const;

const faqs = [
  ["Is this another AI video generator?", "No. Montage starts with your footage and project state. Generative providers are optional, replaceable support tools—not the owner of the edit."],
  ["Do I have to upload footage to a cloud vendor?", "The current verified workflow can keep processing on your computer through Montage Local Engine. Hosted collaboration and provider features are separate boundaries."],
  ["What can I use today?", "The repository-verified beta covers project creation, local footage ingest, transcription, reversible timeline edits, captions, review rendering, and deterministic verification."],
  ["Is it fully production-deployed?", "Not yet. The product is in a gated build sprint. The page distinguishes repository-verified capabilities from later hosted activation so you can judge it honestly."],
] as const;

export default function HomePage() {
  return (
    <main className="landing">
      <a className="skip-link landing-skip" href="#landing-content">Skip to main content</a>
      <header className="landing-nav">
        <Link className="landing-logo" href="/">MONTAGE</Link>
        <nav className="landing-nav-center" aria-label="Primary">
          <a href="#why">Why Montage</a>
          <a href="#flow">Workflow</a>
          <a href="#proof">Proof</a>
          <a href="#offer">Beta</a>
        </nav>
        <div className="landing-nav-actions">
          <Link href="/sign-in">Sign in</Link>
          <Link className="nav-pill" href="/sign-in">Enter beta</Link>
        </div>
      </header>

      <div id="landing-content">
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
            <Link className="hero-button" href="/sign-in"><span>Enter the private beta</span><span>↗</span></Link>
          </div>
        </div>
      </section>

      <section className="motion-stage" aria-label="Illustrated Montage source-to-story workflow">
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

      <section className="proof-section" id="proof">
        <div className="section-rule"><span>Verified product path</span><span>Working code, not a concept reel</span></div>
        <div className="proof-heading">
          <h2>One real path.<br/>Proven end to end.</h2>
          <p>Every claim below is backed by executable repository tests. Hosted production activation is tracked separately.</p>
        </div>
        <div className="proof-grid">
          {proof.map(([n, title, copy]) => (
            <article className="proof-card" key={n}><span>{n}</span><h3>{title}</h3><p>{copy}</p></article>
          ))}
        </div>
      </section>

      <section className="offer-section" id="offer">
        <div className="offer-copy">
          <span className="offer-label">Private local-first beta</span>
          <h2>Bring the footage.<br/>Keep the project.</h2>
          <p>Use the verified local workflow while hosted collaboration, billing, and wider provider activation move through their own release gates.</p>
        </div>
        <div className="offer-card">
          <div><span>Beta access</span><strong>$0</strong><small>during the gated build</small></div>
          <ul>
            <li>Local source ingest and transcription</li>
            <li>Reversible timeline editing</li>
            <li>Captions and vertical review renders</li>
            <li>Owner-controlled project state</li>
          </ul>
          <Link className="offer-button" href="/sign-in">Sign in to Montage <span>→</span></Link>
        </div>
      </section>

      <section className="faq-section" id="faq">
        <div className="section-rule"><span>Questions</span><span>Straight answers</span></div>
        <div className="faq-layout">
          <h2>Before you<br/>bring the footage.</h2>
          <div className="faq-list">
            {faqs.map(([question, answer], index) => (
              <details key={question} open={index === 0}><summary>{question}<span aria-hidden="true">+</span></summary><p>{answer}</p></details>
            ))}
          </div>
        </div>
      </section>

      <section className="final-cta">
        <div>
          <h2>MAKE<br/>THE CUT.</h2>
          <p>Bring the footage. Montage helps you understand it, find the best moments, shape the edit, and deliver the versions.</p>
          <Link href="/sign-in">Enter the private beta →</Link>
        </div>
      </section>

      </div>

      <footer className="landing-footer">
        <span>MONTAGE / Yappyverse Studio</span>
        <span>Owner-controlled video production</span>
      </footer>
    </main>
  );
}
