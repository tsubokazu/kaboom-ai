"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Mascot, Wifi, Bell, ChevronDown, Sun, Moon } from "./icons";
import { useAuthStore } from "@/lib/auth-store";

function useTheme() {
  const [mode, setMode] = useState("light");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", mode === "dark");
  }, [mode]);
  return { mode, setMode };
}

export default function Navbar() {
  const { mode, setMode } = useTheme();
  const pathname = usePathname();
  const [ws, setWs] = useState("connected");
  const { user, logout } = useAuthStore();
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    const id = setInterval(() => setWs("connected"), 3000);
    return () => clearInterval(id);
  }, []);

  const wsColor = {
    connected: "var(--kb-success)",
    connecting: "var(--kb-warning)",
    disconnected: "var(--kb-error)",
  }[ws];

  const nav = [
    { href: "/", label: "ダッシュボード" },
    { href: "/ai", label: "AI分析" },
    { href: "/backtest", label: "バックテスト" },
    { href: "/admin", label: "管理" },
  ];

  return (
    <header
      style={{
        background: "var(--kb-bg-surface)",
        borderBottom: `1px solid var(--kb-border)`,
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
            <span className="text-xl font-extrabold">Kaboom.ai</span>
          </div>
          <nav className="ml-6 hidden md:flex items-center gap-2 text-sm">
            {nav.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`kb-nav-link ${active ? "active" : ""}`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-4 flex-nowrap">
          <div
            className="flex items-center gap-2 text-sm"
            title={`WebSocket: ${ws}`}
          >
            <span className="kb-ws-dot" style={{ background: wsColor }} />
            <Wifi size={16} />
          </div>
          <button className="relative" aria-label="notifications">
            <Bell size={20} />
            <span
              className="absolute -top-2 -right-1 kb-badge"
              style={{ background: "var(--kb-brand)" }}
            >
              3
            </span>
          </button>
          <button
            className="kb-pill"
            onClick={() => setMode(mode === "light" ? "dark" : "light")}
            title={"テーマ切替"}
          >
            {mode === "light" ? <Moon size={16} /> : <Sun size={16} />}
            <span>{mode === "light" ? "ダーク" : "ライト"}</span>
          </button>
          <div className="relative">
            <button
              className="flex items-center gap-2"
              onClick={() => setShowDropdown(!showDropdown)}
            >
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center"
                style={{ background: "#FED7AA" }}
              >
                {user?.username?.charAt(0).toUpperCase() || "U"}
              </div>
              <span className="hidden md:block text-sm font-medium">
                {user?.username || "User"}
              </span>
              <ChevronDown size={16} />
            </button>
            {showDropdown && (
              <div
                className="absolute right-0 mt-2 w-48 rounded-lg shadow-lg"
                style={{
                  background: "var(--kb-bg-surface)",
                  border: "1px solid var(--kb-border)",
                }}
              >
                <div className="py-1">
                  <div
                    className="px-4 py-2 text-sm"
                    style={{ color: "var(--kb-text-muted)" }}
                  >
                    {user?.email}
                  </div>
                  <hr style={{ borderColor: "var(--kb-border)" }} />
                  <button
                    onClick={() => {
                      logout();
                      setShowDropdown(false);
                    }}
                    className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    ログアウト
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
