"use client";

import React from "react";
import { useBacktestStore } from "@/stores/backtestStore";

export function BacktestProgress() {
  const { progress, isRunning } = useBacktestStore();

  if (!isRunning && progress === 0) return null;

  return (
    <div
      className="p-4 rounded-lg mt-4 space-y-3"
      style={{
        background: "var(--kb-bg-surface)",
        border: "1px solid var(--kb-border)",
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium" style={{ color: "var(--kb-text-secondary)" }}>
          進捗
        </span>
        <span className="text-sm font-mono" style={{ color: "var(--kb-text-primary)" }}>
          {Math.round(progress)}%
        </span>
      </div>

      {/* プログレスバー */}
      <div
        className="w-full h-3 rounded-full overflow-hidden"
        style={{ background: "var(--kb-bg-elevated)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-300 ease-out"
          style={{
            width: `${progress}%`,
            background: isRunning
              ? "linear-gradient(90deg, var(--kb-brand) 0%, var(--kb-brand-light) 100%)"
              : "var(--kb-success)",
          }}
        />
      </div>

      {/* ステータステキスト */}
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${
            isRunning ? "animate-pulse" : ""
          }`}
          style={{
            background: isRunning ? "var(--kb-brand)" : "var(--kb-success)",
          }}
        />
        <span className="text-sm" style={{ color: "var(--kb-text-secondary)" }}>
          {isRunning
            ? "バックテスト実行中..."
            : progress >= 100
            ? "バックテスト完了"
            : "一時停止中"}
        </span>
      </div>

      {/* 推定残り時間（実行中のみ） */}
      {isRunning && progress > 0 && progress < 100 && (
        <div className="text-xs" style={{ color: "var(--kb-text-muted)" }}>
          推定残り時間: {Math.round((100 - progress) * 0.05)}秒
        </div>
      )}
    </div>
  );
}