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
        <form action="/api/auth/sign-out" method="post">
          <button className="side-signout" type="submit">Sign out</button>
        </form>
      </aside>
      <main className="studio-main">{children}</main>
    </div>
  );
}