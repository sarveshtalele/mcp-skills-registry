import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MCP Skill Registry",
  description: "Discover, upload, and run MCP skills and agents.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
