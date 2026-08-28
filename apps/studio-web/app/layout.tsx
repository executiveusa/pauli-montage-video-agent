import type { Metadata } from "next";
import "./globals.css";
import "./landing.css";
import "./timeline.css";
import "./generation.css";
import "./footage.css";
import "./hosted-assets.css";
import "./design-system.css";

export const metadata: Metadata = {
  title: {
    default: "MONTAGE — Find the story in your footage",
    template: "%s · MONTAGE",
  },
  description:
    "A calm AI video studio for finding moments, shaping edits, creating clips, and delivering finished stories from real footage.",
  applicationName: "MONTAGE",
  keywords: ["video editing", "transcript editing", "local-first video", "AI video workflow"],
  openGraph: {
    type: "website",
    title: "MONTAGE — Find the story in your footage",
    description: "Search real footage, shape reversible edits, and deliver verified versions from one owner-controlled project.",
    siteName: "MONTAGE",
  },
  twitter: {
    card: "summary",
    title: "MONTAGE — Find the story in your footage",
    description: "A local-first video workspace for source, story, edits, review, and delivery.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body data-analytics-scope="consent-required">{children}</body>
    </html>
  );
}
