"use client";

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface EquityChartProps {
  data: { date: string; value: number; drawdown: number }[];
}

export function EquityChart({ data }: EquityChartProps) {
  const formatCurrency = (value: number) => {
    return `¥${new Intl.NumberFormat('ja-JP').format(value)}`;
  };

  const CustomTooltip = ({ active, payload, label }: {active?: boolean; payload?: {value: number}[]; label?: string}) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div
        className="p-3 rounded shadow-lg"
        style={{
          background: "var(--kb-bg-surface)",
          border: "1px solid var(--kb-border)",
        }}
      >
        <p className="text-sm font-medium mb-2" style={{ color: "var(--kb-text-primary)" }}>
          {label}
        </p>
        <p className="text-sm" style={{ color: "var(--kb-brand)" }}>
          資産額: {formatCurrency(payload[0].value)}
        </p>
      </div>
    );
  };

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
        <h3 className="text-lg font-semibold">資産推移</h3>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{
              top: 5,
              right: 30,
              left: 20,
              bottom: 5,
            }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--kb-border)"
              opacity={0.5}
            />
            <XAxis
              dataKey="date"
              tick={{ fill: "var(--kb-text-muted)", fontSize: 12 }}
              axisLine={{ stroke: "var(--kb-border)" }}
            />
            <YAxis
              tick={{ fill: "var(--kb-text-muted)", fontSize: 12 }}
              axisLine={{ stroke: "var(--kb-border)" }}
              tickFormatter={(value) => `¥${(value / 1000000).toFixed(1)}M`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--kb-brand)"
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 4,
                fill: "var(--kb-brand)",
                strokeWidth: 2,
                stroke: "var(--kb-bg-surface)",
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* チャート下部の統計情報 */}
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t" style={{ borderColor: "var(--kb-border)" }}>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            初期資産
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-text-primary)" }}>
            {formatCurrency(data[0]?.value || 0)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            最終資産
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-text-primary)" }}>
            {formatCurrency(data[data.length - 1]?.value || 0)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            最高資産
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-success)" }}>
            {formatCurrency(Math.max(...data.map(d => d.value)))}
          </div>
        </div>
      </div>
    </div>
  );
}