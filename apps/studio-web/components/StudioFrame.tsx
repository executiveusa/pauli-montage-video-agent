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
          <div className="side-kicker">Yappyverse Studio</div>
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
          <strong>Local-first by design</strong>
          <span>Your project stays portable. Editing engines stay replaceable.</span>
        </div>
      </aside>
      <main className="studio-main">{children}</main>
    </div>
  );
}
