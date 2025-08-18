// AI分析用のモックデータ生成

export interface AIDecision {
  signal: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  model: string;
  timestamp: Date;
  entryPrice?: number;
  stopLoss?: number;
  takeProfit?: number;
  reasoning: string[];
  risks: string[];
  timeframe: string;
}

export interface TechnicalIndicator {
  name: string;
  value: number;
  signal: 'BUY' | 'SELL' | 'NEUTRAL';
  status: 'bullish' | 'bearish' | 'neutral';
  description: string;
}

export interface PriceData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export function generateMockPriceData(_symbol: string, days: number = 90): PriceData[] {
  const data: PriceData[] = [];
  const now = new Date();
  let currentPrice = 2500 + Math.random() * 1000; // 基準価格

  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    
    // ランダムウォーク with ドリフト
    const drift = 0.001; // 上昇バイアス
    const volatility = 0.02; // ボラティリティ
    const change = (Math.random() - 0.5) * 2 * volatility + drift;
    
    const open = currentPrice;
    const close = open * (1 + change);
    const high = Math.max(open, close) * (1 + Math.random() * 0.01);
    const low = Math.min(open, close) * (1 - Math.random() * 0.01);
    const volume = Math.floor(1000000 + Math.random() * 5000000);

    data.push({
      time: date.toISOString().split('T')[0],
      open: Math.round(open),
      high: Math.round(high),
      low: Math.round(low),
      close: Math.round(close),
      volume
    });

    currentPrice = close;
  }

  return data;
}

export function generateMockAIData(_symbol: string): {
  decision: AIDecision;
  technicalIndicators: Record<string, TechnicalIndicator>;
  marketSentiment: {
    overall: string;
    newsCount: number;
    socialScore: number;
    institutionalFlow: string;
  };
} {
  const signals = ['BUY', 'SELL', 'HOLD'] as const;
  const randomSignal = signals[Math.floor(Math.random() * signals.length)];
  const confidence = 65 + Math.random() * 30; // 65-95%

  const currentPrice = 2500 + Math.random() * 1000;

  const decision: AIDecision = {
    signal: randomSignal,
    confidence: Math.round(confidence),
    model: 'kaboom-v1.5',
    timestamp: new Date(),
    entryPrice: randomSignal !== 'HOLD' ? Math.round(currentPrice) : undefined,
    stopLoss: randomSignal === 'BUY' ? Math.round(currentPrice * 0.95) : 
               randomSignal === 'SELL' ? Math.round(currentPrice * 1.05) : undefined,
    takeProfit: randomSignal === 'BUY' ? Math.round(currentPrice * 1.08) : 
                randomSignal === 'SELL' ? Math.round(currentPrice * 0.92) : undefined,
    reasoning: generateReasoning(randomSignal),
    risks: generateRisks(randomSignal),
    timeframe: '1日-1週間'
  };

  const technicalIndicators: Record<string, TechnicalIndicator> = {
    RSI: {
      name: 'RSI(14)',
      value: 30 + Math.random() * 40,
      signal: Math.random() > 0.5 ? 'BUY' : 'NEUTRAL',
      status: 'neutral',
      description: 'Relative Strength Index - 過買い/過売り判定'
    },
    MACD: {
      name: 'MACD',
      value: -2 + Math.random() * 4,
      signal: randomSignal === 'HOLD' ? 'NEUTRAL' : randomSignal,
      status: randomSignal === 'BUY' ? 'bullish' : randomSignal === 'SELL' ? 'bearish' : 'neutral',
      description: 'Moving Average Convergence Divergence'
    },
    BBANDS: {
      name: 'ボリンジャーバンド',
      value: Math.random() * 100,
      signal: Math.random() > 0.6 ? 'BUY' : 'NEUTRAL',
      status: 'neutral',
      description: 'ボラティリティベースのサポート・レジスタンス'
    },
    MA: {
      name: '移動平均',
      value: Math.random() * 100,
      signal: randomSignal === 'HOLD' ? 'NEUTRAL' : randomSignal,
      status: randomSignal === 'BUY' ? 'bullish' : randomSignal === 'SELL' ? 'bearish' : 'neutral',
      description: '短期/長期移動平均のクロスオーバー'
    },
    VOLUME: {
      name: '出来高',
      value: Math.random() * 100,
      signal: 'BUY',
      status: 'bullish',
      description: '取引量のトレンド分析'
    }
  };

  const marketSentiment = {
    overall: randomSignal,
    newsCount: Math.floor(Math.random() * 10) + 1,
    socialScore: Math.random() * 100,
    institutionalFlow: Math.random() > 0.5 ? 'inflow' : 'outflow'
  };

  return {
    decision,
    technicalIndicators,
    marketSentiment
  };
}

function generateReasoning(signal: 'BUY' | 'SELL' | 'HOLD'): string[] {
  const buyReasons = [
    '上昇トレンドの継続が確認されました',
    'MACDがゴールデンクロスを形成',
    '出来高の増加とともに価格が上昇',
    'サポートラインでの反発を確認',
    '業績好調による長期的な成長期待',
    'セクター全体の上昇トレンド',
    'テクニカル指標の多くが買いシグナル'
  ];

  const sellReasons = [
    '下降トレンドの始まりを示唆',
    'MACDがデッドクロスを形成',
    'レジスタンスラインでの反落',
    '出来高減少とともに価格が下落',
    'オーバーボート状態の修正局面',
    'セクターローテーションの影響',
    'リスクオフの市場環境'
  ];

  const holdReasons = [
    '明確なトレンドが見られません',
    'レンジ相場での様子見が適切',
    '重要な発表待ちの状況',
    'ボラティリティが高く判断困難',
    'テクニカル指標が混在している状況',
    '市場全体の方向感待ち'
  ];

  const reasons = signal === 'BUY' ? buyReasons : 
                  signal === 'SELL' ? sellReasons : holdReasons;
  
  // 3-5個のランダムな理由を選択
  const count = 3 + Math.floor(Math.random() * 3);
  return reasons.sort(() => 0.5 - Math.random()).slice(0, count);
}

function generateRisks(_signal: 'BUY' | 'SELL' | 'HOLD'): string[] {
  const risks = [
    '急激な市場変動の可能性',
    '決算発表による影響',
    '地政学的リスクの高まり',
    '金利変動の影響',
    'セクター特有のリスク要因',
    'ボラティリティの拡大',
    '流動性の低下リスク',
    '外部環境の急変',
    'テクニカル分析の限界',
    '人工知能判断の不確実性'
  ];

  // 2-4個のランダムなリスクを選択
  const count = 2 + Math.floor(Math.random() * 3);
  return risks.sort(() => 0.5 - Math.random()).slice(0, count);
}

// リアルタイム価格更新のシミュレーション
export function generateRealTimePriceUpdate(currentPrice: number): {
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: Date;
} {
  const change = (Math.random() - 0.5) * currentPrice * 0.01; // ±1%の変動
  const newPrice = currentPrice + change;
  const changePercent = (change / currentPrice) * 100;
  const volume = Math.floor(100000 + Math.random() * 500000);

  return {
    price: Math.round(newPrice * 100) / 100,
    change: Math.round(change * 100) / 100,
    changePercent: Math.round(changePercent * 100) / 100,
    volume,
    timestamp: new Date()
  };
}