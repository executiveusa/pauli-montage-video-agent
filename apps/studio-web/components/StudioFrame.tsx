import Link from "next/link";

const items = [
  { label: "Projects", href: "/studio" },
  { label: "New project", href: "/studio/new" },
] as const;

export function StudioFrame({ children, active = "Projects" }: { children: React.ReactNode; active?: string }) {
  return (
    <div className="studio-layout">
      <aside className="sidebar">
        <div>
          <Link className="side-brand" href="/">MONTAGE</Link>
          <div className="side-kicker">Source → story → versions</div>
        </div>
        <nav className="side-nav" aria-label="Studio">
          {items.map((item) => (
            <Link className={active === item.label ? "active" : ""} href={item.href} key={item.label}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="side-spacer" />
        <div className="side-note">
          <strong>One project truth</strong>
          <span>Footage, edits, review renders, and versions stay traceable to their source.</span>
        </div>
        <form action="/api/auth/sign-out" method="post" style={{ padding: "10px 14px 0" }}>
          <button
            type="submit"
            style={{
              width: "100%",
              border: "1px solid rgba(255,255,255,.12)",
              borderRadius: 10,
              background: "transparent",
              color: "#8f8a81",
              padding: "9px 10px",
              cursor: "pointer",
              textAlign: "left",
              fontSize: ".76rem",
            }}
          >
            Sign out
          </button>
        </form>
      </aside>
      <main className="studio-main">{children}</main>
    </div>
  );
}