import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LeadOS — AI Lead Intelligence & Discovery",
  description: "Turn raw business data into verified, high-scoring sales leads.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-950 text-slate-50 antialiased dark">
      <body className={`${inter.className} min-h-full flex flex-col bg-slate-950 text-slate-100`}>
        {children}
      </body>
    </html>
  );
}
