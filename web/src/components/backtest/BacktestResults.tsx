"use client";

import React from "react";
import { Download } from "lucide-react";
import { useBacktestStore } from "@/stores/backtestStore";
import { PerformanceMetrics } from "./PerformanceMetrics";
import { EquityChart } from "./EquityChart";
import { DrawdownChart } from "./DrawdownChart";
import { MonthlyHeatmap } from "./MonthlyHeatmap";
import { TradeHistory } from "./TradeHistory";
import { TradeDetailModal } from "./TradeDetailModal";

export function BacktestResults() {
  const { results, exportResults } = useBacktestStore();

  if (!results) {
    return (
      <div
        className="p-8 rounded-lg flex items-center justify-center"
        style={{
          background: "var(--kb-bg-surface)",
          border: "1px solid var(--kb-border)",
          minHeight: "400px",
        }}
      >
        <div className="text-center space-y-2">
          <div className="text-lg font-medium" style={{ color: "var(--kb-text-secondary)" }}>
            バックテスト結果
          </div>
          <p className="text-sm" style={{ color: "var(--kb-text-muted)" }}>
            バックテストを実行すると結果が表示されます
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* パフォーマンス指標 */}
      <PerformanceMetrics metrics={results.metrics} />

      {/* チャート */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <EquityChart data={results.equityData} />
        <DrawdownChart data={results.equityData} />
      </div>

      {/* 月別収益ヒートマップ */}
      <MonthlyHeatmap monthlyReturns={results.monthlyReturns} />

      {/* 取引履歴 */}
      <TradeHistory />

      {/* エクスポートボタン */}
      <div className="flex justify-end">
        <button
          onClick={exportResults}
          className="flex items-center gap-2 px-4 py-2 rounded font-medium text-sm transition-colors"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
            color: "var(--kb-text-primary)",
          }}
        >
          <Download size={16} />
          結果をエクスポート
        </button>
      </div>

      {/* 取引詳細モーダル */}
      <TradeDetailModal />
    </div>
  );
}