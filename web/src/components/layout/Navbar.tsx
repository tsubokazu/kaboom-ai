"use client";

import { useState, useEffect } from "react";
import { Bell, Wifi, ChevronDown, Sun, Moon } from "lucide-react";
import { Mascot, Pill } from "@/components/ui";
import { useTheme } from "@/hooks/useTheme";

interface NavbarProps {
  page: string;
  setPage: (page: string) => void;
}

export function Navbar({ page, setPage }: NavbarProps) {
  const { theme, toggleTheme } = useTheme();
  const [wsStatus, setWsStatus] = useState<
    "connected" | "connecting" | "disconnected"
  >("connected");

  useEffect(() => {
    // Simulate WebSocket status changes
    const interval = setInterval(() => {
      setWsStatus((prev) => (prev === "connected" ? "connected" : "connected"));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const wsColor = {
    connected: "var(--kb-success)",
    connecting: "var(--kb-warning)",
    disconnected: "var(--kb-error)",
  }[wsStatus];

  const pages = [
    { key: "dashboard", label: "ダッシュボード" },
    { key: "ai", label: "AI分析" },
    { key: "backtest", label: "バックテスト" },
    { key: "admin", label: "管理" },
  ];

  return (
    <header
      style={{
        background: "var(--kb-bg-surface)",
        borderBottom: "1px solid var(--kb-border)",
      }}
      className="sticky top-0 z-10"
    >
      <div
        className="kb-container flex items-center justify-between"
        style={{ paddingTop: 12, paddingBottom: 12 }}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Mascot size={28} />
            <span
              className="text-xl font-extrabold"
              style={{ color: "var(--kb-text)" }}
            >
              Kaboom.ai
            </span>
          </div>
          <nav className="ml-6 hidden md:flex items-center gap-2 text-sm">
            {pages.map((p) => (
              <a
                key={p.key}
                className={`kb-nav-link ${page === p.key ? "active" : ""}`}
                style={{ color: "var(--kb-text)" }}
                onClick={() => setPage(p.key)}
                href="#"
                onMouseDown={(e) => e.preventDefault()}
              >
                {p.label}
              </a>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4 flex-nowrap">
          <div
            className="flex items-center gap-2 text-sm"
            title={`WebSocket: ${wsStatus}`}
          >
            <span className="kb-ws-dot" style={{ background: wsColor }} />
            <Wifi size={16} color="var(--kb-text)" />
          </div>
          <button className="relative" aria-label="notifications">
            <Bell size={20} color="var(--kb-text)" />
            <span
              className="absolute -top-2 -right-1 kb-badge"
              style={{ background: "var(--kb-brand)" }}
            >
              3
            </span>
          </button>
          <Pill onClick={toggleTheme}>
            {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
            <span>{theme === "light" ? "ダーク" : "ライト"}</span>
          </Pill>
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center"
              style={{ background: "#FED7AA" }}
            >
              K
            </div>
            <ChevronDown size={16} color="var(--kb-text)" />
          </div>
        </div>
      </div>
    </header>
  );
}
