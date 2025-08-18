"use client";

import React from "react";
import { BacktestMetrics } from "@/stores/backtestStore";

interface PerformanceMetricsProps {
  metrics: BacktestMetrics;
}

export function PerformanceMetrics({ metrics }: PerformanceMetricsProps) {
  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('ja-JP').format(num);
  };

  const formatPercent = (num: number): string => {
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const formatCurrency = (num: number): string => {
    return `¥${formatNumber(num)}`;
  };

  const metricsData = [
    {
      label: "最終資産額",
      value: formatCurrency(metrics.finalValue),
      color: metrics.totalReturn >= 0 ? "var(--kb-success)" : "var(--kb-error)",
    },
    {
      label: "総損益",
      value: formatCurrency(metrics.totalReturn),
      color: metrics.totalReturn >= 0 ? "var(--kb-success)" : "var(--kb-error)",
    },
    {
      label: "収益率",
      value: formatPercent(metrics.totalReturnPercent),
      color: metrics.totalReturnPercent >= 0 ? "var(--kb-success)" : "var(--kb-error)",
    },
    {
      label: "勝率",
      value: formatPercent(metrics.winRate),
      color: metrics.winRate >= 50 ? "var(--kb-success)" : "var(--kb-warning)",
    },
    {
      label: "最大ドローダウン",
      value: formatPercent(-metrics.maxDrawdownPercent),
      color: metrics.maxDrawdownPercent <= 10 ? "var(--kb-success)" : 
             metrics.maxDrawdownPercent <= 20 ? "var(--kb-warning)" : "var(--kb-error)",
    },
    {
      label: "シャープレシオ",
      value: metrics.sharpeRatio.toFixed(3),
      color: metrics.sharpeRatio >= 1 ? "var(--kb-success)" : 
             metrics.sharpeRatio >= 0 ? "var(--kb-warning)" : "var(--kb-error)",
    },
    {
      label: "総取引回数",
      value: formatNumber(metrics.totalTrades),
      color: "var(--kb-text-primary)",
    },
    {
      label: "勝ちトレード",
      value: formatNumber(metrics.winTrades),
      color: "var(--kb-success)",
    },
    {
      label: "負けトレード",
      value: formatNumber(metrics.lossTrades),
      color: "var(--kb-error)",
    },
    {
      label: "平均利益",
      value: formatCurrency(metrics.avgWin),
      color: "var(--kb-success)",
    },
    {
      label: "平均損失",
      value: formatCurrency(-metrics.avgLoss),
      color: "var(--kb-error)",
    },
    {
      label: "プロフィットファクター",
      value: metrics.profitFactor.toFixed(2),
      color: metrics.profitFactor >= 1 ? "var(--kb-success)" : "var(--kb-error)",
    },
  ];

  return (
    <div
      className="p-6 rounded-lg space-y-4"
      style={{
        background: "var(--kb-bg-surface)",
        border: "1px solid var(--kb-border)",
      }}
    >
      <div className="flex items-center gap-2">
        <div className="w-1 h-5 bg-[var(--kb-brand)] rounded-full" />
        <h2 className="text-lg font-semibold">パフォーマンス指標</h2>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {metricsData.map((metric, index) => (
          <div
            key={index}
            className="p-3 rounded border"
            style={{
              background: "var(--kb-bg-elevated)",
              border: "1px solid var(--kb-border)",
            }}
          >
            <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
              {metric.label}
            </div>
            <div
              className="text-sm font-semibold"
              style={{ color: metric.color }}
            >
              {metric.value}
            </div>
          </div>
        ))}
      </div>

      {/* 詳細サマリー */}
      <div
        className="p-4 rounded mt-4"
        style={{
          background: "var(--kb-bg-elevated)",
          border: "1px solid var(--kb-border)",
        }}
      >
        <h3 className="text-sm font-semibold mb-2" style={{ color: "var(--kb-text-secondary)" }}>
          サマリー
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span style={{ color: "var(--kb-text-muted)" }}>期間収益率: </span>
            <span style={{ color: metrics.totalReturnPercent >= 0 ? "var(--kb-success)" : "var(--kb-error)" }}>
              {formatPercent(metrics.totalReturnPercent)}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--kb-text-muted)" }}>勝敗: </span>
            <span style={{ color: "var(--kb-success)" }}>{metrics.winTrades}勝</span>
            <span style={{ color: "var(--kb-text-muted)" }}> / </span>
            <span style={{ color: "var(--kb-error)" }}>{metrics.lossTrades}敗</span>
          </div>
          <div>
            <span style={{ color: "var(--kb-text-muted)" }}>リスク調整後収益: </span>
            <span style={{ color: metrics.sharpeRatio >= 0 ? "var(--kb-success)" : "var(--kb-error)" }}>
              シャープ {metrics.sharpeRatio.toFixed(3)}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--kb-text-muted)" }}>最大DD: </span>
            <span style={{ color: "var(--kb-error)" }}>
              {formatCurrency(metrics.maxDrawdown)} ({formatPercent(-metrics.maxDrawdownPercent)})
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}