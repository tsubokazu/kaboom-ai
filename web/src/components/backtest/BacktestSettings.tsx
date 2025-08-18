"use client";

import React from "react";
import { Play, Pause, Square, RotateCcw } from "lucide-react";
import { useBacktestStore } from "@/stores/backtestStore";

export function BacktestSettings() {
  const {
    settings,
    updateSettings,
    isRunning,
    startBacktest,
    pauseBacktest,
    stopBacktest,
    resetBacktest,
  } = useBacktestStore();

  const handleInputChange = (field: string, value: string | number) => {
    updateSettings({ [field]: value });
  };

  const handleSymbolsChange = (value: string) => {
    const symbols = value.split(",").map(s => s.trim()).filter(Boolean);
    updateSettings({ symbols });
  };

  return (
    <div
      className="p-6 rounded-lg space-y-6"
      style={{
        background: "var(--kb-bg-surface)",
        border: "1px solid var(--kb-border)",
      }}
    >
      <div className="flex items-center gap-2">
        <div className="w-1 h-5 bg-[var(--kb-brand)] rounded-full" />
        <h2 className="text-lg font-semibold">バックテスト設定</h2>
      </div>

      <div className="space-y-4">
        {/* 期間設定 */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: "var(--kb-text-secondary)" }}>
              開始日
            </label>
            <input
              type="date"
              value={settings.startDate}
              onChange={(e) => handleInputChange("startDate", e.target.value)}
              className="w-full px-3 py-2 rounded border text-sm"
              style={{
                background: "var(--kb-bg-elevated)",
                border: "1px solid var(--kb-border)",
                color: "var(--kb-text-primary)",
              }}
              disabled={isRunning}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: "var(--kb-text-secondary)" }}>
              終了日
            </label>
            <input
              type="date"
              value={settings.endDate}
              onChange={(e) => handleInputChange("endDate", e.target.value)}
              className="w-full px-3 py-2 rounded border text-sm"
              style={{
                background: "var(--kb-bg-elevated)",
                border: "1px solid var(--kb-border)",
                color: "var(--kb-text-primary)",
              }}
              disabled={isRunning}
            />
          </div>
        </div>

        {/* 資金・手数料設定 */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: "var(--kb-text-secondary)" }}>
              初期資金 (円)
            </label>
            <input
              type="number"
              value={settings.initialCapital}
              onChange={(e) => handleInputChange("initialCapital", Number(e.target.value))}
              className="w-full px-3 py-2 rounded border text-sm"
              style={{
                background: "var(--kb-bg-elevated)",
                border: "1px solid var(--kb-border)",
                color: "var(--kb-text-primary)",
              }}
              placeholder="1000000"
              min={0}
              step={10000}
              disabled={isRunning}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: "var(--kb-text-secondary)" }}>
              手数料 (%)
            </label>
            <input
              type="number"
              value={settings.commission}
              onChange={(e) => handleInputChange("commission", Number(e.target.value))}
              className="w-full px-3 py-2 rounded border text-sm"
              style={{
                background: "var(--kb-bg-elevated)",
                border: "1px solid var(--kb-border)",
                color: "var(--kb-text-primary)",
              }}
              placeholder="0.1"
              min={0}
              max={5}
              step={0.01}
              disabled={isRunning}
            />
          </div>
        </div>

        {/* 銘柄設定 */}
        <div>
          <label className="block text-sm font-medium mb-1" style={{ color: "var(--kb-text-secondary)" }}>
            対象銘柄 (カンマ区切り)
          </label>
          <input
            type="text"
            value={settings.symbols.join(", ")}
            onChange={(e) => handleSymbolsChange(e.target.value)}
            className="w-full px-3 py-2 rounded border text-sm"
            style={{
              background: "var(--kb-bg-elevated)",
              border: "1px solid var(--kb-border)",
              color: "var(--kb-text-primary)",
            }}
            placeholder="7203, 9984, 6758"
            disabled={isRunning}
          />
          <p className="text-xs mt-1" style={{ color: "var(--kb-text-muted)" }}>
            例: 7203 (トヨタ), 9984 (ソフトバンク), 6758 (ソニー)
          </p>
        </div>
      </div>

      {/* 実行ボタン */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={startBacktest}
          disabled={isRunning}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded font-medium text-sm transition-colors"
          style={{
            background: isRunning ? "var(--kb-bg-muted)" : "var(--kb-brand)",
            color: isRunning ? "var(--kb-text-muted)" : "white",
            cursor: isRunning ? "not-allowed" : "pointer",
          }}
        >
          <Play size={16} />
          実行
        </button>
        <button
          onClick={pauseBacktest}
          disabled={!isRunning}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded font-medium text-sm transition-colors"
          style={{
            background: !isRunning ? "var(--kb-bg-muted)" : "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
            color: !isRunning ? "var(--kb-text-muted)" : "var(--kb-text-primary)",
            cursor: !isRunning ? "not-allowed" : "pointer",
          }}
        >
          <Pause size={16} />
          一時停止
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={stopBacktest}
          disabled={!isRunning}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded font-medium text-sm transition-colors"
          style={{
            background: !isRunning ? "var(--kb-bg-muted)" : "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
            color: !isRunning ? "var(--kb-text-muted)" : "var(--kb-text-primary)",
            cursor: !isRunning ? "not-allowed" : "pointer",
          }}
        >
          <Square size={16} />
          停止
        </button>
        <button
          onClick={resetBacktest}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded font-medium text-sm transition-colors"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
            color: "var(--kb-text-primary)",
          }}
        >
          <RotateCcw size={16} />
          リセット
        </button>
      </div>
    </div>
  );
}