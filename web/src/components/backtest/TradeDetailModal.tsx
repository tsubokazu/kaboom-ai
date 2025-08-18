"use client";

import React, { useState } from "react";
import { X } from "lucide-react";
import { useBacktestStore } from "@/stores/backtestStore";
import { TradeChartAnalysis } from "./TradeChartAnalysis";
import { TradeTechnicalIndicators } from "./TradeTechnicalIndicators";

export function TradeDetailModal() {
  const { selectedTrade, isTradeDetailOpen, closeTradeDetail } = useBacktestStore();
  const [activeTab, setActiveTab] = useState<'chart' | 'technical'>('chart');

  if (!isTradeDetailOpen || !selectedTrade) return null;

  const formatCurrency = (value: number) => {
    return `¥${new Intl.NumberFormat('ja-JP').format(value)}`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('ja-JP');
  };


  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0, 0, 0, 0.5)" }}
    >
      <div
        className="w-full max-w-6xl max-h-[90vh] overflow-y-auto rounded-lg"
        style={{
          background: "var(--kb-bg-surface)",
          border: "1px solid var(--kb-border)",
        }}
      >
        {/* ヘッダー */}
        <div className="sticky top-0 p-6 border-b" style={{ 
          background: "var(--kb-bg-surface)", 
          borderColor: "var(--kb-border)" 
        }}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold" style={{ color: "var(--kb-text-primary)" }}>
                取引詳細分析
              </h2>
              <div className="flex items-center gap-4 mt-2 text-sm" style={{ color: "var(--kb-text-secondary)" }}>
                <span>{selectedTrade.symbol}</span>
                <span className="px-2 py-1 rounded" style={{
                  background: selectedTrade.type === 'buy' ? "var(--kb-success)" : "var(--kb-error)",
                  color: "white",
                }}>
                  {selectedTrade.type === 'buy' ? '買い' : '売り'}
                </span>
                <span>{formatDate(selectedTrade.date)}</span>
              </div>
            </div>
            <button
              onClick={closeTradeDetail}
              className="p-2 rounded hover:bg-opacity-20 transition-colors"
              style={{ color: "var(--kb-text-muted)" }}
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* 取引サマリー */}
        <div className="p-6 border-b" style={{ borderColor: "var(--kb-border)" }}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
                取引価格
              </div>
              <div className="text-lg font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                {formatCurrency(selectedTrade.price)}
              </div>
            </div>
            <div>
              <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
                数量
              </div>
              <div className="text-lg font-semibold" style={{ color: "var(--kb-text-primary)" }}>
                {selectedTrade.quantity.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
                損益
              </div>
              <div className="text-lg font-semibold" style={{ 
                color: (selectedTrade.profit || 0) >= 0 ? "var(--kb-success)" : "var(--kb-error)" 
              }}>
                {(selectedTrade.profit || 0) >= 0 ? '+' : ''}{formatCurrency(selectedTrade.profit || 0)}
              </div>
            </div>
            <div>
              <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
                AI信頼度
              </div>
              <div className="text-lg font-semibold" style={{ color: "var(--kb-brand)" }}>
                {selectedTrade.confidence}%
              </div>
            </div>
          </div>

          {/* エントリー・エグジット理由 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            <div>
              <div className="text-xs mb-2" style={{ color: "var(--kb-text-muted)" }}>
                エントリー理由
              </div>
              <div className="p-3 rounded" style={{ 
                background: "var(--kb-bg-elevated)",
                border: "1px solid var(--kb-border)",
                color: "var(--kb-text-primary)"
              }}>
                {selectedTrade.entryReason}
              </div>
            </div>
            <div>
              <div className="text-xs mb-2" style={{ color: "var(--kb-text-muted)" }}>
                エグジット理由
              </div>
              <div className="p-3 rounded" style={{ 
                background: "var(--kb-bg-elevated)",
                border: "1px solid var(--kb-border)",
                color: "var(--kb-text-primary)"
              }}>
                {selectedTrade.exitReason}
              </div>
            </div>
          </div>
        </div>

        {/* タブナビゲーション */}
        <div className="px-6 pt-6">
          <div className="flex border-b" style={{ borderColor: "var(--kb-border)" }}>
            <button
              onClick={() => setActiveTab('chart')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'chart' ? 'border-[var(--kb-brand)]' : 'border-transparent'
              }`}
              style={{ 
                color: activeTab === 'chart' ? "var(--kb-brand)" : "var(--kb-text-muted)"
              }}
            >
              チャート分析 (4つの時間足)
            </button>
            <button
              onClick={() => setActiveTab('technical')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'technical' ? 'border-[var(--kb-brand)]' : 'border-transparent'
              }`}
              style={{ 
                color: activeTab === 'technical' ? "var(--kb-brand)" : "var(--kb-text-muted)"
              }}
            >
              テクニカル指標分析
            </button>
          </div>
        </div>

        {/* タブコンテンツ */}
        <div className="p-6">
          {activeTab === 'chart' ? (
            <TradeChartAnalysis chartAnalysis={selectedTrade.chartAnalysis} />
          ) : (
            <TradeTechnicalIndicators indicators={selectedTrade.technicalIndicators} />
          )}
        </div>
      </div>
    </div>
  );
}