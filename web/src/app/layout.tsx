import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Kaboom.ai - 株式自動売買管理システム",
  description:
    "AI-powered stock trading management system with backtesting capabilities",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="min-h-screen" style={{ background: "var(--kb-bg-canvas)", color: "var(--kb-text)" }}>
        <Navbar />
        {children}
        <footer className="kb-container mt-10 pb-8 text-sm" style={{ color: "var(--kb-text-muted)" }}>
          © 2025 Kaboom.ai — Sample UI built from the design system
        </footer>
      </body>
    </html>
  );
}
