import Link from "next/link";

function BrandMark() {
  return (
    <svg className="beta-thanks-mark" viewBox="0 0 64 64" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeLinecap="square" strokeLinejoin="miter">
        <rect x="5" y="9" width="54" height="46" rx="1.5" strokeWidth="3.5" />
        <path d="M15 46V20L32 38L49 20V46" strokeWidth="4.5" />
      </g>
    </svg>
  );
}

export default function ThanksPage() {
  return (
    <main className="beta-thanks">
      <div className="beta-thanks-inner">
        <BrandMark />
        <p className="beta-thanks-kicker">Montage · Private beta</p>
        <h1>You’re on the list.</h1>
        <p>We’re opening Montage in small groups while we finish production connection proof for the cloud media workflow. We’ll use the email you submitted when your beta invite is ready.</p>
        <Link href="/">Back to Montage</Link>
      </div>
    </main>
  );
}
