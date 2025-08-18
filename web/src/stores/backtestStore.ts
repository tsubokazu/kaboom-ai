import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export interface BacktestSettings {
  startDate: string;
  endDate: string;
  initialCapital: number;
  commission: number;
  symbols: string[];
}

// チャート分析データ構造
export interface ChartAnalysisData {
  timeframe: '1m' | '5m' | '1h' | '4h';
  trend: 'bullish' | 'bearish' | 'sideways';
  support: number;
  resistance: number;
  priceData: {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }[];
  signals: {
    type: 'entry' | 'exit';
    price: number;
    time: string;
    reason: string;
  }[];
}

// テクニカル指標データ構造
export interface TechnicalIndicatorData {
  rsi: {
    value: number;
    signal: 'buy' | 'sell' | 'neutral';
    description: string;
  };
  macd: {
    value: number;
    signal: number;
    histogram: number;
    status: 'bullish' | 'bearish';
    description: string;
  };
  bollinger: {
    upper: number;
    middle: number;
    lower: number;
    position: 'upper' | 'middle' | 'lower';
    description: string;
  };
  sma: {
    sma20: number;
    sma50: number;
    trend: 'golden_cross' | 'dead_cross' | 'neutral';
    description: string;
  };
  volume: {
    current: number;
    average: number;
    ratio: number;
    status: 'high' | 'normal' | 'low';
    description: string;
  };
}

export interface BacktestTrade {
  id: string;
  symbol: string;
  type: 'buy' | 'sell';
  quantity: number;
  price: number;
  date: string;
  profit?: number;
  
  // 拡張：取引詳細分析データ
  chartAnalysis: {
    '1m': ChartAnalysisData;
    '5m': ChartAnalysisData;
    '1h': ChartAnalysisData;
    '4h': ChartAnalysisData;
  };
  technicalIndicators: TechnicalIndicatorData;
  entryReason: string;
  exitReason: string;
  confidence: number; // AI判断の信頼度 (0-100)
}

export interface BacktestMetrics {
  finalValue: number;
  totalReturn: number;
  totalReturnPercent: number;
  totalTrades: number;
  winRate: number;
  maxDrawdown: number;
  maxDrawdownPercent: number;
  sharpeRatio: number;
  winTrades: number;
  lossTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
}

export interface BacktestResults {
  trades: BacktestTrade[];
  metrics: BacktestMetrics;
  equityData: { date: string; value: number; drawdown: number }[];
  monthlyReturns: { [key: string]: number };
  isCompleted: boolean;
}

interface BacktestState {
  // Settings
  settings: BacktestSettings;
  updateSettings: (settings: Partial<BacktestSettings>) => void;
  
  // Execution state
  isRunning: boolean;
  progress: number;
  
  // Results
  results: BacktestResults | null;
  
  // 取引詳細表示
  selectedTrade: BacktestTrade | null;
  isTradeDetailOpen: boolean;
  
  // Actions
  startBacktest: () => Promise<void>;
  pauseBacktest: () => void;
  stopBacktest: () => void;
  resetBacktest: () => void;
  
  // 取引詳細関連
  openTradeDetail: (trade: BacktestTrade) => void;
  closeTradeDetail: () => void;
  
  // Export
  exportResults: () => void;
}

const defaultSettings: BacktestSettings = {
  startDate: '2024-01-01',
  endDate: '2024-12-31',
  initialCapital: 1000000,
  commission: 0.1,
  symbols: ['7203', '9984', '6758'],
};

export const useBacktestStore = create<BacktestState>()(
  devtools(
    (set, get) => ({
      // Initial state
      settings: defaultSettings,
      isRunning: false,
      progress: 0,
      results: null,

      // 取引詳細表示の初期状態
      selectedTrade: null,
      isTradeDetailOpen: false,

      // Settings actions
      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),

      // Execution actions
      startBacktest: async () => {
        const { settings } = get();
        set({ isRunning: true, progress: 0, results: null });

        try {
          // モックデータでバックテストをシミュレート
          await simulateBacktest(settings, (progress) => {
            set({ progress });
          });

          // 完了時に結果を生成
          const results = generateMockResults(settings);
          set({ results, isRunning: false, progress: 100 });
        } catch (error) {
          console.error('Backtest failed:', error);
          set({ isRunning: false, progress: 0 });
        }
      },

      pauseBacktest: () => {
        set({ isRunning: false });
      },

      stopBacktest: () => {
        set({ isRunning: false, progress: 0, results: null });
      },

      resetBacktest: () => {
        set({ isRunning: false, progress: 0, results: null });
      },

      // 取引詳細関連のアクション
      openTradeDetail: (trade) => {
        set({ selectedTrade: trade, isTradeDetailOpen: true });
      },

      closeTradeDetail: () => {
        set({ selectedTrade: null, isTradeDetailOpen: false });
      },

      exportResults: () => {
        const { results } = get();
        if (!results) return;

        const csvData = generateCSV(results);
        const blob = new Blob([csvData], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `backtest_results_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      },
    }),
    {
      name: 'backtest-store',
    }
  )
);

// モックバックテストシミュレーション
async function simulateBacktest(
  settings: BacktestSettings,
  onProgress: (progress: number) => void
): Promise<void> {
  const totalSteps = 100;
  
  for (let i = 0; i <= totalSteps; i++) {
    await new Promise(resolve => setTimeout(resolve, 50)); // 5秒で完了
    onProgress((i / totalSteps) * 100);
  }
}

// モック詳細データ生成ヘルパー関数
function generateMockChartAnalysis(timeframe: '1m' | '5m' | '1h' | '4h', symbol: string, basePrice: number): ChartAnalysisData {
  const variation = timeframe === '1m' ? 0.01 : timeframe === '5m' ? 0.02 : timeframe === '1h' ? 0.05 : 0.1;
  const support = basePrice * (1 - variation);
  const resistance = basePrice * (1 + variation);
  
  const trends: ('bullish' | 'bearish' | 'sideways')[] = ['bullish', 'bearish', 'sideways'];
  const trend = trends[Math.floor(Math.random() * trends.length)];
  
  // モック価格データ (直近24ポイント)
  const priceData = Array.from({ length: 24 }, (_, i) => {
    const time = new Date(Date.now() - (24 - i) * 60000);
    const open = basePrice + (Math.random() - 0.5) * basePrice * variation;
    const high = open + Math.random() * basePrice * variation * 0.5;
    const low = open - Math.random() * basePrice * variation * 0.5;
    const close = low + Math.random() * (high - low);
    
    return {
      time: time.toISOString(),
      open: Math.round(open),
      high: Math.round(high),
      low: Math.round(low),
      close: Math.round(close),
      volume: Math.round(Math.random() * 1000000),
    };
  });
  
  return {
    timeframe,
    trend,
    support: Math.round(support),
    resistance: Math.round(resistance),
    priceData,
    signals: [
      {
        type: 'entry',
        price: basePrice,
        time: new Date().toISOString(),
        reason: trend === 'bullish' ? 'ブレイクアウト確認' : trend === 'bearish' ? 'ダウントレンド継続' : 'レンジ下限反発',
      },
    ],
  };
}

function generateMockTechnicalIndicators(symbol: string, basePrice: number): TechnicalIndicatorData {
  const rsiValue = Math.random() * 100;
  const macdValue = (Math.random() - 0.5) * 10;
  
  return {
    rsi: {
      value: Math.round(rsiValue * 100) / 100,
      signal: rsiValue > 70 ? 'sell' : rsiValue < 30 ? 'buy' : 'neutral',
      description: rsiValue > 70 ? '買われすぎ圏' : rsiValue < 30 ? '売られすぎ圏' : '中立圏',
    },
    macd: {
      value: Math.round(macdValue * 100) / 100,
      signal: Math.round((macdValue + (Math.random() - 0.5) * 2) * 100) / 100,
      histogram: Math.round((Math.random() - 0.5) * 5 * 100) / 100,
      status: macdValue > 0 ? 'bullish' : 'bearish',
      description: macdValue > 0 ? 'ゴールデンクロス形成' : 'デッドクロス形成',
    },
    bollinger: {
      upper: Math.round(basePrice * 1.05),
      middle: Math.round(basePrice),
      lower: Math.round(basePrice * 0.95),
      position: Math.random() > 0.5 ? 'upper' : Math.random() > 0.5 ? 'lower' : 'middle',
      description: 'ボリンジャーバンド中央付近',
    },
    sma: {
      sma20: Math.round(basePrice * (0.98 + Math.random() * 0.04)),
      sma50: Math.round(basePrice * (0.95 + Math.random() * 0.1)),
      trend: Math.random() > 0.6 ? 'golden_cross' : Math.random() > 0.5 ? 'dead_cross' : 'neutral',
      description: '移動平均線は上昇トレンド',
    },
    volume: {
      current: Math.round(Math.random() * 1000000),
      average: Math.round(Math.random() * 800000),
      ratio: Math.round((1 + (Math.random() - 0.5) * 0.5) * 100) / 100,
      status: Math.random() > 0.6 ? 'high' : Math.random() > 0.3 ? 'normal' : 'low',
      description: '出来高は平均的',
    },
  };
}

// モック結果生成
function generateMockResults(settings: BacktestSettings): BacktestResults {
  const trades: BacktestTrade[] = [];
  const equityData: { date: string; value: number; drawdown: number }[] = [];
  const monthlyReturns: { [key: string]: number } = {};

  // 12ヶ月分のデータを生成
  let currentValue = settings.initialCapital;
  let maxValue = currentValue;
  
  for (let month = 0; month < 12; month++) {
    const date = new Date(2024, month, 1);
    const monthKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
    
    // ランダムな月次リターンを生成(-10% to +15%)
    const monthlyReturn = (Math.random() * 0.25 - 0.1);
    currentValue *= (1 + monthlyReturn);
    maxValue = Math.max(maxValue, currentValue);
    
    const drawdown = ((maxValue - currentValue) / maxValue) * 100;
    
    equityData.push({
      date: monthKey,
      value: Math.round(currentValue),
      drawdown: -Math.round(drawdown * 100) / 100,
    });
    
    monthlyReturns[monthKey] = Math.round(monthlyReturn * 10000) / 100;
    
    // ランダムにトレードを生成
    if (Math.random() > 0.3) {
      const symbol = settings.symbols[Math.floor(Math.random() * settings.symbols.length)];
      const isWin = Math.random() > 0.4;
      const profit = isWin 
        ? Math.random() * 50000 + 10000 
        : -(Math.random() * 30000 + 5000);
      
      const basePrice = Math.floor(Math.random() * 5000) + 500;
      const tradeType = Math.random() > 0.5 ? 'buy' : 'sell';
      
      // 詳細データ生成
      const chartAnalysis = {
        '1m': generateMockChartAnalysis('1m', symbol, basePrice),
        '5m': generateMockChartAnalysis('5m', symbol, basePrice),
        '1h': generateMockChartAnalysis('1h', symbol, basePrice),
        '4h': generateMockChartAnalysis('4h', symbol, basePrice),
      } as const;
      
      const technicalIndicators = generateMockTechnicalIndicators(symbol, basePrice);
      
      const entryReasons = [
        'ブレイクアウト確認',
        'サポートライン反発',
        'ゴールデンクロス形成',
        'RSI oversold反転',
        'MACD買いシグナル',
        'ボリンジャーバンド下限タッチ',
      ];
      
      const exitReasons = [
        '利確ライン到達',
        '損切りライン到達', 
        'トレンド転換確認',
        'RSI overbought到達',
        'MACD売りシグナル',
        '時間切れクローズ',
      ];
      
      trades.push({
        id: `trade_${month}_${Math.random().toString(36).substr(2, 9)}`,
        symbol,
        type: tradeType,
        quantity: Math.floor(Math.random() * 1000) + 100,
        price: basePrice,
        date: monthKey + '-15',
        profit: Math.round(profit),
        chartAnalysis,
        technicalIndicators,
        entryReason: entryReasons[Math.floor(Math.random() * entryReasons.length)],
        exitReason: exitReasons[Math.floor(Math.random() * exitReasons.length)],
        confidence: Math.floor(Math.random() * 40) + 60, // 60-100の信頼度
      });
    }
  }

  // メトリクス計算
  const totalReturn = currentValue - settings.initialCapital;
  const totalReturnPercent = (totalReturn / settings.initialCapital) * 100;
  const winTrades = trades.filter(t => (t.profit || 0) > 0).length;
  const lossTrades = trades.filter(t => (t.profit || 0) < 0).length;
  const winRate = trades.length > 0 ? (winTrades / trades.length) * 100 : 0;
  const maxDrawdown = Math.min(...equityData.map(d => d.drawdown));
  const maxDrawdownPercent = Math.abs(maxDrawdown);

  const avgWin = winTrades > 0 
    ? trades.filter(t => (t.profit || 0) > 0).reduce((sum, t) => sum + (t.profit || 0), 0) / winTrades 
    : 0;
  const avgLoss = lossTrades > 0 
    ? Math.abs(trades.filter(t => (t.profit || 0) < 0).reduce((sum, t) => sum + (t.profit || 0), 0) / lossTrades)
    : 0;
  const profitFactor = avgLoss > 0 ? avgWin / avgLoss : 0;
  
  // シャープレシオの簡易計算
  const monthlyReturnsArray = Object.values(monthlyReturns);
  const avgReturn = monthlyReturnsArray.reduce((sum, r) => sum + r, 0) / monthlyReturnsArray.length;
  const variance = monthlyReturnsArray.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / monthlyReturnsArray.length;
  const stdDev = Math.sqrt(variance);
  const sharpeRatio = stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(12) : 0; // 年率化

  const metrics: BacktestMetrics = {
    finalValue: Math.round(currentValue),
    totalReturn: Math.round(totalReturn),
    totalReturnPercent: Math.round(totalReturnPercent * 100) / 100,
    totalTrades: trades.length,
    winRate: Math.round(winRate * 100) / 100,
    maxDrawdown: Math.round(Math.abs(maxDrawdown) * settings.initialCapital / 100),
    maxDrawdownPercent: Math.round(maxDrawdownPercent * 100) / 100,
    sharpeRatio: Math.round(sharpeRatio * 1000) / 1000,
    winTrades,
    lossTrades,
    avgWin: Math.round(avgWin),
    avgLoss: Math.round(avgLoss),
    profitFactor: Math.round(profitFactor * 100) / 100,
  };

  return {
    trades,
    metrics,
    equityData,
    monthlyReturns,
    isCompleted: true,
  };
}

// CSV生成
function generateCSV(results: BacktestResults): string {
  const lines = [
    'Date,Symbol,Type,Quantity,Price,Profit',
    ...results.trades.map(trade => 
      `${trade.date},${trade.symbol},${trade.type},${trade.quantity},${trade.price},${trade.profit || 0}`
    ),
    '',
    'Metrics',
    `Final Value,${results.metrics.finalValue}`,
    `Total Return,${results.metrics.totalReturn}`,
    `Total Return %,${results.metrics.totalReturnPercent}`,
    `Win Rate %,${results.metrics.winRate}`,
    `Max Drawdown,${results.metrics.maxDrawdown}`,
    `Sharpe Ratio,${results.metrics.sharpeRatio}`,
  ];
  
  return lines.join('\n');
}