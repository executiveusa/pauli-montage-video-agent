import type { Metadata } from "next";
import "./globals.css";
import "./landing.css";
import "./brand-launch.css";
import "./beta-launch.css";
import "./timeline.css";
import "./generation.css";
import "./footage.css";
import "./hosted-assets.css";
import "./design-system.css";

export const metadata: Metadata = {
  title: {
    default: "Montage — Turn raw footage into one finished story",
    template: "%s · Montage",
  },
  description:
    "AI-assisted video editing for real footage. Review transcripts and indexed scene evidence, protect source masters, edit reversibly, and request private beta access.",
  applicationName: "Montage",
  keywords: ["video editing", "AI video editor", "video transcription", "scene indexing", "documentary footage", "Google Drive video", "OneDrive video", "protected source media"],
  icons: {
    icon: "/brand/montage-mark.svg",
  },
  openGraph: {
    type: "website",
    title: "Montage — Turn raw footage into one finished story",
    description: "Review transcript and scene evidence, build the edit, keep source masters protected, and verify the result. Private beta.",
    siteName: "Montage",
  },
  twitter: {
    card: "summary_large_image",
    title: "Montage — Turn raw footage into one finished story",
    description: "Many moments. One story. AI-assisted editing for real footage, now opening in private beta.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body data-analytics-scope="consent-required">{children}</body>
    </html>
  );
}
