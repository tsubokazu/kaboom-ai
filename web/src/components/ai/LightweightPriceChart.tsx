"use client";

import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Calendar, TrendingUp, Volume } from 'lucide-react';

interface LightweightPriceChartProps {
  symbol: string;
  data: Array<{
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  isLoading?: boolean;
}

export default function LightweightPriceChart({ symbol, data, isLoading }: LightweightPriceChartProps) {
  const [timeframe, setTimeframe] = useState('1D');

  // Rechartsで使用するためのデータ変換
  const chartData = data.map(item => ({
    ...item,
    date: new Date(item.time).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' }),
    candleColor: item.close > item.open ? '#22c55e' : '#ef4444'
  }));

  const timeframes = [
    { label: '1分', value: '1m' },
    { label: '5分', value: '5m' },
    { label: '1時間', value: '1h' },
    { label: '1日', value: '1D' },
    { label: '1週間', value: '1W' },
  ];

  if (isLoading) {
    return (
      <div className="kb-card p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-[var(--kb-text)]">
              価格チャート - {symbol}
            </h3>
            <p className="text-sm text-[var(--kb-text-muted)]">リアルタイム価格分析</p>
          </div>
        </div>
        <div className="h-96 bg-[var(--kb-bg-elevated)] rounded-lg flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="animate-spin w-8 h-8 border-2 border-[var(--kb-brand)] border-t-transparent rounded-full"></div>
            <p className="text-[var(--kb-text-muted)]">チャートを分析中...</p>
          </div>
        </div>
      </div>
    );
  }

  const latestData = data[data.length - 1];
  const previousData = data[data.length - 2];
  const priceChange = latestData && previousData ? latestData.close - previousData.close : 0;
  const priceChangePercent = latestData && previousData ? (priceChange / previousData.close) * 100 : 0;

  return (
    <div className="kb-card p-4">
      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-[var(--kb-text)]">
            価格チャート - {symbol}
          </h3>
          <div className="flex items-center gap-4 mt-1">
            <span className="text-2xl font-bold text-[var(--kb-text)]">
              ¥{latestData?.close?.toLocaleString() || '---'}
            </span>
            <span className={`flex items-center gap-1 text-sm ${
              priceChange >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              <TrendingUp className={`w-4 h-4 ${priceChange < 0 ? 'rotate-180' : ''}`} />
              {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} 
              ({priceChangePercent >= 0 ? '+' : ''}{priceChangePercent.toFixed(2)}%)
            </span>
          </div>
        </div>

        {/* 時間足選択 */}
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-[var(--kb-text-muted)]" />
          <div className="flex bg-[var(--kb-bg-elevated)] rounded-lg p-1">
            {timeframes.map((tf) => (
              <button
                key={tf.value}
                className={`px-3 py-1 text-xs rounded-md transition-all ${
                  timeframe === tf.value
                    ? 'bg-[var(--kb-brand)] text-white'
                    : 'text-[var(--kb-text-muted)] hover:text-[var(--kb-text)]'
                }`}
                onClick={() => setTimeframe(tf.value)}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* チャート */}
      <div className="relative">
        <div className="w-full h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--kb-border)" />
              <XAxis 
                dataKey="date" 
                stroke="var(--kb-text-muted)"
                fontSize={12}
              />
              <YAxis 
                domain={['dataMin - 100', 'dataMax + 100']}
                stroke="var(--kb-text-muted)"
                fontSize={12}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'var(--kb-bg-surface)', 
                  border: '1px solid var(--kb-border)',
                  borderRadius: '8px',
                  color: 'var(--kb-text)'
                }}
                formatter={(value: number, name: string) => [
                  `¥${value?.toLocaleString()}`, 
                  name === 'close' ? '終値' : 
                  name === 'high' ? '高値' : 
                  name === 'low' ? '安値' : 
                  name === 'open' ? '始値' : name
                ]}
              />
              <Line 
                type="monotone" 
                dataKey="close" 
                stroke="var(--kb-brand)" 
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: 'var(--kb-brand)' }}
              />
              <Line 
                type="monotone" 
                dataKey="high" 
                stroke="#22c55e" 
                strokeWidth={1}
                strokeDasharray="2 2"
                dot={false}
              />
              <Line 
                type="monotone" 
                dataKey="low" 
                stroke="#ef4444" 
                strokeWidth={1}
                strokeDasharray="2 2"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        {/* 出来高チャート */}
        <div className="w-full h-32 mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--kb-border)" />
              <XAxis 
                dataKey="date" 
                stroke="var(--kb-text-muted)"
                fontSize={10}
              />
              <YAxis 
                stroke="var(--kb-text-muted)"
                fontSize={10}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'var(--kb-bg-surface)', 
                  border: '1px solid var(--kb-border)',
                  borderRadius: '8px',
                  color: 'var(--kb-text)'
                }}
                formatter={(value: number) => [value?.toLocaleString(), '出来高']}
              />
              <Bar 
                dataKey="volume" 
                fill="var(--kb-brand)"
                opacity={0.6}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        {/* チャート統計 */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-[var(--kb-bg-elevated)] p-3 rounded-lg">
            <div className="text-xs text-[var(--kb-text-muted)]">始値</div>
            <div className="text-sm font-semibold">¥{latestData?.open?.toLocaleString()}</div>
          </div>
          <div className="bg-[var(--kb-bg-elevated)] p-3 rounded-lg">
            <div className="text-xs text-[var(--kb-text-muted)]">高値</div>
            <div className="text-sm font-semibold">¥{latestData?.high?.toLocaleString()}</div>
          </div>
          <div className="bg-[var(--kb-bg-elevated)] p-3 rounded-lg">
            <div className="text-xs text-[var(--kb-text-muted)]">安値</div>
            <div className="text-sm font-semibold">¥{latestData?.low?.toLocaleString()}</div>
          </div>
          <div className="bg-[var(--kb-bg-elevated)] p-3 rounded-lg">
            <div className="text-xs text-[var(--kb-text-muted)] flex items-center gap-1">
              <Volume className="w-3 h-3" />
              出来高
            </div>
            <div className="text-sm font-semibold">{latestData?.volume?.toLocaleString()}</div>
          </div>
        </div>
      </div>
    </div>
  );
}