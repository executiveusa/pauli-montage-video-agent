import Link from "next/link";

const items = [
  { label: "Projects", href: "/studio", implemented: true },
  { label: "Create", href: "/studio/new", implemented: true },
  { label: "Elements", href: null, implemented: false },
  { label: "Canvas", href: null, implemented: false },
  { label: "Timeline", href: null, implemented: false },
  { label: "Settings", href: null, implemented: false },
] as const;

export function StudioFrame({ children, active = "Projects" }: { children: React.ReactNode; active?: string }) {
  return (
    <div className="studio-layout">
      <aside className="sidebar">
        <Link className="side-brand" href="/">YAPPY<span>-CLIPZ</span></Link>
        <nav className="side-nav" aria-label="Studio">
          {items.map((item) =>
            item.implemented && item.href ? (
              <Link className={active === item.label ? "active" : ""} href={item.href} key={item.label}>
                {item.label}
              </Link>
            ) : (
              <span className="disabled" aria-disabled="true" key={item.label} title="Coming in a later production phase">
                {item.label}<small>Soon</small>
              </span>
            ),
          )}
        </nav>
        <div className="side-spacer" />
        <div className="side-note">
          Project truth: StudioProject v1.<br />
          Engines stay replaceable.
        </div>
      </aside>
      <main className="studio-main">{children}</main>
    </div>
  );
}
