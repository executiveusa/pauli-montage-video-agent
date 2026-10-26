import Link from "next/link";

const items = [
  { label: "Projects", href: "/studio" },
  { label: "Sources", href: "/studio/sources" },
  { label: "New project", href: "/studio/new" },
] as const;

export function StudioFrame({ children, active = "Projects" }: { children: React.ReactNode; active?: string }) {
  return (
    <div className="studio-layout">
      <a className="skip-link" href="#studio-content">Skip to studio content</a>
      <aside className="sidebar">
        <div className="side-identity">
          <Link aria-label="Montage home" className="side-brand" href="/">MONTAGE</Link>
          <div className="side-kicker">Source → story → versions</div>
        </div>
        <nav className="side-nav" aria-label="Studio">
          {items.map((item) => (
            <Link
              aria-current={active === item.label ? "page" : undefined}
              className={active === item.label ? "active" : ""}
              href={item.href}
              key={item.label}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="side-spacer" />
        <div className="side-note">
          <strong>One project truth</strong>
          <span>Footage, edits, review renders, and versions stay traceable to their source.</span>
        </div>
        {process.env.YAPPY_STUDIO_API_URL ? (
          <>
            <Link className="button secondary" href="/sign-in">Hosted sign-in</Link>
            <form action="/api/auth/sign-out" className="side-sign-out" method="post">
              <button type="submit">Sign out</button>
            </form>
          </>
        ) : (
          <div className="side-note" role="status">
            <strong>Browser-local test studio</strong>
            <span>Projects and original media stay on this device. Protected preview access uses Vercel sign-in; no separate Montage account is required.</span>
          </div>
        )}
      </aside>
      <main className="studio-main" id="studio-content" tabIndex={-1}>{children}</main>
    </div>
  );
}
