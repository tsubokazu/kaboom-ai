"use client";

import React, { useState, useEffect } from 'react';
import { Search, Play } from 'lucide-react';
import LightweightPriceChart from '@/components/ai/LightweightPriceChart';
import EvidencePanel from '@/components/ai/EvidencePanel';
import TechnicalIndicators from '@/components/ai/TechnicalIndicators';
import { generateMockAIData, generateMockPriceData } from '@/lib/mock-ai-data';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useNotification } from '@/hooks/useNotification';
import { WebSocketMessage } from '@/stores/websocketStore';

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface AIAnalysisPageProps {}

export default function AIAnalysisPage({}: AIAnalysisPageProps) {
  const [selectedSymbol, setSelectedSymbol] = useState('7203'); // トヨタ自動車
  const [searchQuery, setSearchQuery] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  // WebSocket接続とAI分析結果の監視
  const { subscribe, isConnected, send } = useWebSocket({
    autoConnect: true
  });
  
  // 通知システム
  const { showSuccess, showLoading, updateLoadingToast } = useNotification();
  const [priceData, setPriceData] = useState<Array<{
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>>([]);
  const [aiData, setAiData] = useState<{
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
    technicalIndicators: Record<string, unknown>;
    marketSentiment: unknown;
  } | null>(null);

  // WebSocketからAI分析結果を受信
  useEffect(() => {
    const unsubscribe = subscribe('ai_analysis', (message: WebSocketMessage) => {
      const { payload } = message;
      
      if (payload.symbol === selectedSymbol) {
        // AI分析完了
        setAiData((payload.analysisResult as typeof aiData) || generateMockAIData(selectedSymbol));
        setIsAnalyzing(false);
        
        // 成功通知
        showSuccess('AI分析完了', `${selectedSymbol}の分析が完了しました`);
      }
    });

    return unsubscribe;
  }, [subscribe, selectedSymbol, showSuccess]);

  // 価格データの更新を監視
  useEffect(() => {
    const unsubscribe = subscribe('price_update', (message: WebSocketMessage) => {
      const { payload } = message;
      
      if (payload.symbol === selectedSymbol && payload.priceData) {
        // リアルタイム価格データ更新
        setPriceData(payload.priceData as typeof priceData);
      }
    });

    return unsubscribe;
  }, [subscribe, selectedSymbol]);

  // モックデータの生成（WebSocket未接続時）
  useEffect(() => {
    if (isConnected) return; // WebSocket接続時はモック無効

    const mockPriceData = generateMockPriceData(selectedSymbol);
    const mockAiData = generateMockAIData(selectedSymbol);
    setPriceData(mockPriceData);
    setAiData(mockAiData);
  }, [selectedSymbol, isConnected]);

  const handleSymbolSearch = (symbol: string) => {
    setSelectedSymbol(symbol);
    setIsAnalyzing(true);

    // 分析開始通知
    const loadingToastId = showLoading('AI分析実行中', `${symbol}の分析を開始しています...`);

    if (isConnected) {
      // WebSocket経由でAI分析リクエスト送信
      send({
        type: 'ai_analysis',
        payload: {
          symbol: symbol,
          analysisType: 'comprehensive',
          timeframe: '1D'
        }
      });
    } else {
      // WebSocket未接続時のモック処理
      setTimeout(() => {
        const mockAiData = generateMockAIData(symbol);
        setAiData(mockAiData);
        setIsAnalyzing(false);
        
        // 完了通知
        updateLoadingToast(loadingToastId, 'success', 'AI分析完了', `${symbol}の分析が完了しました（モックデータ）`);
      }, 3000);
    }
  };

  const popularSymbols = [
    { code: '7203', name: 'トヨタ自動車' },
    { code: '9984', name: 'ソフトバンクグループ' },
    { code: '6758', name: 'ソニーグループ' },
    { code: '7974', name: '任天堂' },
    { code: '8035', name: '東京エレクトロン' }
  ];

  return (
    <div className="min-h-screen p-4 bg-[var(--kb-bg)]">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* 検索・銘柄選択 */}
        <div className="kb-card p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3 flex-1">
              <Search className="w-5 h-5 text-[var(--kb-text-muted)]" />
              <input
                type="text"
                className="kb-input flex-1"
                placeholder="銘柄コード / 名前を検索 (例: 7203, トヨタ)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchQuery.trim()) {
                    handleSymbolSearch(searchQuery.trim());
                  }
                }}
              />
              <button
                className="kb-btn kb-btn-primary"
                onClick={() => handleSymbolSearch(searchQuery.trim())}
                disabled={!searchQuery.trim() || isAnalyzing}
              >
                <Play className="w-4 h-4 mr-1" />
                分析実行
              </button>
            </div>
            
            {/* 接続状態表示 */}
            <div className="flex items-center gap-2 ml-4">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-xs text-[var(--kb-text-muted)]">
                {isConnected ? 'リアルタイム分析' : 'オフライン'}
              </span>
            </div>
          </div>

          {/* 人気銘柄 */}
          <div>
            <div className="text-sm text-[var(--kb-text-muted)] mb-2">人気銘柄:</div>
            <div className="flex flex-wrap gap-2">
              {popularSymbols.map((symbol) => (
                <button
                  key={symbol.code}
                  className={`px-3 py-1 rounded-full text-sm transition-all ${
                    selectedSymbol === symbol.code
                      ? 'bg-[var(--kb-brand)] text-white'
                      : 'bg-[var(--kb-bg-elevated)] text-[var(--kb-text)] hover:bg-[var(--kb-border)]'
                  }`}
                  onClick={() => handleSymbolSearch(symbol.code)}
                >
                  {symbol.code} {symbol.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* メインコンテンツ */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* チャート領域 */}
          <div className="lg:col-span-3 space-y-4">
            <LightweightPriceChart 
              symbol={selectedSymbol}
              data={priceData}
              isLoading={isAnalyzing}
            />
            
            {/* テクニカル指標 */}
            <TechnicalIndicators 
              indicators={aiData?.technicalIndicators as Record<string, {
                name: string;
                value: number;
                signal: 'BUY' | 'SELL' | 'NEUTRAL';
                status: 'bullish' | 'bearish' | 'neutral';
                description: string;
              }> || {}}
              isLoading={isAnalyzing}
            />
          </div>

          {/* AI判断パネル */}
          <div className="space-y-4">
            <EvidencePanel 
              aiData={aiData}
              isLoading={isAnalyzing}
              symbol={selectedSymbol}
            />
          </div>
        </div>
      </div>
    </div>
  );
}