"use client";

import { useState } from "react";
import { Navbar } from "@/components/layout/Navbar";

export default function Home() {
  const [page, setPage] = useState("dashboard");

  return (
    <>
      <Navbar page={page} setPage={setPage} />
      <main className="kb-container">
        <div className="kb-card p-8">
          <h1
            className="text-2xl font-bold mb-4"
            style={{ color: "var(--kb-text)" }}
          >
            Kaboom.ai - 株式自動売買管理システム
          </h1>
          <p style={{ color: "var(--kb-text-muted)" }}>現在のページ: {page}</p>
          <div className="mt-6">
            <p style={{ color: "var(--kb-text-muted)" }}>
              Phase 1: プロジェクトセットアップ完了
              <br />
              ✅ Next.js 15 + TypeScript
              <br />
              ✅ Tailwind CSS
              <br />
              ✅ デザインシステム（CSS変数）
              <br />
              ✅ テーマ切り替え機能
              <br />✅ 基本コンポーネント
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
