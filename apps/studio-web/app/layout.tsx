import type { Metadata } from "next";
import "./globals.css";
import "./landing.css";
import "./timeline.css";
import "./generation.css";
import "./footage.css";
import "./design-system.css";

export const metadata: Metadata = {
  title: "MONTAGE — Find the story in your footage",
  description:
    "A calm AI video studio for finding moments, shaping edits, creating clips, and delivering finished stories from real footage.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
