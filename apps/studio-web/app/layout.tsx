import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "YAPPY-CLIPZ — AI-Native Production Studio",
  description:
    "A sovereign production studio for anime, consistent characters, AI avatars, documentary footage, campaigns, and clips.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
