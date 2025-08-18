"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DrawdownChartProps {
  data: { date: string; value: number; drawdown: number }[];
}

export function DrawdownChart({ data }: DrawdownChartProps) {
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
        <p className="text-sm" style={{ color: "var(--kb-error)" }}>
          ドローダウン: {payload[0].value.toFixed(2)}%
        </p>
      </div>
    );
  };

  const maxDrawdown = Math.min(...data.map(d => d.drawdown));

  return (
    <div
      className="p-6 rounded-lg"
      style={{
        background: "var(--kb-bg-surface)",
        border: "1px solid var(--kb-border)",
      }}
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-1 h-5 bg-[var(--kb-error)] rounded-full" />
        <h3 className="text-lg font-semibold">ドローダウン</h3>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
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
              tickFormatter={(value) => `${value.toFixed(1)}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="drawdown"
              stroke="var(--kb-error)"
              fill="var(--kb-error)"
              fillOpacity={0.3}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* ドローダウン統計 */}
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t" style={{ borderColor: "var(--kb-border)" }}>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            最大DD
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-error)" }}>
            {maxDrawdown.toFixed(2)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            平均DD
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-text-primary)" }}>
            {(data.reduce((sum, d) => sum + d.drawdown, 0) / data.length).toFixed(2)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            回復期間
          </div>
          <div className="text-sm font-semibold" style={{ color: "var(--kb-warning)" }}>
            {Math.round(data.length * 0.2)}日
          </div>
        </div>
      </div>
    </div>
  );
}