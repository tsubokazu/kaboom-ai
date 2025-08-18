"use client";

import React, { useState } from 'react';
import { 
  Brain, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  ShoppingCart, 
  Heart, 
  AlertTriangle,
  Info,
  Clock,
  Target,
  Shield
} from 'lucide-react';

interface EvidencePanelProps {
  aiData: {
    decision: {
      signal: string;
      confidence: number;
      model: string;
      timestamp: Date;
      entryPrice?: number;
      stopLoss?: number;
      takeProfit?: number;
      reasoning: string[];
      risks: string[];
      timeframe: string;
    };
  } | null;
  isLoading?: boolean;
  symbol: string;
}

export default function EvidencePanel({ aiData, isLoading, symbol }: EvidencePanelProps) {
  const [activeTab, setActiveTab] = useState<'decision' | 'evidence' | 'risks'>('decision');

  if (isLoading) {
    return (
      <div className="kb-card p-4">
        <div className="flex items-center gap-2 mb-4">
          <Brain className="w-5 h-5 text-[var(--kb-brand)]" />
          <span className="font-semibold">AI判断分析中...</span>
        </div>
        <div className="space-y-3">
          <div className="h-8 bg-[var(--kb-bg-elevated)] rounded animate-pulse"></div>
          <div className="h-6 bg-[var(--kb-bg-elevated)] rounded animate-pulse"></div>
          <div className="h-16 bg-[var(--kb-bg-elevated)] rounded animate-pulse"></div>
        </div>
      </div>
    );
  }

  if (!aiData) {
    return (
      <div className="kb-card p-4">
        <div className="flex items-center gap-2 mb-4">
          <Brain className="w-5 h-5 text-[var(--kb-text-muted)]" />
          <span className="font-semibold text-[var(--kb-text-muted)]">AI判断待機中</span>
        </div>
        <p className="text-sm text-[var(--kb-text-muted)]">
          銘柄を選択してAI分析を実行してください
        </p>
      </div>
    );
  }

  const { decision } = aiData;
  
  const getSignalIcon = (signal: string) => {
    switch (signal) {
      case 'BUY': return <TrendingUp className="w-5 h-5" />;
      case 'SELL': return <TrendingDown className="w-5 h-5" />;
      default: return <Minus className="w-5 h-5" />;
    }
  };

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'SELL': return 'text-red-500 bg-red-500/10 border-red-500/20';
      default: return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-green-500';
    if (confidence >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  const tabs = [
    { id: 'decision', label: 'AI判断', icon: Brain },
    { id: 'evidence', label: '根拠', icon: Info },
    { id: 'risks', label: 'リスク', icon: AlertTriangle },
  ] as const;

  return (
    <div className="space-y-4">
      {/* AI判断結果ヘッダー */}
      <div className="kb-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-5 h-5 text-[var(--kb-brand)]" />
          <span className="font-semibold">AI判断結果</span>
        </div>

        {/* シグナル表示 */}
        <div className={`flex items-center gap-3 p-3 rounded-lg border mb-3 ${getSignalColor(decision.signal)}`}>
          {getSignalIcon(decision.signal)}
          <div className="flex-1">
            <div className="font-bold text-lg">{decision.signal}</div>
            <div className="text-sm opacity-80">
              信頼度: <span className={getConfidenceColor(decision.confidence)}>{decision.confidence}%</span>
            </div>
          </div>
        </div>

        {/* モデル情報 */}
        <div className="flex items-center justify-between text-sm text-[var(--kb-text-muted)] mb-3">
          <span>モデル: {decision.model}</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {decision.timeframe}
          </span>
        </div>

        {/* 価格情報 */}
        {decision.entryPrice && (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--kb-text-muted)]">推奨エントリー:</span>
              <span className="font-semibold">¥{decision.entryPrice.toLocaleString()}</span>
            </div>
            {decision.stopLoss && (
              <div className="flex justify-between">
                <span className="text-[var(--kb-text-muted)]">ストップロス:</span>
                <span className="text-red-500">¥{decision.stopLoss.toLocaleString()}</span>
              </div>
            )}
            {decision.takeProfit && (
              <div className="flex justify-between">
                <span className="text-[var(--kb-text-muted)]">利確目標:</span>
                <span className="text-green-500">¥{decision.takeProfit.toLocaleString()}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* アクションボタン */}
      <div className="kb-card p-4">
        <div className="grid grid-cols-1 gap-2">
          <button 
            className={`kb-btn w-full justify-center ${
              decision.signal === 'BUY' ? 'kb-btn-primary' : 
              decision.signal === 'SELL' ? 'kb-btn-danger' : 'kb-btn-secondary'
            }`}
            disabled={decision.signal === 'HOLD'}
          >
            <ShoppingCart className="w-4 h-4 mr-2" />
            {decision.signal === 'BUY' ? '成行で買い' : 
             decision.signal === 'SELL' ? '成行で売り' : '取引なし'}
          </button>
          <button className="kb-btn kb-btn-secondary w-full justify-center">
            <Heart className="w-4 h-4 mr-2" />
            ウォッチリストに追加
          </button>
        </div>
      </div>

      {/* タブナビゲーション */}
      <div className="kb-card">
        <div className="flex border-b border-[var(--kb-border)]">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-[var(--kb-brand)] border-b-2 border-[var(--kb-brand)]'
                  : 'text-[var(--kb-text-muted)] hover:text-[var(--kb-text)]'
              }`}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {activeTab === 'decision' && (
            <div className="space-y-3">
              <div>
                <h4 className="font-semibold mb-2 flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  投資戦略
                </h4>
                <p className="text-sm text-[var(--kb-text-muted)]">
                  {decision.signal === 'BUY' 
                    ? `上昇トレンドを見込んで${decision.timeframe}での買いポジションを推奨します。`
                    : decision.signal === 'SELL'
                    ? `下降リスクを考慮して${decision.timeframe}での売りポジションを推奨します。`
                    : '現在は明確なトレンドが見られないため、様子見を推奨します。'
                  }
                </p>
              </div>
              <div>
                <h4 className="font-semibold mb-2">アルゴリズム情報</h4>
                <div className="text-sm text-[var(--kb-text-muted)] space-y-1">
                  <div>• 分析時刻: {decision.timestamp.toLocaleTimeString()}</div>
                  <div>• 使用モデル: {decision.model}</div>
                  <div>• 分析対象: {symbol}</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-3">
              <h4 className="font-semibold mb-2">判断根拠</h4>
              <ul className="space-y-2">
                {decision.reasoning.map((reason: string, index: number) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <div className="w-1.5 h-1.5 bg-[var(--kb-brand)] rounded-full mt-2 flex-shrink-0"></div>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {activeTab === 'risks' && (
            <div className="space-y-3">
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                <Shield className="w-4 h-4" />
                リスク要因
              </h4>
              <ul className="space-y-2">
                {decision.risks.map((risk: string, index: number) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <p className="text-xs text-[var(--kb-text-muted)]">
                  ⚠️ このAI判断は投資助言ではありません。最終的な投資判断はご自身の責任で行ってください。
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}