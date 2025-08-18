"use client";

import React from 'react';
import { 
  Activity, 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  LineChart,
  Minus
} from 'lucide-react';

interface TechnicalIndicator {
  name: string;
  value: number;
  signal: 'BUY' | 'SELL' | 'NEUTRAL';
  status: 'bullish' | 'bearish' | 'neutral';
  description: string;
}

interface TechnicalIndicatorsProps {
  indicators: Record<string, TechnicalIndicator>;
  isLoading?: boolean;
}

export default function TechnicalIndicators({ indicators, isLoading }: TechnicalIndicatorsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[...Array(5)].map((_, index) => (
          <div key={index} className="kb-card p-4">
            <div className="h-4 bg-[var(--kb-bg-elevated)] rounded animate-pulse mb-2"></div>
            <div className="h-16 bg-[var(--kb-bg-elevated)] rounded animate-pulse"></div>
          </div>
        ))}
      </div>
    );
  }

  const getSignalIcon = (signal: string) => {
    switch (signal) {
      case 'BUY': return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'SELL': return <TrendingDown className="w-4 h-4 text-red-500" />;
      default: return <Minus className="w-4 h-4 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'bullish': return 'text-green-500 bg-green-500/10';
      case 'bearish': return 'text-red-500 bg-red-500/10';
      default: return 'text-yellow-500 bg-yellow-500/10';
    }
  };

  // const getGaugeColor = (value: number, type: string) => {
  //   if (type === 'RSI') {
  //     if (value > 70) return 'text-red-500';
  //     if (value < 30) return 'text-green-500';
  //     return 'text-yellow-500';
  //   }
  //   return 'text-[var(--kb-brand)]';
  // };

  const renderIndicatorGauge = (indicator: TechnicalIndicator, type: string) => {
    const percentage = Math.min(Math.max(indicator.value, 0), 100);
    
    if (type === 'RSI') {
      return (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm font-semibold">{indicator.value.toFixed(1)}</span>
            {getSignalIcon(indicator.signal)}
          </div>
          <div className="w-full bg-[var(--kb-bg-elevated)] rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${
                indicator.value > 70 ? 'bg-red-500' :
                indicator.value < 30 ? 'bg-green-500' :
                'bg-yellow-500'
              }`}
              style={{ width: `${percentage}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-[var(--kb-text-muted)]">
            <span>0</span>
            <span className="text-red-400">70</span>
            <span>100</span>
          </div>
        </div>
      );
    }

    if (type === 'MACD') {
      const isPositive = indicator.value > 0;
      return (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className={`text-sm font-semibold ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
              {indicator.value > 0 ? '+' : ''}{indicator.value.toFixed(2)}
            </span>
            {getSignalIcon(indicator.signal)}
          </div>
          <div className="h-12 flex items-end justify-center">
            <div className="w-full bg-[var(--kb-bg-elevated)] h-1 relative rounded">
              <div 
                className={`absolute top-0 h-1 rounded transition-all duration-300 ${
                  isPositive ? 'bg-green-500' : 'bg-red-500'
                }`}
                style={{ 
                  width: `${Math.abs(indicator.value) * 10}%`,
                  left: isPositive ? '50%' : `${50 - Math.abs(indicator.value) * 10}%`
                }}
              />
            </div>
          </div>
        </div>
      );
    }

    // その他の指標（汎用）
    return (
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm font-semibold">{indicator.value.toFixed(1)}</span>
          {getSignalIcon(indicator.signal)}
        </div>
        <div className="h-12 flex items-end">
          <div className="w-full bg-[var(--kb-bg-elevated)] rounded-t h-2">
            <div 
              className="bg-[var(--kb-brand)] rounded-t h-full transition-all duration-300"
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          </div>
        </div>
      </div>
    );
  };

  const indicatorConfigs = {
    RSI: { icon: Activity, label: 'RSI(14)' },
    MACD: { icon: BarChart3, label: 'MACD' },
    BBANDS: { icon: LineChart, label: 'ボリンジャーバンド' },
    MA: { icon: TrendingUp, label: '移動平均' },
    VOLUME: { icon: BarChart3, label: '出来高' },
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-[var(--kb-text)] flex items-center gap-2">
        <Activity className="w-5 h-5 text-[var(--kb-brand)]" />
        テクニカル指標
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {Object.entries(indicators).map(([key, indicator]) => {
          const config = indicatorConfigs[key as keyof typeof indicatorConfigs];
          if (!config) return null;

          return (
            <div key={key} className="kb-card p-4 relative overflow-hidden">
              {/* ステータスインジケーター */}
              <div className={`absolute top-2 right-2 w-2 h-2 rounded-full ${
                indicator.status === 'bullish' ? 'bg-green-500' :
                indicator.status === 'bearish' ? 'bg-red-500' :
                'bg-yellow-500'
              }`} />

              {/* ヘッダー */}
              <div className="flex items-center gap-2 mb-3">
                <config.icon className="w-4 h-4 text-[var(--kb-text-muted)]" />
                <span className="text-sm font-semibold truncate">{config.label}</span>
              </div>

              {/* 指標の可視化 */}
              <div className="mb-3">
                {renderIndicatorGauge(indicator, key)}
              </div>

              {/* 説明 */}
              <div className="text-xs text-[var(--kb-text-muted)] mb-2">
                {indicator.description}
              </div>

              {/* シグナル */}
              <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(indicator.status)}`}>
                {getSignalIcon(indicator.signal)}
                {indicator.signal}
              </div>
            </div>
          );
        })}
      </div>

      {/* 指標の説明 */}
      <div className="kb-card p-4 bg-[var(--kb-bg-elevated)]">
        <h4 className="text-sm font-semibold mb-2">指標の見方</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-[var(--kb-text-muted)]">
          <div>
            <strong>RSI:</strong> 70以上で過買い、30以下で過売り状態を示します
          </div>
          <div>
            <strong>MACD:</strong> ゼロライン上で強気、下で弱気のシグナル
          </div>
          <div>
            <strong>ボリンジャーバンド:</strong> バンド幅でボラティリティを判定
          </div>
          <div>
            <strong>移動平均:</strong> 短期・長期のクロスオーバーで方向性判定
          </div>
        </div>
      </div>
    </div>
  );
}