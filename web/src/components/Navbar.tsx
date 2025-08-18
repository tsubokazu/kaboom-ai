"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Mascot, Wifi, Bell, ChevronDown, Sun, Moon } from "./icons";

function useTheme() {
  const [mode, setMode] = useState("light");
  useEffect(() => {
    document.documentElement.classList.toggle('dark', mode === 'dark');
  }, [mode]);
  return { mode, setMode };
}

export default function Navbar() {
  const { mode, setMode } = useTheme();
  const pathname = usePathname();
  const [ws, setWs] = useState("connected");
  
  useEffect(() => {
    const id = setInterval(() => setWs("connected"), 3000);
    return () => clearInterval(id);
  }, []);
  
  const wsColor = {
    connected: "var(--kb-success)",
    connecting: "var(--kb-warning)",
    disconnected: "var(--kb-error)"
  }[ws];

  const nav = [
    { href: "/", label: "ダッシュボード" },
    { href: "/ai", label: "AI分析" },
    { href: "/backtest", label: "バックテスト" },
    { href: "/admin", label: "管理" },
  ];

  return (
    <header style={{ background: "var(--kb-bg-surface)", borderBottom: `1px solid var(--kb-border)` }} className="sticky top-0 z-10">
      <div className="kb-container flex items-center justify-between" style={{ paddingTop: 12, paddingBottom: 12 }}>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Mascot size={28} />
            <span className="text-xl font-extrabold">Kaboom.ai</span>
          </div>
          <nav className="ml-6 hidden md:flex items-center gap-2 text-sm">
            {nav.map(item => {
              const active = pathname === item.href;
              return (
                <Link key={item.href} href={item.href} className={`kb-nav-link ${active ? 'active' : ''}`}>
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-4 flex-nowrap">
          <div className="flex items-center gap-2 text-sm" title={`WebSocket: ${ws}`}>
            <span className="kb-ws-dot" style={{ background: wsColor }} />
            <Wifi size={16} />
          </div>
          <button className="relative" aria-label="notifications">
            <Bell size={20} />
            <span className="absolute -top-2 -right-1 kb-badge" style={{ background: "var(--kb-brand)" }}>3</span>
          </button>
          <button className="kb-pill" onClick={() => setMode(mode === "light" ? "dark" : "light")} title={"テーマ切替"}>
            {mode === "light" ? <Moon size={16} /> : <Sun size={16} />}
            <span>{mode === "light" ? "ダーク" : "ライト"}</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: "#FED7AA" }}>K</div>
            <ChevronDown size={16} />
          </div>
        </div>
      </div>
    </header>
  );
}