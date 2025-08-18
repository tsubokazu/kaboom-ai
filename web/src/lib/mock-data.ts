// Mock data for development and testing

export interface StockData {
  code: string;
  name: string;
  price: number;
  change: number;
  ai: "BUY" | "SELL" | "HOLD";
  confidence: number;
  updatedAt: Date;
}

export const initialStocks: StockData[] = [
  {
    code: "7203",
    name: "トヨタ",
    price: 3123,
    change: +0.8,
    ai: "BUY",
    confidence: 0.82,
    updatedAt: new Date(),
  },
  {
    code: "6758",
    name: "ソニーG",
    price: 13345,
    change: -0.5,
    ai: "HOLD",
    confidence: 0.54,
    updatedAt: new Date(),
  },
  {
    code: "9984",
    name: "ソフトバンクG",
    price: 7891,
    change: +1.9,
    ai: "SELL",
    confidence: 0.68,
    updatedAt: new Date(),
  },
  {
    code: "6954",
    name: "ファナック",
    price: 46450,
    change: +0.2,
    ai: "BUY",
    confidence: 0.71,
    updatedAt: new Date(),
  },
  {
    code: "8306",
    name: "三菱UFJ",
    price: 1518,
    change: -0.3,
    ai: "HOLD",
    confidence: 0.49,
    updatedAt: new Date(),
  },
];

export interface TradingPlan {
  side: "BUY" | "SELL";
  horizon: string;
  confidence: number;
  model: string;
  changedSince: string;
  entry: number;
  stop: number;
  takeProfit: number;
  sizePct: number;
}

export const mockTradingPlan: TradingPlan = {
  side: "BUY",
  horizon: "1D",
  confidence: 0.78,
  model: "kaboom-v1",
  changedSince: "2時間前に HOLD→BUY",
  entry: 108.2,
  stop: 104.5,
  takeProfit: 114.8,
  sizePct: 0.03,
};

export interface TechnicalIndicator {
  id: string;
  role: "support" | "oppose" | "neutral";
  weight: number;
}

export const mockTechnicalIndicators: TechnicalIndicator[] = [
  { id: "RSI", role: "support", weight: 0.28 },
  { id: "MACD", role: "support", weight: 0.33 },
  { id: "VOL", role: "support", weight: 0.18 },
  { id: "MA25", role: "oppose", weight: 0.12 },
];

export interface BacktestTrade {
  id: string;
  time: string;
  side: "BUY" | "SELL";
  qty: number;
  price: number;
  pnl: number;
}

export function generateMockTrades(count: number = 10): BacktestTrade[] {
  const trades: BacktestTrade[] = [];

  for (let i = 0; i < count; i++) {
    const pnl = (Math.random() - 0.45) * 10000;
    trades.push({
      id: `T-${i + 1}`,
      time: new Date(Date.now() - i * 60000).toLocaleString("ja-JP"),
      side: pnl >= 0 ? "BUY" : "SELL",
      qty: Math.round(1 + Math.random() * 3),
      price: Math.round(100 + Math.random() * 20),
      pnl: Math.round(pnl),
    });
  }

  return trades;
}

export interface User {
  id: string;
  email: string;
  created: string;
  lastLogin: string;
  status: "active" | "suspended";
}

export const mockUsers: User[] = Array.from({ length: 6 }, (_, i) => ({
  id: `U-${1000 + i}`,
  email: `user${i}@kaboom.ai`,
  created: "2025-01-01",
  lastLogin: "2025-08-01",
  status: i % 2 ? "active" : "suspended",
}));
