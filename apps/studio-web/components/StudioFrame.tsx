import Link from "next/link";

const items = [
  ["Projects", "/studio"],
  ["Create", "/studio/new"],
  ["Elements", "#elements"],
  ["Canvas", "#canvas"],
  ["Timeline", "#timeline"],
  ["Settings", "#settings"],
] as const;

export function StudioFrame({ children, active = "Projects" }: { children: React.ReactNode; active?: string }) {
  return (
    <div className="studio-layout">
      <aside className="sidebar">
        <Link className="side-brand" href="/">YAPPY<span>-CLIPZ</span></Link>
        <nav className="side-nav" aria-label="Studio">
          {items.map(([label, href]) => (
            <Link className={active === label ? "active" : ""} href={href} key={label}>{label}</Link>
          ))}
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
