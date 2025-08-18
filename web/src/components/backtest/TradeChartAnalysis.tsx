"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { ChartAnalysisData } from "@/stores/backtestStore";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface TradeChartAnalysisProps {
  chartAnalysis: {
    '1m': ChartAnalysisData;
    '5m': ChartAnalysisData;
    '1h': ChartAnalysisData;
    '4h': ChartAnalysisData;
  };
}

export function TradeChartAnalysis({ chartAnalysis }: TradeChartAnalysisProps) {
  const timeframes = [
    { key: '1m' as const, label: '1分足', data: chartAnalysis['1m'] },
    { key: '5m' as const, label: '5分足', data: chartAnalysis['5m'] },
    { key: '1h' as const, label: '1時間足', data: chartAnalysis['1h'] },
    { key: '4h' as const, label: '4時間足', data: chartAnalysis['4h'] },
  ];

  const getTrendIcon = (trend: 'bullish' | 'bearish' | 'sideways') => {
    switch (trend) {
      case 'bullish':
        return <TrendingUp size={16} style={{ color: "var(--kb-success)" }} />;
      case 'bearish':
        return <TrendingDown size={16} style={{ color: "var(--kb-error)" }} />;
      case 'sideways':
        return <Minus size={16} style={{ color: "var(--kb-warning)" }} />;
    }
  };

  const getTrendColor = (trend: 'bullish' | 'bearish' | 'sideways') => {
    switch (trend) {
      case 'bullish': return "var(--kb-success)";
      case 'bearish': return "var(--kb-error)";
      case 'sideways': return "var(--kb-warning)";
    }
  };

  const getTrendText = (trend: 'bullish' | 'bearish' | 'sideways') => {
    switch (trend) {
      case 'bullish': return "上昇トレンド";
      case 'bearish': return "下降トレンド";
      case 'sideways': return "横ばい";
    }
  };

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
          {label ? new Date(label).toLocaleTimeString('ja-JP') : ''}
        </p>
        <p className="text-sm" style={{ color: "var(--kb-brand)" }}>
          終値: {formatCurrency(payload[0].value)}
        </p>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {timeframes.map(({ key, label, data }) => (
          <div
            key={key}
            className="p-4 rounded-lg"
            style={{
              background: "var(--kb-bg-elevated)",
              border: "1px solid var(--kb-border)",
            }}
          >
            {/* ヘッダー */}
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                {label}
              </h3>
              <div className="flex items-center gap-2">
                {getTrendIcon(data.trend)}
                <span 
                  className="text-sm font-medium"
                  style={{ color: getTrendColor(data.trend) }}
                >
                  {getTrendText(data.trend)}
                </span>
              </div>
            </div>

            {/* 価格チャート */}
            <div className="h-48 mb-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={data.priceData}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="var(--kb-border)"
                    opacity={0.5}
                  />
                  <XAxis
                    dataKey="time"
                    tick={{ fill: "var(--kb-text-muted)", fontSize: 10 }}
                    axisLine={{ stroke: "var(--kb-border)" }}
                    tickFormatter={(value) => new Date(value).toLocaleTimeString('ja-JP', { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  />
                  <YAxis
                    tick={{ fill: "var(--kb-text-muted)", fontSize: 10 }}
                    axisLine={{ stroke: "var(--kb-border)" }}
                    tickFormatter={(value) => `¥${(value / 1000).toFixed(1)}K`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  
                  {/* サポート・レジスタンスライン */}
                  <ReferenceLine 
                    y={data.support} 
                    stroke="var(--kb-success)" 
                    strokeDasharray="5 5"
                    label={{ value: "サポート", position: "left" }}
                  />
                  <ReferenceLine 
                    y={data.resistance} 
                    stroke="var(--kb-error)" 
                    strokeDasharray="5 5"
                    label={{ value: "レジスタンス", position: "left" }}
                  />
                  
                  <Line
                    type="monotone"
                    dataKey="close"
                    stroke="var(--kb-brand)"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{
                      r: 3,
                      fill: "var(--kb-brand)",
                      strokeWidth: 2,
                      stroke: "var(--kb-bg-surface)",
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* 分析データ */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
                  サポートライン
                </div>
                <div className="text-sm font-semibold" style={{ color: "var(--kb-success)" }}>
                  {formatCurrency(data.support)}
                </div>
              </div>
              <div>
                <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
                  レジスタンスライン
                </div>
                <div className="text-sm font-semibold" style={{ color: "var(--kb-error)" }}>
                  {formatCurrency(data.resistance)}
                </div>
              </div>
            </div>

            {/* シグナル */}
            {data.signals.length > 0 && (
              <div className="mt-4">
                <div className="text-xs mb-2" style={{ color: "var(--kb-text-muted)" }}>
                  シグナル
                </div>
                <div className="space-y-2">
                  {data.signals.map((signal, index) => (
                    <div
                      key={index}
                      className="p-2 rounded text-xs"
                      style={{
                        background: signal.type === 'entry' 
                          ? "color-mix(in srgb, var(--kb-success) 10%, var(--kb-bg-surface))"
                          : "color-mix(in srgb, var(--kb-error) 10%, var(--kb-bg-surface))",
                        border: `1px solid ${signal.type === 'entry' ? 'var(--kb-success)' : 'var(--kb-error)'}`,
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <span style={{ 
                          color: signal.type === 'entry' ? "var(--kb-success)" : "var(--kb-error)" 
                        }}>
                          {signal.type === 'entry' ? 'エントリー' : 'エグジット'}
                        </span>
                        <span style={{ color: "var(--kb-text-primary)" }}>
                          {formatCurrency(signal.price)}
                        </span>
                      </div>
                      <div className="mt-1" style={{ color: "var(--kb-text-secondary)" }}>
                        {signal.reason}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 総合分析サマリー */}
      <div
        className="p-4 rounded-lg"
        style={{
          background: "var(--kb-bg-elevated)",
          border: "1px solid var(--kb-border)",
        }}
      >
        <h3 className="text-lg font-semibold mb-3" style={{ color: "var(--kb-text-primary)" }}>
          時間足別分析サマリー
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {timeframes.map(({ key, label, data }) => (
            <div key={key} className="text-center">
              <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
                {label}
              </div>
              <div className="flex items-center justify-center gap-1">
                {getTrendIcon(data.trend)}
                <span 
                  className="text-sm font-medium"
                  style={{ color: getTrendColor(data.trend) }}
                >
                  {getTrendText(data.trend)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}