import type { Metadata } from "next";
import "./globals.css";
import "./landing.css";
import "./brand-launch.css";
import "./timeline.css";
import "./generation.css";
import "./footage.css";
import "./hosted-assets.css";
import "./design-system.css";

export const metadata: Metadata = {
  title: {
    default: "Montage — Many moments. One story.",
    template: "%s · Montage",
  },
  description:
    "Turn raw clips into social-ready stories, walkthroughs, reels, and highlight edits. Bring in footage, find the best moments, build the montage, and export anywhere.",
  applicationName: "Montage",
  keywords: ["montage maker", "video editing", "AI video workflow", "social reels", "video highlights", "walkthrough video", "Google Drive video", "OneDrive video"],
  openGraph: {
    type: "website",
    title: "Montage — Many moments. One story.",
    description: "Turn scattered footage into one clear story with protected source media, searchable moments, reversible edits, and format-ready exports.",
    siteName: "Montage",
  },
  twitter: {
    card: "summary_large_image",
    title: "Montage — Many moments. One story.",
    description: "Bring in your clips. Find the best moments. Build the montage. Export anywhere.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body data-analytics-scope="consent-required">{children}</body>
    </html>
  );
}
