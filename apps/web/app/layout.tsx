import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "RAZERPAY Mandate Gateway — AI Commerce Control Center",
  description: "Verified zero-LLM payment authorization, multi-merchant product discovery, total cost truth model, and cryptographic transaction settlement.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-[#090d16] text-[#f8fafc]">
        {children}
      </body>
    </html>
  );
}
