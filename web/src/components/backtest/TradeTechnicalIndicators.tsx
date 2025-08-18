"use client";

import React from "react";
import { TrendingUp, TrendingDown, AlertCircle, Activity } from "lucide-react";
import { TechnicalIndicatorData } from "@/stores/backtestStore";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface TradeTechnicalIndicatorsProps {
  indicators: TechnicalIndicatorData;
}

export function TradeTechnicalIndicators({ indicators }: TradeTechnicalIndicatorsProps) {
  const getSignalColor = (signal: 'buy' | 'sell' | 'neutral') => {
    switch (signal) {
      case 'buy': return "var(--kb-success)";
      case 'sell': return "var(--kb-error)";
      case 'neutral': return "var(--kb-warning)";
    }
  };

  const getSignalIcon = (signal: 'buy' | 'sell' | 'neutral') => {
    switch (signal) {
      case 'buy': return <TrendingUp size={16} />;
      case 'sell': return <TrendingDown size={16} />;
      case 'neutral': return <AlertCircle size={16} />;
    }
  };

  const getSignalText = (signal: 'buy' | 'sell' | 'neutral') => {
    switch (signal) {
      case 'buy': return "買いシグナル";
      case 'sell': return "売りシグナル";
      case 'neutral': return "中立";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'bullish':
      case 'high': 
      case 'golden_cross':
        return "var(--kb-success)";
      case 'bearish':
      case 'low':
      case 'dead_cross':
        return "var(--kb-error)";
      default:
        return "var(--kb-warning)";
    }
  };


  // MACDの棒グラフデータ
  const macdData = [
    { name: 'MACD', value: indicators.macd.value },
    { name: 'Signal', value: indicators.macd.signal },
    { name: 'Histogram', value: indicators.macd.histogram },
  ];

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
        <p className="text-sm font-medium mb-1" style={{ color: "var(--kb-text-primary)" }}>
          {label}
        </p>
        <p className="text-sm" style={{ color: "var(--kb-brand)" }}>
          値: {payload[0].value?.toFixed(2)}
        </p>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* RSI */}
      <div
        className="p-6 rounded-lg"
        style={{
          background: "var(--kb-bg-elevated)",
          border: "1px solid var(--kb-border)",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold" style={{ color: "var(--kb-text-primary)" }}>
            RSI (相対力指数)
          </h3>
          <div className="flex items-center gap-2">
            <div style={{ color: getSignalColor(indicators.rsi.signal) }}>
              {getSignalIcon(indicators.rsi.signal)}
            </div>
            <span 
              className="text-sm font-medium"
              style={{ color: getSignalColor(indicators.rsi.signal) }}
            >
              {getSignalText(indicators.rsi.signal)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* RSI値とゲージ */}
          <div>
            <div className="text-center mb-4">
              <div className="text-3xl font-bold mb-1" style={{ color: "var(--kb-text-primary)" }}>
                {indicators.rsi.value.toFixed(2)}
              </div>
              <div className="text-sm" style={{ color: "var(--kb-text-muted)" }}>
                {indicators.rsi.description}
              </div>
            </div>

            {/* RSIゲージ */}
            <div className="relative h-4 rounded-full overflow-hidden" style={{ background: "var(--kb-bg-surface)" }}>
              <div className="absolute inset-0 flex">
                <div className="h-full bg-[var(--kb-success)]" style={{ width: '30%' }} />
                <div className="h-full bg-[var(--kb-warning)]" style={{ width: '40%' }} />
                <div className="h-full bg-[var(--kb-error)]" style={{ width: '30%' }} />
              </div>
              <div 
                className="absolute top-0 w-1 h-full bg-white border-2 border-gray-800 transition-all duration-300"
                style={{ left: `${indicators.rsi.value}%`, transform: 'translateX(-50%)' }}
              />
            </div>
            <div className="flex justify-between text-xs mt-1" style={{ color: "var(--kb-text-muted)" }}>
              <span>0</span>
              <span>30</span>
              <span>70</span>
              <span>100</span>
            </div>
          </div>

          {/* RSI解説 */}
          <div>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-[var(--kb-success)]" />
                <span className="text-sm" style={{ color: "var(--kb-text-secondary)" }}>
                  売られすぎ圏 (0-30): 買いシグナル
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-[var(--kb-warning)]" />
                <span className="text-sm" style={{ color: "var(--kb-text-secondary)" }}>
                  中立圏 (30-70): 様子見
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-[var(--kb-error)]" />
                <span className="text-sm" style={{ color: "var(--kb-text-secondary)" }}>
                  買われすぎ圏 (70-100): 売りシグナル
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* MACD */}
      <div
        className="p-6 rounded-lg"
        style={{
          background: "var(--kb-bg-elevated)",
          border: "1px solid var(--kb-border)",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold" style={{ color: "var(--kb-text-primary)" }}>
            MACD
          </h3>
          <div className="flex items-center gap-2">
            <Activity size={16} style={{ color: getStatusColor(indicators.macd.status) }} />
            <span 
              className="text-sm font-medium"
              style={{ color: getStatusColor(indicators.macd.status) }}
            >
              {indicators.macd.status === 'bullish' ? '強気' : '弱気'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* MACD値 */}
          <div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>MACD</span>
                <span className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                  {indicators.macd.value.toFixed(3)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>Signal</span>
                <span className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                  {indicators.macd.signal.toFixed(3)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>Histogram</span>
                <span 
                  className="font-semibold"
                  style={{ color: indicators.macd.histogram >= 0 ? "var(--kb-success)" : "var(--kb-error)" }}
                >
                  {indicators.macd.histogram.toFixed(3)}
                </span>
              </div>
            </div>
            <div className="mt-4 p-3 rounded" style={{ 
              background: "var(--kb-bg-surface)",
              border: "1px solid var(--kb-border)"
            }}>
              <div className="text-sm" style={{ color: "var(--kb-text-secondary)" }}>
                {indicators.macd.description}
              </div>
            </div>
          </div>

          {/* MACDチャート */}
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={macdData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--kb-border)" opacity={0.5} />
                <XAxis 
                  dataKey="name" 
                  tick={{ fill: "var(--kb-text-muted)", fontSize: 12 }}
                  axisLine={{ stroke: "var(--kb-border)" }}
                />
                <YAxis 
                  tick={{ fill: "var(--kb-text-muted)", fontSize: 12 }}
                  axisLine={{ stroke: "var(--kb-border)" }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                  {macdData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.value >= 0 ? "var(--kb-success)" : "var(--kb-error)"} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ボリンジャーバンド */}
      <div
        className="p-6 rounded-lg"
        style={{
          background: "var(--kb-bg-elevated)",
          border: "1px solid var(--kb-border)",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold" style={{ color: "var(--kb-text-primary)" }}>
            ボリンジャーバンド
          </h3>
          <span 
            className="text-sm font-medium px-2 py-1 rounded"
            style={{ 
              background: "var(--kb-bg-surface)",
              color: "var(--kb-text-primary)",
              border: "1px solid var(--kb-border)"
            }}
          >
            {indicators.bollinger.position === 'upper' ? '上限付近' : 
             indicators.bollinger.position === 'lower' ? '下限付近' : '中央付近'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>上限 (+2σ)</span>
              <span className="font-semibold" style={{ color: "var(--kb-error)" }}>
                ¥{indicators.bollinger.upper.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>中央 (SMA)</span>
              <span className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                ¥{indicators.bollinger.middle.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>下限 (-2σ)</span>
              <span className="font-semibold" style={{ color: "var(--kb-success)" }}>
                ¥{indicators.bollinger.lower.toLocaleString()}
              </span>
            </div>
          </div>

          <div>
            <div className="p-3 rounded" style={{ 
              background: "var(--kb-bg-surface)",
              border: "1px solid var(--kb-border)"
            }}>
              <div className="text-sm" style={{ color: "var(--kb-text-secondary)" }}>
                {indicators.bollinger.description}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 移動平均線 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          className="p-6 rounded-lg"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold" style={{ color: "var(--kb-text-primary)" }}>
              移動平均線
            </h3>
            <span 
              className="text-sm font-medium"
              style={{ color: getStatusColor(indicators.sma.trend) }}
            >
              {indicators.sma.trend === 'golden_cross' ? 'ゴールデンクロス' :
               indicators.sma.trend === 'dead_cross' ? 'デッドクロス' : '中立'}
            </span>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>SMA20</span>
              <span className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                ¥{indicators.sma.sma20.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>SMA50</span>
              <span className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                ¥{indicators.sma.sma50.toLocaleString()}
              </span>
            </div>
            <div className="p-3 rounded" style={{ 
              background: "var(--kb-bg-surface)",
              border: "1px solid var(--kb-border)"
            }}>
              <div className="text-sm" style={{ color: "var(--kb-text-secondary)" }}>
                {indicators.sma.description}
              </div>
            </div>
          </div>
        </div>

        {/* 出来高 */}
        <div
          className="p-6 rounded-lg"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold" style={{ color: "var(--kb-text-primary)" }}>
              出来高分析
            </h3>
            <span 
              className="text-sm font-medium"
              style={{ color: getStatusColor(indicators.volume.status) }}
            >
              {indicators.volume.status === 'high' ? '高水準' :
               indicators.volume.status === 'low' ? '低水準' : '通常'}
            </span>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>現在出来高</span>
              <span className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                {indicators.volume.current.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>平均出来高</span>
              <span className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                {indicators.volume.average.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: "var(--kb-text-muted)" }}>比率</span>
              <span 
                className="font-semibold"
                style={{ color: indicators.volume.ratio >= 1 ? "var(--kb-success)" : "var(--kb-warning)" }}
              >
                {indicators.volume.ratio.toFixed(2)}x
              </span>
            </div>
            <div className="p-3 rounded" style={{ 
              background: "var(--kb-bg-surface)",
              border: "1px solid var(--kb-border)"
            }}>
              <div className="text-sm" style={{ color: "var(--kb-text-secondary)" }}>
                {indicators.volume.description}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}