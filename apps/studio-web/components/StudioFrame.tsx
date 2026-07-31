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
              <span
                aria-disabled="true"
                key={item.label}
                title="Coming in a later production phase"
                style={{
                  alignItems: "center",
                  borderRadius: 12,
                  color: "#5f5b56",
                  display: "flex",
                  fontSize: ".9rem",
                  gap: 8,
                  justifyContent: "space-between",
                  padding: "11px 12px",
                  whiteSpace: "nowrap",
                }}
              >
                {item.label}<small style={{ fontSize: ".6rem", textTransform: "uppercase" }}>Soon</small>
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
