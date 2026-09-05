import Link from "next/link";
import { MontageHero } from "../components/MontageHero";

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
  ["01", "Bring in your clips", "Google Drive, OneDrive, local footage, interviews, screen recordings, audio, images, and references."],
  ["02", "Find the best moments", "Search what was said and what was seen. Build selects from real moments instead of hunting the timeline."],
  ["03", "Build the montage", "Shape the sequence, captions, framing, sound, graphics, and supporting media while source masters stay protected."],
  ["04", "Export anywhere", "Review, verify, export, repurpose, and keep the project ready for the next cut."],
];

const proof = [
  ["01", "Bring real footage", "Use protected source media and keep the original immutable while Montage prepares working copies and proxies."],
  ["02", "Understand the footage", "Create time-coded transcript and scene evidence so the library becomes searchable instead of opaque."],
  ["03", "Edit reversibly", "Cut, split, undo, redo, reopen, and keep captions synchronized with the canonical timeline."],
  ["04", "Verify delivery", "Render platform-ready reviews and validate the resulting media before calling it finished."],
] as const;

const faqs = [
  ["Is this another AI video generator?", "No. Montage starts with your footage and project state. Generative providers are optional, replaceable support tools — not the owner of the edit."],
  ["Can Montage use Google Drive or OneDrive?", "Yes. The media library is designed to treat Google Drive and OneDrive as peer source providers feeding one protected asset registry."],
  ["Does it overwrite my source footage?", "No. Source masters are treated as protected. Editing happens on copies, proxies, and derivatives, with review before consequential export or publishing."],
  ["Can some of the editing intelligence run locally?", "Yes. Sage can use LM Studio/Bionic locally for private editorial reasoning while deterministic media tools handle probing, proxying, captions, cuts, and verification."],
  ["Can I use Montage today?", "Montage is in private beta. We are opening access in small groups while the public runtime and provider connections are verified. Join the waitlist and we will invite people in as capacity opens."],
] as const;

function BrandMark() {
  return (
    <svg className="landing-logo-mark" viewBox="0 0 64 64" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeLinecap="square" strokeLinejoin="miter">
        <rect x="5" y="9" width="54" height="46" rx="1.5" strokeWidth="3.5" />
        <path d="M15 46V20L32 38L49 20V46" strokeWidth="4.5" />
      </g>
    </svg>
  );
}

export default function HomePage() {
  return (
    <main className="landing">
      <a className="skip-link landing-skip" href="#landing-content">Skip to main content</a>
      <header className="landing-nav">
        <Link className="landing-logo" href="/" aria-label="Montage home"><BrandMark /><span>Montage</span></Link>
        <nav className="landing-nav-center" aria-label="Primary">
          <a href="#why">Why Montage</a>
          <a href="#flow">Workflow</a>
          <a href="#proof">How it works</a>
          <a href="#faq">FAQ</a>
        </nav>
        <div className="landing-nav-actions">
          <span className="beta-nav-label">Private beta</span>
          <a className="nav-pill" href="#waitlist">Join the waitlist</a>
        </div>
      </header>

      <div id="landing-content">
        <p className="brand-visually-hidden">Illustrated Montage source-to-story workflow</p>
        <MontageHero />

        <section className="problem-section" id="why">
          <div className="section-rule"><span>The problem</span><span>Less software. More finished work.</span></div>
          <div className="problem-grid">
            <h2>Find<br/>what<br/>matters.</h2>
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
          <div className="section-rule"><span>The workflow</span><span>Many moments → one story</span></div>
          <h2 className="flow-title">From scattered clips to one clear story.</h2>
          <div className="flow-steps">
            {flow.map(([n, title, copy]) => (
              <article className="flow-step" key={n}><span>{n}</span><h3>{title}</h3><p>{copy}</p></article>
            ))}
          </div>
        </section>

        <section className="proof-section" id="proof">
          <div className="section-rule"><span>Verified product path</span><span>Working code, not a concept reel</span></div>
          <div className="proof-heading">
            <h2>AI prepares.<br/>You decide.</h2>
            <p>Montage uses intelligence to remove unnecessary editing work while keeping source footage protected and consequential output reviewable.</p>
          </div>
          <div className="proof-grid">
            {proof.map(([n, title, copy]) => (
              <article className="proof-card" key={n}><span>{n}</span><h3>{title}</h3><p>{copy}</p></article>
            ))}
          </div>
        </section>

        <section className="offer-section" id="waitlist">
          <div className="offer-copy">
            <span className="offer-label">Private beta · invitations opening now</span>
            <h2>Bring the footage.<br/>Find the story.</h2>
            <p>Montage is opening in small groups. Join the waitlist for early access to the protected-source workflow, cloud media library, searchable scenes, Sage-assisted editing, and verified exports.</p>
          </div>
          <div className="offer-card waitlist-card">
            <div><span>Beta access</span><strong>Join</strong><small>no charge while access is gated</small></div>
            <form className="waitlist-form" name="montage-waitlist" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="/thanks">
              <input type="hidden" name="form-name" value="montage-waitlist" />
              <p className="waitlist-honeypot" aria-hidden="true">
                <label>Do not fill this out: <input name="bot-field" tabIndex={-1} autoComplete="off" /></label>
              </p>
              <label>
                <span>Name</span>
                <input name="name" type="text" autoComplete="name" placeholder="Your name" required />
              </label>
              <label>
                <span>Email</span>
                <input name="email" type="email" autoComplete="email" placeholder="you@company.com" required />
              </label>
              <label>
                <span>What do you want to make?</span>
                <select name="use-case" defaultValue="social">
                  <option value="social">Social clips / reels</option>
                  <option value="documentary">Documentary / long-form</option>
                  <option value="walkthrough">Walkthrough / product demo</option>
                  <option value="brand">Brand / campaign content</option>
                  <option value="other">Something else</option>
                </select>
              </label>
              <button className="offer-button waitlist-submit" type="submit">Join the waitlist <span>→</span></button>
              <small className="waitlist-note">Early beta invites are reviewed in small batches. No spam.</small>
            </form>
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
            <p className="final-cta-kicker">Montage /mänˈtäZH/</p>
            <h2>Many moments.<br/>One story.</h2>
            <p>Bring the footage. Montage helps you understand it, find the best moments, shape the edit, and deliver the versions.</p>
            <a href="#waitlist">Join the private beta →</a>
          </div>
        </section>
      </div>

      <footer className="landing-footer">
        <span>Montage</span>
        <span>Protected-source video storytelling · Private beta</span>
      </footer>
    </main>
  );
}
