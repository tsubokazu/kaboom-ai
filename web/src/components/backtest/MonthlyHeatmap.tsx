"use client";

import React from "react";

interface MonthlyHeatmapProps {
  monthlyReturns: { [key: string]: number };
}

export function MonthlyHeatmap({ monthlyReturns }: MonthlyHeatmapProps) {
  const months = [
    "1月", "2月", "3月", "4月", "5月", "6月",
    "7月", "8月", "9月", "10月", "11月", "12月"
  ];

  const getIntensity = (value: number): number => {
    const absValue = Math.abs(value);
    if (absValue === 0) return 0;
    if (absValue < 2) return 0.2;
    if (absValue < 5) return 0.4;
    if (absValue < 10) return 0.6;
    if (absValue < 15) return 0.8;
    return 1;
  };

  const getCellStyle = (value: number) => {
    const intensity = getIntensity(value);
    const isPositive = value >= 0;
    
    if (value === 0) {
      return {
        background: "var(--kb-bg-elevated)",
        color: "var(--kb-text-muted)",
      };
    }

    const baseColor = isPositive ? "var(--kb-success)" : "var(--kb-error)";
    
    return {
      background: `color-mix(in srgb, ${baseColor} ${intensity * 100}%, var(--kb-bg-elevated))`,
      color: intensity > 0.6 ? "white" : "var(--kb-text-primary)",
    };
  };

  // 2024年のデータを整理
  const year = 2024;
  const monthlyData = months.map((month, index) => {
    const monthKey = `${year}-${(index + 1).toString().padStart(2, '0')}`;
    const value = monthlyReturns[monthKey] || 0;
    return {
      month,
      value,
      key: monthKey,
    };
  });

  const totalReturn = Object.values(monthlyReturns).reduce((sum, value) => sum + value, 0);
  const positiveMonths = Object.values(monthlyReturns).filter(v => v > 0).length;
  const negativeMonths = Object.values(monthlyReturns).filter(v => v < 0).length;
  const bestMonth = Math.max(...Object.values(monthlyReturns));
  const worstMonth = Math.min(...Object.values(monthlyReturns));

  return (
    <div
      className="p-6 rounded-lg"
      style={{
        background: "var(--kb-bg-surface)",
        border: "1px solid var(--kb-border)",
      }}
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-1 h-5 bg-[var(--kb-brand)] rounded-full" />
        <h3 className="text-lg font-semibold">月別収益ヒートマップ ({year}年)</h3>
      </div>

      {/* ヒートマップ */}
      <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2 mb-6">
        {monthlyData.map((data) => (
          <div
            key={data.key}
            className="p-3 rounded text-center cursor-pointer transition-all hover:scale-105"
            style={getCellStyle(data.value)}
            title={`${data.month}: ${data.value >= 0 ? '+' : ''}${data.value.toFixed(2)}%`}
          >
            <div className="text-xs font-medium mb-1">
              {data.month}
            </div>
            <div className="text-sm font-bold">
              {data.value >= 0 ? '+' : ''}{data.value.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>

      {/* 統計サマリー */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div
          className="p-3 rounded text-center"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
          }}
        >
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            年間収益率
          </div>
          <div
            className="text-sm font-semibold"
            style={{ color: totalReturn >= 0 ? "var(--kb-success)" : "var(--kb-error)" }}
          >
            {totalReturn >= 0 ? '+' : ''}{totalReturn.toFixed(2)}%
          </div>
        </div>
        
        <div
          className="p-3 rounded text-center"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
          }}
        >
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            プラス月
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-success)" }}>
            {positiveMonths}ヶ月
          </div>
        </div>

        <div
          className="p-3 rounded text-center"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
          }}
        >
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            マイナス月
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-error)" }}>
            {negativeMonths}ヶ月
          </div>
        </div>

        <div
          className="p-3 rounded text-center"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
          }}
        >
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            最高月
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-success)" }}>
            +{bestMonth.toFixed(2)}%
          </div>
        </div>

        <div
          className="p-3 rounded text-center"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
          }}
        >
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            最低月
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-error)" }}>
            {worstMonth.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* 色の凡例 */}
      <div className="mt-6 flex items-center justify-center gap-4">
        <span className="text-xs" style={{ color: "var(--kb-text-muted)" }}>損失</span>
        <div className="flex gap-1">
          {[-15, -10, -5, -2, 0, 2, 5, 10, 15].map(value => (
            <div
              key={value}
              className="w-4 h-4 rounded"
              style={getCellStyle(value)}
              title={`${value >= 0 ? '+' : ''}${value}%`}
            />
          ))}
        </div>
        <span className="text-xs" style={{ color: "var(--kb-text-muted)" }}>利益</span>
      </div>
    </div>
  );
}