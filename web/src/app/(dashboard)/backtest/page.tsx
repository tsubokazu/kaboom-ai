"use client";

import React from "react";
import { BacktestSettings } from "@/components/backtest/BacktestSettings";
import { BacktestResults } from "@/components/backtest/BacktestResults";
import { BacktestProgress } from "@/components/backtest/BacktestProgress";
import { useBacktestStore } from "@/stores/backtestStore";

export default function BacktestPage() {
  const { isRunning, progress } = useBacktestStore();

  return (
    <main className="container mx-auto p-4 space-y-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-2 h-8 bg-[var(--kb-brand)] rounded-full" />
        <h1 className="text-2xl font-bold">バックテスト</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 設定パネル */}
        <div className="lg:col-span-1">
          <BacktestSettings />
          {(isRunning || progress > 0) && <BacktestProgress />}
        </div>

        {/* 結果表示パネル */}
        <div className="lg:col-span-2">
          <BacktestResults />
        </div>
      </div>
    </main>
  );
}