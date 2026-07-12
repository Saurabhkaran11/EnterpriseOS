import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EnterpriseOS — AI Business Operator",
  description: "The AI employee that operates your business.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
