import type { Metadata } from "next";
import type { ReactNode } from "react";

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
      <body
        style={{
          margin: 0,
          fontFamily: "Inter, system-ui, -apple-system, sans-serif",
          background: "#f6f8fa"
        }}
      >
        {children}
      </body>
    </html>
  );
}
