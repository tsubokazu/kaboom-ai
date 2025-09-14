"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Line,
} from "recharts";
import { Badge, Pill } from "@/components/ui";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useWebSocketNotifications } from "@/hooks/useNotification";
import { ToastContainer } from "@/components/ui/Toast";
import { useNotification } from "@/hooks/useNotification";
import { WebSocketMessage } from "@/stores/websocketStore";
import { useAuthStore } from "@/lib/auth-store";

// Mock data helpers
// 型定義
type StockRow = {
  code: string;
  name: string;
  price: number;
  change: number;
  ai: "BUY" | "SELL" | "HOLD";
  confidence: number;
  updatedAt: Date;
};

type FlashState = {
  t?: number;
};

const makeChartData = () =>
  Array.from({ length: 40 }).map((_, i) => ({
    t: i,
    asset: 100 + Math.sin(i / 3) * 6 + Math.random() * 3,
    bench: 100 + Math.cos(i / 4) * 4,
  }));

const initialRows: StockRow[] = [
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

function useRealtimeNumbers() {
  const [total, setTotal] = useState(12034567);
  const [today, setToday] = useState(23456);
  const [monthly, setMonthly] = useState(345678);
  const [winRate, setWinRate] = useState(0.62);

  // WebSocket接続とポートフォリオ更新の監視
  const { subscribe, isConnected } = useWebSocket({
    autoConnect: true,
    onConnect: () => console.log('Dashboard WebSocket connected'),
    onDisconnect: () => console.log('Dashboard WebSocket disconnected')
  });

  useEffect(() => {
    // WebSocketからポートフォリオ更新を受信
    const unsubscribe = subscribe('portfolio_update', (message: WebSocketMessage) => {
      const { payload } = message;
      if (payload.totalAssets !== undefined) setTotal(payload.totalAssets as number);
      if (payload.todayPL !== undefined) setToday(payload.todayPL as number);
      if (payload.monthlyPL !== undefined) setMonthly(payload.monthlyPL as number);
      if (payload.winRate !== undefined) setWinRate(payload.winRate as number);
    });

    return unsubscribe;
  }, [subscribe]);

  // WebSocket未接続時はモックデータで更新（開発用）
  useEffect(() => {
    if (isConnected) return; // WebSocket接続時はモック無効

    const id = setInterval(() => {
      setTotal((v) => v + Math.round((Math.random() - 0.48) * 4000));
      setToday((v) => v + Math.round((Math.random() - 0.5) * 1200));
      setMonthly((v) => v + Math.round((Math.random() - 0.5) * 3000));
      setWinRate((v) =>
        Math.min(0.85, Math.max(0.35, v + (Math.random() - 0.5) * 0.01)),
      );
    }, 1000);
    return () => clearInterval(id);
  }, [isConnected]);

  return { total, today, monthly, winRate, isConnected };
}

function formatCurrency(n: number) {
  return n.toLocaleString("ja-JP", {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 0,
  });
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function SummaryCards() {
  const { total, today, monthly, winRate, isConnected } = useRealtimeNumbers();
  const Item = ({
    label,
    value,
    sub,
  }: {
    label: string;
    value: string;
    sub?: { text: string; color: string };
  }) => (
    <div className="kb-card p-6">
      <div className="text-sm" style={{ color: "var(--kb-text-muted)" }}>
        {label}
      </div>
      <div
        className="mt-2 text-2xl font-extrabold"
        style={{ color: "var(--kb-text)" }}
      >
        {value}
      </div>
      {sub && (
        <div className="mt-1 text-sm" style={{ color: sub.color }}>
          {sub.text}
        </div>
      )}
    </div>
  );

  const subToday = {
    text: `${today >= 0 ? "+" : ""}${formatCurrency(today)} (${today >= 0 ? "+" : ""}${((today / Math.max(1, total)) * 10000).toFixed(2)}‰)`,
    color: today >= 0 ? "var(--kb-success)" : "var(--kb-error)",
  };
  const subMonthly = {
    text: `${monthly >= 0 ? "+" : ""}${formatCurrency(monthly)}`,
    color: monthly >= 0 ? "var(--kb-success)" : "var(--kb-error)",
  };

  return (
    <div className="space-y-4">
      {/* 接続状態表示 */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
          {isConnected ? 'リアルタイム接続中' : 'オフライン（モックデータ）'}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Item label="総資産額" value={formatCurrency(total)} />
        <Item label="本日の損益" value={formatCurrency(today)} sub={subToday} />
        <Item label="月間損益" value={formatCurrency(monthly)} sub={subMonthly} />
        <Item label="全体勝率" value={pct(winRate)} />
      </div>
    </div>
  );
}

function PortfolioChart() {
  const [period, setPeriod] = useState("1M");
  const [data, setData] = useState(() => makeChartData());

  // Regenerate data when period changes
  useEffect(() => {
    setData(makeChartData());
  }, [period]);

  useEffect(() => {
    const id = setInterval(() => {
      setData((prevData) => {
        if (prevData.length === 0) return makeChartData(); // Fallback for empty data
        
        const last = prevData[prevData.length - 1];
        const next = {
          t: last.t + 1,
          asset: last.asset + (Math.random() - 0.48) * 2,
          bench: last.bench + (Math.random() - 0.5) * 1.2,
        };
        return [...prevData.slice(1), next];
      });
    }, 1200);
    return () => clearInterval(id);
  }, []); // Keep this independent of period

  const periods = ["1D", "1W", "1M", "3M", "1Y", "ALL"];

  return (
    <div className="kb-card p-4">
      <div className="flex items-center justify-between px-2 py-1">
        <div className="font-bold" style={{ color: "var(--kb-text)" }}>
          ポートフォリオ推移
        </div>
        <div className="flex gap-2">
          {periods.map((p) => (
            <Pill key={p} active={period === p} onClick={() => setPeriod(p)}>
              {p}
            </Pill>
          ))}
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorAsset" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor="var(--kb-chart-primary)"
                  stopOpacity={0.35}
                />
                <stop
                  offset="95%"
                  stopColor="var(--kb-chart-primary)"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--kb-border)" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              tick={{ fontSize: 12 }}
              stroke="var(--kb-text-muted)"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke="var(--kb-text-muted)"
              domain={["dataMin-5", "dataMax+5"]}
            />
            <Tooltip contentStyle={{ borderRadius: 8 }} />
            <Area
              type="monotone"
              dataKey="asset"
              stroke="var(--kb-chart-primary)"
              fillOpacity={1}
              fill="url(#colorAsset)"
            />
            <Line
              type="monotone"
              dataKey="bench"
              stroke="var(--kb-chart-benchmark)"
              dot={false}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function RealtimeTable() {
  const [rows, setRows] = useState(initialRows);
  const [sortKey, setSortKey] = useState("updatedAt");
  const [dir, setDir] = useState("desc");
  const [filter, setFilter] = useState("ALL");
  const [modal, setModal] = useState<StockRow | null>(null);
  const [flash, setFlash] = useState<FlashState>({});
  const [mounted, setMounted] = useState(false);

  // WebSocket価格更新の監視
  const { subscribe, isConnected } = useWebSocket({
    autoConnect: true
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    // WebSocketから価格更新を受信
    const unsubscribe = subscribe('price_update', (message: WebSocketMessage) => {
      const { payload } = message;
      if (payload.symbol && payload.price !== undefined) {
        setRows(prevRows => prevRows.map(row => {
          if (row.code === payload.symbol) {
            return {
              ...row,
              price: payload.price as number,
              change: (payload.change as number) || row.change,
              ai: (payload.aiJudgment as StockRow["ai"]) || row.ai,
              confidence: (payload.confidence as number) || row.confidence,
              updatedAt: new Date()
            };
          }
          return row;
        }));
        setFlash({ t: Date.now() });
      }
    });

    return unsubscribe;
  }, [subscribe]);

  useEffect(() => {
    // WebSocket未接続時のモックデータ更新
    if (isConnected) return;

    const id = setInterval(() => {
      setRows((rs) =>
        rs.map((r) => {
          const delta = (Math.random() - 0.5) * 2;
          const newPrice = Math.max(1, r.price + delta);
          const newChange = (Math.random() - 0.5) * 2;
          const aiStates: StockRow["ai"][] = ["BUY", "SELL", "HOLD"];
          const flip: StockRow["ai"] =
            Math.random() < 0.05
              ? aiStates[Math.floor(Math.random() * 3)]
              : r.ai;
          const updated = {
            ...r,
            price: Math.round(newPrice * 100) / 100,
            change: Math.round(newChange * 10) / 10,
            ai: flip,
            updatedAt: new Date(),
          };
          return updated;
        }),
      );
      setFlash({ t: Date.now() });
    }, 1000);
    return () => clearInterval(id);
  }, [isConnected]);

  const display = useMemo(() => {
    let d = [...rows];
    if (filter !== "ALL") d = d.filter((r) => r.ai === filter);
    d.sort((a, b) => {
      const va = a[sortKey as keyof StockRow];
      const vb = b[sortKey as keyof StockRow];
      const s = va > vb ? 1 : va < vb ? -1 : 0;
      return dir === "asc" ? s : -s;
    });
    return d;
  }, [rows, sortKey, dir, filter]);

  const HeaderCell = ({ k, label }: { k: string; label: string }) => (
    <th
      className="px-3 py-2 cursor-pointer select-none"
      onClick={() => {
        if (sortKey === k) setDir(dir === "asc" ? "desc" : "asc");
        else {
          setSortKey(k);
          setDir("asc");
        }
      }}
    >
      <div className="flex items-center gap-1">
        <span>{label}</span>
        {sortKey === k && (
          <span className="text-xs" style={{ color: "var(--kb-text-muted)" }}>
            {dir === "asc" ? "▲" : "▼"}
          </span>
        )}
      </div>
    </th>
  );

  return (
    <div className="kb-card">
      <div className="flex items-center justify-between p-4">
        <div className="font-bold" style={{ color: "var(--kb-text)" }}>
          リアルタイム AI 判断
        </div>
        <div className="flex gap-2">
          {["ALL", "BUY", "SELL", "HOLD"].map((x) => (
            <Pill key={x} active={filter === x} onClick={() => setFilter(x)}>
              {x}
            </Pill>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="kb-table w-full text-sm">
          <thead>
            <tr>
              <HeaderCell k="code" label="銘柄コード" />
              <HeaderCell k="name" label="銘柄名" />
              <HeaderCell k="price" label="現在価格" />
              <HeaderCell k="change" label="前日比" />
              <HeaderCell k="ai" label="AI 判断" />
              <HeaderCell k="confidence" label="信頼度" />
              <HeaderCell k="updatedAt" label="最終更新" />
            </tr>
          </thead>
          <tbody>
            {display.map((r, i) => (
              <tr
                key={r.code}
                className={flash.t && i === 0 ? "kb-flash" : ""}
                onClick={() => setModal(r)}
                style={{ cursor: "pointer" }}
              >
                <td
                  className="px-3 py-2 whitespace-nowrap"
                  style={{ color: "var(--kb-text)" }}
                >
                  {r.code}
                </td>
                <td className="px-3 py-2" style={{ color: "var(--kb-text)" }}>
                  {r.name}
                </td>
                <td
                  className="px-3 py-2 text-right"
                  style={{ color: "var(--kb-text)" }}
                >
                  {r.price.toLocaleString()}
                </td>
                <td
                  className="px-3 py-2 text-right"
                  style={{
                    color:
                      r.change >= 0 ? "var(--kb-success)" : "var(--kb-error)",
                  }}
                >
                  {r.change > 0 ? `+${r.change}` : r.change}%
                </td>
                <td className="px-3 py-2">
                  <Badge
                    variant={
                      r.ai === "BUY" ? "buy" : r.ai === "SELL" ? "sell" : "hold"
                    }
                  >
                    {r.ai}
                  </Badge>
                </td>
                <td className="px-3 py-2">
                  <div className="w-full bg-[var(--kb-bg-elevated)] h-2 rounded-full">
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: `${Math.round(r.confidence * 100)}%`,
                        background: "var(--kb-brand)",
                      }}
                    />
                  </div>
                </td>
                <td
                  className="px-3 py-2 text-right"
                  style={{ color: "var(--kb-text-muted)" }}
                >
                  {mounted ? r.updatedAt.toLocaleTimeString() : "Loading..."}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {modal && (
        <div className="kb-modal-backdrop" onClick={() => setModal(null)}>
          <div
            className="kb-card kb-modal p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <div
                className="text-xl font-bold"
                style={{ color: "var(--kb-text)" }}
              >
                {modal.name} ({modal.code})
              </div>
              <button className="kb-pill" onClick={() => setModal(null)}>
                閉じる
              </button>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div
                className="kb-frame h-40 flex items-center justify-center text-sm"
                style={{ color: "var(--kb-text-muted)" }}
              >
                詳細チャート（モーダル内）
              </div>
              <div>
                <div>
                  AI判断:{" "}
                  <Badge
                    variant={
                      modal.ai === "BUY"
                        ? "buy"
                        : modal.ai === "SELL"
                          ? "sell"
                          : "hold"
                    }
                  >
                    {modal.ai}
                  </Badge>
                </div>
                <div className="mt-2">
                  信頼度: {Math.round(modal.confidence * 100)}%
                </div>
                <div className="mt-2">
                  現在価格: {modal.price.toLocaleString()} 円
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const { toasts, removeToast } = useNotification();
  const { handleWebSocketMessage } = useWebSocketNotifications();
  const { isAuthenticated, checkAuth } = useAuthStore();

  // 認証状態チェック
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // WebSocket通知の処理
  useWebSocket({
    autoConnect: true,
    onMessage: handleWebSocketMessage
  });

  useEffect(() => {
    console.log("Kaboom.ai Dashboard loaded");
  }, []);

  // 認証されていない場合は何も表示しない（middlewareがリダイレクトするため）
  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      <main className="kb-container space-y-6">
        <SummaryCards />
        <PortfolioChart />
        <RealtimeTable />
      </main>

      {/* 通知コンテナ */}
      <ToastContainer
        toasts={toasts}
        onClose={removeToast}
        position="top-right"
      />
    </>
  );
}
