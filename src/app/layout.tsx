import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Footy Tipping",
  description: "NRL tipping tips powered by baked data."
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body className="m-0 font-sans">
        {children}
        <SpeedInsights />
      </body>
    </html>
  );
}
