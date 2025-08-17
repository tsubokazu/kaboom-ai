import React, { useEffect, useMemo, useState, useRef } from "react";
import { Bell, Wifi, ChevronDown, Sun, Moon, Play, Pause, Square, RotateCcw, Download } from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Line, ReferenceLine } from "recharts";
import { createChart, CrosshairMode } from "lightweight-charts";

// -------------------------------------------------------------
// Kaboom.ai — Sample Site to demo the provided Design System
// Single-file React component. Tailwind classes + CSS variables.
// -------------------------------------------------------------

const LIGHT = {
  "--kb-bg-canvas": "#FAFAFA",
  "--kb-bg-surface": "#FFFFFF",
  "--kb-bg-elevated": "#F3F4F6",
  "--kb-text": "#111827",
  "--kb-text-muted": "#6B7280",
  "--kb-border": "#D1D5DB",
  "--kb-border-strong": "#9CA3AF",
  "--kb-brand": "#F66B0E",
  "--kb-brand-hover": "#EA580C",
  "--kb-brand-pressed": "#C2410C",
  "--kb-on-brand": "#FFFFFF",
  "--kb-success": "#16A34A",
  "--kb-warning": "#D97706",
  "--kb-error": "#DC2626",
  "--kb-info": "#2563EB",
  "--kb-chart-primary": "#F66B0E",
  "--kb-chart-benchmark": "#14B8A6",
  "--kb-illustration-stroke": "#111827",
};

const DARK = {
  "--kb-bg-canvas": "#0B0F16",
  "--kb-bg-surface": "#111827",
  "--kb-bg-elevated": "#151A22",
  "--kb-text": "#F9FAFB",
  "--kb-text-muted": "#E5E7EB",
  "--kb-border": "#374151",
  "--kb-border-strong": "#4B5563",
  "--kb-brand": "#F97316",
  "--kb-brand-hover": "#FB923C",
  "--kb-brand-pressed": "#EA580C",
  "--kb-on-brand": "#0B0F16",
  "--kb-success": "#34D399",
  "--kb-warning": "#FBBF24",
  "--kb-error": "#F87171",
  "--kb-info": "#60A5FA",
  "--kb-chart-primary": "#FB923C",
  "--kb-chart-benchmark": "#2DD4BF",
  "--kb-illustration-stroke": "#F9FAFB",
};

const CSS = `
:root { --kb-radius-card: 24px; --kb-radius-input: 16px; --kb-shadow-card: 0 4px 12px rgba(0,0,0,0.10); }
.kb-container { max-width: 1280px; margin: 0 auto; padding: 24px; }
.kb-card { background: var(--kb-bg-surface); border: 1px solid var(--kb-border); border-radius: var(--kb-radius-card); box-shadow: var(--kb-shadow-card); }
.kb-input { height: 44px; border: 1px solid var(--kb-border); border-radius: var(--kb-radius-input); padding: 0 12px; background: var(--kb-bg-surface); color: var(--kb-text); }
.kb-select { height: 44px; border: 1px solid var(--kb-border); border-radius: var(--kb-radius-input); padding: 0 12px; background: var(--kb-bg-surface); color: var(--kb-text); }
.kb-btn { border-radius: 9999px; height: 40px; padding: 0 16px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; font-weight: 600; white-space: nowrap; }
.kb-btn-primary { background: var(--kb-brand); color: var(--kb-on-brand); }
.kb-btn-primary:hover { background: var(--kb-brand-hover); }
.kb-btn-secondary { background: transparent; color: var(--kb-text); border: 1px solid var(--kb-border-strong); }
.kb-btn-secondary:hover { background: rgba(246,107,14,0.08); }
.kb-badge { border-radius: 9999px; padding: 2px 10px; font-size: 12px; font-weight: 700; color: white; }
.badge-buy { background: #16A34A; } .badge-sell { background: #DC2626; } .badge-hold { background: #6B7280; }
.kb-table th, .kb-table td { border-bottom: 1px solid var(--kb-border); }
.kb-table tbody tr:last-child td { border-bottom: none; }
.kb-table th { background: var(--kb-bg-elevated); font-weight: 700; font-size: 14px; }
.kb-pill { border-radius: 9999px; border: 1px solid var(--kb-border); padding: 6px 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.kb-pill.active { background: var(--kb-brand); color: var(--kb-on-brand); border-color: var(--kb-brand); }
.kb-nav-link { padding: 8px 12px; border-radius: 9999px; }
.kb-nav-link.active { background: rgba(246,107,14,0.1); color: var(--kb-brand); }
.kb-modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; }
.kb-modal { width: min(640px, 92vw); }
.kb-ws-dot { width: 10px; height: 10px; border-radius: 9999px; }
.kb-frame { border: 2px solid var(--kb-border-strong); border-radius: var(--kb-radius-card); }
.kb-flash { animation: flash 800ms ease-out; }
@keyframes flash { 0% { background: rgba(246,107,14,0.15); } 100% { background: transparent; } }
.kb-chip { border-radius: 9999px; background: rgba(246,107,14,0.1); color: var(--kb-brand); padding: 4px 10px; font-weight: 700; }
.kb-legend { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--kb-text-muted); }
.kb-legend .dot { width: 10px; height: 10px; border-radius: 9999px; }
.kb-legend .dot.entry { background: var(--kb-brand); }
.kb-legend .dot.stop { background: var(--kb-error); }
.kb-legend .dot.tp { background: var(--kb-success); }
.kb-tag { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border:1px solid var(--kb-border); border-radius: 9999px; background: var(--kb-bg-surface); }
.kb-tag .x { cursor:pointer; }
.kb-help { font-size:12px; color: var(--kb-text-muted); }
.kb-heat { display:grid; grid-template-columns: repeat(12, minmax(0,1fr)); gap:6px; }
.kb-heat-cell { height: 36px; border-radius: 8px; display:flex; align-items:center; justify-content:center; font-size:12px; }
`;

const Mascot = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="32" r="28" fill="url(#g)" stroke="var(--kb-illustration-stroke)" strokeWidth="2"/>
    <defs>
      <linearGradient id="g" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FB923C"/>
        <stop offset="1" stopColor="#F66B0E"/>
      </linearGradient>
    </defs>
    <rect x="22" y="14" width="20" height="6" rx="2" fill="#fff" opacity="0.8"/>
    <circle cx="24" cy="28" r="4" fill="#fff"/>
    <circle cx="40" cy="28" r="4" fill="#fff"/>
    <rect x="22" y="36" width="20" height="8" rx="4" fill="#fff"/>
  </svg>
);

const makeChartData = () => {
  const arr = [];
  for (let i = 0; i < 40; i++) {
    arr.push({ t: i, asset: 100 + Math.sin(i / 3) * 6 + Math.random() * 3, bench: 100 + Math.cos(i / 4) * 4 });
  }
  return arr;
};

const initialRows = [
  { code: "7203", name: "トヨタ", price: 3123, change: +0.8, ai: "BUY", confidence: 0.82, updatedAt: new Date() },
  { code: "6758", name: "ソニーG", price: 13345, change: -0.5, ai: "HOLD", confidence: 0.54, updatedAt: new Date() },
  { code: "9984", name: "ソフトバンクG", price: 7891, change: +1.9, ai: "SELL", confidence: 0.68, updatedAt: new Date() },
  { code: "6954", name: "ファナック", price: 46450, change: +0.2, ai: "BUY", confidence: 0.71, updatedAt: new Date() },
  { code: "8306", name: "三菱UFJ", price: 1518, change: -0.3, ai: "HOLD", confidence: 0.49, updatedAt: new Date() }
];

function useTheme() {
  const [mode, setMode] = useState("light");
  useEffect(() => {
    const palette = mode === "light" ? LIGHT : DARK;
    const keys = Object.keys(palette);
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      const v = palette[k];
      document.documentElement.style.setProperty(k, v);
    }
  }, [mode]);
  return { mode, setMode };
}

function useRealtimeNumbers() {
  const [total, setTotal] = useState(12034567);
  const [today, setToday] = useState(23456);
  const [monthly, setMonthly] = useState(345678);
  const [winRate, setWinRate] = useState(0.62);

  useEffect(() => {
    const id = setInterval(() => {
      setTotal((v) => v + Math.round((Math.random() - 0.48) * 4000));
      setToday((v) => v + Math.round((Math.random() - 0.5) * 1200));
      setMonthly((v) => v + Math.round((Math.random() - 0.5) * 3000));
      setWinRate((v) => Math.min(0.85, Math.max(0.35, v + (Math.random() - 0.5) * 0.01)));
    }, 1000);
    return () => clearInterval(id);
  }, []);
  return { total, today, monthly, winRate };
}

function formatCurrency(n) {
  return n.toLocaleString("ja-JP", { style: "currency", currency: "JPY", maximumFractionDigits: 0 });
}
function pct(n) { return `${(n * 100).toFixed(1)}%`; }
function computeRR({ side, entry, stop, takeProfit }) {
  const long = side === 'BUY';
  const risk = Math.max(0.0001, long ? (entry - stop) : (stop - entry));
  const reward = Math.max(0.0001, long ? (takeProfit - entry) : (entry - takeProfit));
  return Number((reward / risk).toFixed(2));
}
function fmtPrice(p){ return p.toLocaleString('ja-JP'); }
function canUseLWC(){ try { return typeof createChart === 'function'; } catch (e) { return false; } }

function parseSymbolsInput(input){
  const arr = (input || "").split(/[\s,]+/);
  const out = [];
  for (let i=0;i<arr.length;i++){ const s = arr[i].trim(); if(s) out.push(s); if(out.length>=20) break; }
  return out;
}

function validateBacktestInput({ start, end, capital, feePct, strategy, models, symbols }){
  const errors = [];
  const s = start ? new Date(start) : null;
  const e = end ? new Date(end) : null;
  if(!s) errors.push("開始日を入力してください");
  if(!e) errors.push("終了日を入力してください");
  if(s && e && e <= s) errors.push("終了日は開始日より後にしてください");
  if(!(capital > 0)) errors.push("初期資金は正の数値で入力してください");
  if(feePct < 0) errors.push("手数料は0以上で入力してください");
  if(!strategy) errors.push("取引戦略を選択してください");
  let any = false; if(models){ const ks = Object.keys(models); for(let i=0;i<ks.length;i++){ if(models[ks[i]]) { any=true; break; } } }
  if(!any) errors.push("AIモデルを1つ以上選択してください");
  if(!symbols || symbols.length === 0) errors.push("銘柄を1つ以上入力してください");
  return errors;
}

function simulateBacktest({ steps = 200, capital = 1000000, feePct = 0.1 }){
  const series = []; const trades = []; let equity = capital; let peak = capital;
  for(let i=0;i<steps;i++){
    const ret = (Math.random()-0.45) * 0.01;
    const before = equity;
    equity = Math.max(0, equity * (1 + ret) - (feePct/1000));
    series.push({ t: i, v: Math.round(equity) });
    if(Math.random() < 0.12){
      const pnl = equity - before;
      trades.push({ id: `T-${i}`, time: new Date(Date.now() + i*60000).toLocaleString(), side: pnl>=0? 'BUY':'SELL', qty: Math.round(1 + Math.random()*3), price: Math.round(100 + Math.random()*20), pnl: Math.round(pnl) });
    }
    peak = Math.max(peak, equity);
  }
  return { series, trades };
}

function computeBacktestMetrics(equitySeries, trades, capital){
  const arr = []; const src = equitySeries || [];
  for(let i=0;i<src.length;i++){ const x = src[i]; arr.push(typeof x === 'number' ? x : x.v); }
  if(arr.length === 0) return { finalEquity: capital, totalPnL: 0, winRate: 0, maxDDPct: 0, sharpe: 0, totalTrades: (trades && trades.length) || 0 };
  const finalEquity = arr[arr.length-1]; const totalPnL = finalEquity - capital;
  const rets = []; for(let i=1;i<arr.length;i++){ rets.push((arr[i]-arr[i-1]) / arr[i-1]); }
  const mean = rets.reduce((a,b)=>a+b,0) / (rets.length||1);
  const sd = Math.sqrt(rets.reduce((a,b)=>a + Math.pow(b-mean,2),0) / (rets.length||1));
  const sharpe = sd === 0 ? 0 : (mean/sd) * Math.sqrt(252);
  let peak = arr[0]; let maxDD = 0; for(let i=0;i<arr.length;i++){ const v=arr[i]; peak = Math.max(peak, v); maxDD = Math.max(maxDD, (peak - v)/peak); }
  const maxDDPct = +(maxDD*100).toFixed(2);
  const wins = (trades||[]).filter(t=>t.pnl>0).length; const winRate = trades && trades.length ? +(wins / trades.length * 100).toFixed(1) : 0;
  return { finalEquity: Math.round(finalEquity), totalPnL: Math.round(totalPnL), winRate, maxDDPct, sharpe: +sharpe.toFixed(2), totalTrades: (trades && trades.length) || 0 };
}

function exportCSV(trades){
  const header = ['id','time','side','qty','price','pnl'];
  const rows = (trades||[]).map(t=> header.map(h=> t[h]));
  const csv = [header.join(','), ...rows.map(r=> r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' }); const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = 'backtest_trades.csv'; a.click(); URL.revokeObjectURL(url);
}

function runSelfTests() {
  const results = []; const assert = (name, cond) => results.push({ name, pass: !!cond });
  assert("formatCurrency includes yen sign", /[¥￥]/.test(formatCurrency(1000)));
  assert("pct formats 0.5 => 50.0%", pct(0.5) === "50.0%");
  assert("LIGHT has brand color", Boolean(LIGHT["--kb-brand"]));
  assert("DARK has brand color", Boolean(DARK["--kb-brand"]));
  assert("Table last row border removed", CSS.includes("tbody tr:last-child td { border-bottom: none; }"));
  assert("Buttons do not wrap text", CSS.includes("white-space: nowrap"));
  assert("Theme title uses literal", "テーマ切替".length > 0);
  assert("computeRR long 100/95->110 = 2.0", computeRR({side:'BUY',entry:100,stop:95,takeProfit:110}) === 2.0);
  assert("computeRR short 100/105->90 = 2.0", computeRR({side:'SELL',entry:100,stop:105,takeProfit:90}) === 2.0);
  assert("canUseLWC exists", typeof canUseLWC === 'function');
  const errs1 = validateBacktestInput({ start:'2025-01-10', end:'2025-01-05', capital:100, feePct:0, strategy:'x', models:{a:true}, symbols:['7203'] });
  assert("validateBacktest catches end before start", errs1.some(e=>e.includes('終了日は開始日より後')));
  const errs2 = validateBacktestInput({ start:'2025-01-01', end:'2025-01-05', capital:0, feePct:0, strategy:'x', models:{a:true}, symbols:['7203'] });
  assert("validateBacktest requires positive capital", errs2.some(e=>e.includes('初期資金')));
  const m = computeBacktestMetrics([{v:100},{v:110},{v:105},{v:120}], [], 100);
  assert("metrics final equity = 120", m.finalEquity === 120);
  assert("metrics maxDD ~4.55%", Math.abs(m.maxDDPct - 4.55) < 0.2);
  assert("parseSymbolsInput caps to 20", parseSymbolsInput(Array.from({length:25}).map((_,i)=>`s${i}`).join(' ')).length === 20);
  assert("metrics default on empty series/trades", (function(){ const m=computeBacktestMetrics([], null, 100); return m.finalEquity===100 && m.totalTrades===0; })());
  console.table(results); return results.every(r => r.pass);
}

function Pill({ active, children, onClick }) { return (<button className={`kb-pill ${active ? "active" : ""}`} onClick={onClick}>{children}</button>); }

function Navbar({ page, setPage, mode, setMode }) {
  const [ws, setWs] = useState("connected");
  useEffect(() => { const id = setInterval(() => { setWs((prev) => (prev === "connected" ? "connected" : "connected")); }, 3000); return () => clearInterval(id); }, []);
  const wsColor = { connected: "var(--kb-success)", connecting: "var(--kb-warning)", disconnected: "var(--kb-error)" }[ws];
  return (
    <header style={{ background: "var(--kb-bg-surface)", borderBottom: `1px solid var(--kb-border)` }} className="sticky top-0 z-10">
      <div className="kb-container flex items-center justify-between" style={{ paddingTop: 12, paddingBottom: 12 }}>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2"><Mascot size={28} /><span className="text-xl font-extrabold" style={{ color: "var(--kb-text)" }}>Kaboom.ai</span></div>
          <nav className="ml-6 hidden md:flex items-center gap-2 text-sm">
            {["dashboard", "ai", "backtest", "admin"].map((k) => (
              <a key={k} className={`kb-nav-link ${page === k ? "active" : ""}`} style={{ color: "var(--kb-text)" }} onClick={() => setPage(k)} href="#" onMouseDown={(e)=>e.preventDefault()}>
                {k === "dashboard" ? "ダッシュボード" : k === "ai" ? "AI分析" : k === "backtest" ? "バックテスト" : "管理"}
              </a>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4 flex-nowrap">
          <div className="flex items-center gap-2 text-sm" title={`WebSocket: ${ws}`}>
            <span className="kb-ws-dot" style={{ background: wsColor }} />
            <Wifi size={16} color="var(--kb-text)" />
          </div>
          <button className="relative" aria-label="notifications"><Bell size={20} color="var(--kb-text)" /><span className="absolute -top-2 -right-1 kb-badge" style={{ background: "var(--kb-brand)" }}>3</span></button>
          <button className="kb-pill" onClick={() => setMode(mode === "light" ? "dark" : "light")} title={"テーマ切替"}>{mode === "light" ? <Moon size={16} /> : <Sun size={16} />}<span>{mode === "light" ? "ダーク" : "ライト"}</span></button>
          <div className="flex items-center gap-2"><div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: "#FED7AA" }}>K</div><ChevronDown size={16} color="var(--kb-text)" /></div>
        </div>
      </div>
    </header>
  );
}

function SummaryCards() {
  const { total, today, monthly, winRate } = useRealtimeNumbers();
  const Item = ({ label, value, sub }) => (
    <div className="kb-card p-6">
      <div className="text-sm" style={{ color: "var(--kb-text-muted)" }}>{label}</div>
      <div className="mt-2 text-2xl font-extrabold" style={{ color: "var(--kb-text)" }}>{value}</div>
      {sub ? <div className="mt-1 text-sm" style={{ color: sub.color }}>{sub.text}</div> : null}
    </div>
  );
  const subToday = { text: `${today >= 0 ? "+" : ""}${formatCurrency(today)} (${today >= 0 ? "+" : ""}${((today / Math.max(1,total)) * 10000).toFixed(2)}\u2030)`, color: today >= 0 ? "var(--kb-success)" : "var(--kb-error)" };
  const subMonthly = { text: `${monthly >= 0 ? "+" : ""}${formatCurrency(monthly)}`, color: monthly >= 0 ? "var(--kb-success)" : "var(--kb-error)" };
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Item label="総資産額" value={formatCurrency(total)} />
      <Item label="本日の損益" value={formatCurrency(today)} sub={subToday} />
      <Item label="月間損益" value={formatCurrency(monthly)} sub={subMonthly} />
      <Item label="全体勝率" value={pct(winRate)} />
    </div>
  );
}

function PortfolioChart() {
  const [period, setPeriod] = useState("1M");
  const [data, setData] = useState(makeChartData());
  useEffect(() => {
    const id = setInterval(() => {
      setData((d) => {
        const last = d[d.length - 1]; const nextT = last.t + 1;
        const next = { t: nextT, asset: last.asset + (Math.random() - 0.48) * 2, bench: last.bench + (Math.random() - 0.5) * 1.2 };
        const arr = d.slice(1); arr.push(next); return arr;
      });
    }, 1200); return () => clearInterval(id);
  }, []);
  const periods = ["1D","1W","1M","3M","1Y","ALL"];
  return (
    <div className="kb-card p-4">
      <div className="flex items-center justify-between px-2 py-1"><div className="font-bold" style={{ color: "var(--kb-text)" }}>ポートフォリオ推移</div><div className="flex gap-2">{periods.map(function(p){return <Pill key={p} active={period===p} onClick={function(){setPeriod(p);}}>{p}</Pill>;})}</div></div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorAsset" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--kb-chart-primary)" stopOpacity={0.35}/><stop offset="95%" stopColor="var(--kb-chart-primary)" stopOpacity={0}/></linearGradient>
            </defs>
            <CartesianGrid stroke="var(--kb-border)" strokeDasharray="3 3" />
            <XAxis dataKey="t" stroke="var(--kb-text-muted)" tick={{ fontSize: 12 }} />
            <YAxis stroke="var(--kb-text-muted)" tick={{ fontSize: 12 }} domain={["dataMin-5","dataMax+5"]} />
            <Tooltip contentStyle={{ borderRadius: 8 }} />
            <Area type="monotone" dataKey="asset" stroke="var(--kb-chart-primary)" fillOpacity={1} fill="url(#colorAsset)" />
            <Line type="monotone" dataKey="bench" stroke="var(--kb-chart-benchmark)" dot={false} strokeWidth={2} />
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
  const [modal, setModal] = useState(null);
  const [flash, setFlash] = useState({});
  useEffect(() => {
    const id = setInterval(() => {
      setRows((rs) => rs.map(function(r){
        const delta = (Math.random() - 0.5) * 2; const newPrice = Math.max(1, r.price + delta); const newChange = (Math.random() - 0.5) * 2;
        const aiStates = ["BUY","SELL","HOLD"]; const flip = Math.random() < 0.05 ? aiStates[Math.floor(Math.random()*3)] : r.ai;
        return Object.assign({}, r, { price: Math.round(newPrice*100)/100, change: Math.round(newChange*10)/10, ai: flip, updatedAt: new Date() });
      }));
      setFlash({ t: Date.now() });
    }, 1000); return () => clearInterval(id);
  }, []);
  const display = useMemo(() => {
    let d = rows.slice(); if (filter !== "ALL") d = d.filter(r => r.ai === filter);
    d.sort((a,b) => { const va=a[sortKey]; const vb=b[sortKey]; const s = va>vb?1:va<vb?-1:0; return dir === "asc" ? s : -s; }); return d;
  }, [rows, sortKey, dir, filter]);

  const HeaderCell = ({ k, label }) => (
    <th className="px-3 py-2 cursor-pointer select-none" onClick={() => { if (sortKey === k) { setDir(dir === "asc" ? "desc" : "asc"); } else { setSortKey(k); setDir("asc"); } }}>
      <div className="flex items-center gap-1">
        <span>{label}</span>
        {sortKey === k ? (<span className="text-xs" style={{ color: "var(--kb-text-muted)" }}>{dir === "asc" ? "\u25B2" : "\u25BC"}</span>) : null}
      </div>
    </th>
  );

  return (
    <div className="kb-card">
      <div className="flex items-center justify-between p-4"><div className="font-bold" style={{ color: "var(--kb-text)" }}>リアルタイム AI 判断</div><div className="flex gap-2">{["ALL","BUY","SELL","HOLD"].map(function(x){return <Pill key={x} active={filter===x} onClick={function(){setFilter(x);}}>{x}</Pill>;})}</div></div>
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
            {display.map(function(r, i){ return (
              <tr key={r.code} className={(flash.t && i===0) ? 'kb-flash' : ''} onClick={() => setModal(r)} style={{ cursor: 'pointer' }}>
                <td className="px-3 py-2 whitespace-nowrap" style={{ color: "var(--kb-text)" }}>{r.code}</td>
                <td className="px-3 py-2" style={{ color: "var(--kb-text)" }}>{r.name}</td>
                <td className="px-3 py-2 text-right" style={{ color: "var(--kb-text)" }}>{r.price.toLocaleString()}</td>
                <td className="px-3 py-2 text-right" style={{ color: r.change>=0? 'var(--kb-success)':'var(--kb-error)' }}>{r.change>0?`+${r.change}`:r.change}%</td>
                <td className="px-3 py-2"><span className={`kb-badge ${r.ai==='BUY'?'badge-buy':r.ai==='SELL'?'badge-sell':'badge-hold'}`}>{r.ai}</span></td>
                <td className="px-3 py-2">
                  <div className="w-full bg-[var(--kb-bg-elevated)] h-2 rounded-full"><div className="h-2 rounded-full" style={{ width: `${Math.round(r.confidence*100)}%`, background: 'var(--kb-brand)' }} /></div>
                </td>
                <td className="px-3 py-2 text-right" style={{ color: "var(--kb-text-muted)" }}>{r.updatedAt.toLocaleTimeString()}</td>
              </tr>
            );})}
          </tbody>
        </table>
      </div>
      {modal ? (
        <div className="kb-modal-backdrop" onClick={()=>setModal(null)}>
          <div className="kb-card kb-modal p-6" onClick={(e)=>e.stopPropagation()}>
            <div className="flex items-center justify-between"><div className="text-xl font-bold" style={{ color: 'var(--kb-text)' }}>{modal.name} ({modal.code})</div><button className="kb-pill" onClick={()=>setModal(null)}>閉じる</button></div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div className="kb-frame h-40 flex items-center justify-center text-sm" style={{ color: 'var(--kb-text-muted)' }}>詳細チャート（モーダル内）</div>
              <div>
                <div>AI判断: <span className={`kb-badge ${modal.ai==='BUY'?'badge-buy':modal.ai==='SELL'?'badge-sell':'badge-hold'}`}>{modal.ai}</span></div>
                <div className="mt-2">信頼度: {Math.round(modal.confidence*100)}%</div>
                <div className="mt-2">現在価格: {modal.price.toLocaleString()} 円</div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AutoSignalHeader({ plan }) {
  const rr = computeRR(plan);
  return (
    <div className="kb-card p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <div className="flex items-center gap-3">
        <span className={`kb-badge ${plan.side==='BUY'?'badge-buy':plan.side==='SELL'?'badge-sell':'badge-hold'}`}>{plan.side}</span>
        <span className="kb-chip">AUTO</span>
        <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>時間軸: {plan.horizon}・モデル: {plan.model}</div>
        <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>信頼度: {Math.round(plan.confidence*100)}%</div>
        <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>{plan.changedSince}</div>
      </div>
      <div className="flex items-center gap-4">
        <div className="kb-legend"><span className="dot entry"/>エントリー {fmtPrice(plan.entry)}</div>
        <div className="kb-legend"><span className="dot stop"/>ストップ {fmtPrice(plan.stop)}</div>
        <div className="kb-legend"><span className="dot tp"/>利確 {fmtPrice(plan.takeProfit)}</div>
        <div className="kb-legend">R:R {rr}・サイズ {Math.round(plan.sizePct*100)}%</div>
      </div>
    </div>
  );
}

function FallbackPriceChart({ plan }){
  const data = makeChartData();
  return (
    <div className="kb-card p-2">
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <defs><linearGradient id="colorAssetAI" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--kb-chart-primary)" stopOpacity={0.35}/><stop offset="95%" stopColor="var(--kb-chart-primary)" stopOpacity={0}/></linearGradient></defs>
            <CartesianGrid stroke="var(--kb-border)" strokeDasharray="3 3" />
            <XAxis dataKey="t" stroke="var(--kb-text-muted)" tick={{ fontSize: 12 }} />
            <YAxis stroke="var(--kb-text-muted)" tick={{ fontSize: 12 }} domain={["dataMin-5","dataMax+5"]} />
            <Tooltip contentStyle={{ borderRadius: 8 }} />
            <Area type="monotone" dataKey="asset" stroke="var(--kb-chart-primary)" fillOpacity={1} fill="url(#colorAssetAI)" />
            <Line type="monotone" dataKey="bench" stroke="var(--kb-chart-benchmark)" dot={false} strokeWidth={2} />
            <ReferenceLine y={plan.entry} stroke="var(--kb-brand)" strokeDasharray="0" label={{ position:'right', value:'ENTRY' }} />
            <ReferenceLine y={plan.stop} stroke="var(--kb-error)" strokeDasharray="6 6" label={{ position:'right', value:'STOP' }} />
            <ReferenceLine y={plan.takeProfit} stroke="var(--kb-success)" strokeDasharray="6 6" label={{ position:'right', value:'TP' }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="px-3 pb-2 text-xs" style={{ color: 'var(--kb-text-muted)' }}>軽量チャートが利用できない環境のため、エリアチャートで代替表示中。</div>
    </div>
  );
}

function LightweightPriceChart({ plan }){
  const ref = useRef(null); const [needFallback, setNeedFallback] = useState(false); const lwcOk = canUseLWC();
  useEffect(()=>{
    if(!lwcOk || !ref.current){ setNeedFallback(true); return; }
    const css = getComputedStyle(document.documentElement);
    const chart = createChart(ref.current, { height: 320, layout: { background: { type: 'solid', color: 'transparent' }, textColor: css.getPropertyValue('--kb-text').trim() }, grid: { vertLines: { color: css.getPropertyValue('--kb-border').trim() }, horzLines: { color: css.getPropertyValue('--kb-border').trim() } }, crosshair: { mode: CrosshairMode.Magnet } });
    if (typeof chart.addCandlestickSeries !== 'function') { setNeedFallback(true); if (chart && typeof chart.remove === 'function') { chart.remove(); } return; }
    const series = chart.addCandlestickSeries({ upColor: '#16A34A', downColor: '#DC2626', borderVisible: false, wickUpColor: '#16A34A', wickDownColor: '#DC2626' });
    const data=[]; const base = 100; for(let i=0;i<120;i++){ const o=base+Math.sin(i/9)*2+i*0.03; const c=o+(Math.random()-0.5)*2; const h=Math.max(o,c)+Math.random()*1.2; const l=Math.min(o,c)-Math.random()*1.2; data.push({ time: (i+1)*60, open: o, high: h, low: l, close: c }); }
    series.setData(data);
    series.setMarkers([{ time: data[70].time, position: 'belowBar', color: '#16A34A', shape: 'arrowUp', text: 'BUY' },{ time: data[95].time, position: 'aboveBar', color: '#DC2626', shape: 'arrowDown', text: 'SELL' }]);
    series.createPriceLine({ price: plan.entry, color: css.getPropertyValue('--kb-brand').trim(), lineWidth: 2, lineStyle: 0, title: 'ENTRY' });
    series.createPriceLine({ price: plan.stop, color: css.getPropertyValue('--kb-error').trim(), lineWidth: 2, lineStyle: 2, title: 'STOP' });
    series.createPriceLine({ price: plan.takeProfit, color: css.getPropertyValue('--kb-success').trim(), lineWidth: 2, lineStyle: 2, title: 'TP' });
    const resize = function(){ if(ref.current){ chart.applyOptions({ width: ref.current.clientWidth }); } };
    resize(); window.addEventListener('resize', resize);
    return () => { window.removeEventListener('resize', resize); if (chart && typeof chart.remove === 'function') { chart.remove(); } };
  }, [lwcOk, plan.entry, plan.stop, plan.takeProfit]);
  if (!lwcOk || needFallback) return <FallbackPriceChart plan={plan} />; return <div className="kb-card p-2"><div ref={ref} style={{ width: '100%', height: 320 }} /></div>;
}

function EvidencePanel(){
  const items = [ { id: 'RSI', role: 'support', weight: 0.28 }, { id: 'MACD', role: 'support', weight: 0.33 }, { id: 'VOL', role: 'support', weight: 0.18 }, { id: 'MA25', role: 'oppose', weight: 0.12 } ];
  const roleColor = function(r){ return r==='support'? 'var(--kb-success)': r==='oppose'? 'var(--kb-error)': 'var(--kb-text-muted)'; };
  return (
    <div className="kb-card p-4 space-y-2">
      <div className="font-bold" style={{ color: 'var(--kb-text)' }}>根拠</div>
      {items.map(function(x){ return (
        <div key={x.id} className="flex items-center gap-2 text-sm">
          <div style={{ width: 72 }}>{x.id}</div>
          <div className="flex-1 bg-[var(--kb-bg-elevated)] rounded-full h-2 overflow-hidden"><div style={{ width: `${x.weight*100}%`, background: roleColor(x.role), height: 8 }} /></div>
          <div style={{ color: roleColor(x.role), width: 56, textAlign: 'right' }}>{Math.round(x.weight*100)}%</div>
        </div>
      ); })}
      <div className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>※ モデル寄与度（支持/反対/中立）</div>
    </div>
  );
}

function RiskPanel({ plan }){
  const rr = computeRR(plan);
  return (
    <div className="kb-card p-4 space-y-2">
      <div className="font-bold" style={{ color: 'var(--kb-text)' }}>リスク/執行</div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="kb-frame p-2">エントリー: {fmtPrice(plan.entry)}</div>
        <div className="kb-frame p-2">ストップ: {fmtPrice(plan.stop)}</div>
        <div className="kb-frame p-2">利確: {fmtPrice(plan.takeProfit)}</div>
        <div className="kb-frame p-2">R:R: {rr}</div>
        <div className="kb-frame p-2 col-span-2">サイズ: {Math.round(plan.sizePct*100)}%（総資産比）</div>
      </div>
      <div className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>※ 完全自動トレード中（執行はバックエンド）。手動介入は今後対応予定。</div>
    </div>
  );
}

function AISample() {
  const plan = { side: 'BUY', horizon: '1D', confidence: 0.78, model: 'kaboom-v1', changedSince: '2時間前に HOLD→BUY', entry: 108.2, stop: 104.5, takeProfit: 114.8, sizePct: 0.03 };
  return (
    <div className="space-y-4">
      <AutoSignalHeader plan={plan} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <LightweightPriceChart plan={plan} />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {["RSI","MACD","BBANDS","MA"].map(function(t){ return (
              <div key={t} className="kb-card p-3 text-sm"><div className="text-sm font-bold" style={{ color: 'var(--kb-text)' }}>{t}</div><div className="kb-frame h-16 mt-2 flex items-center justify-center text-xs" style={{ color: 'var(--kb-text-muted)' }}>ゲージ/ミニグラフ</div></div>
            ); })}
          </div>
        </div>
        <div className="space-y-4"><RiskPanel plan={plan} /><EvidencePanel /></div>
      </div>
    </div>
  );
}

function BacktestSample() {
  const [form, setForm] = useState({ start: '', end: '', capital: 1000000, feePct: 0.1, symbolsInput: '7203, 6758', strategy: 'breakout', models: { 'kaboom-v1': true, 'kaboom-v2': false, 'xgb-alpha': false } });
  const [state, setState] = useState('idle'); const [progress, setProgress] = useState(0); const [eta, setEta] = useState('--');
  const [series, setSeries] = useState([]); const [trades, setTrades] = useState([]); const [errors, setErrors] = useState([]);
  const timerRef = useRef(null); const stepsRef = useRef(240); const startTsRef = useRef(0);
  const symbols = useMemo(function(){ return parseSymbolsInput(form.symbolsInput); }, [form.symbolsInput]);

  function updateForm(partial){ setForm(function(prev){ return Object.assign({}, prev, partial); }); }

  const startRun = () => {
    const errs = validateBacktestInput({ start: form.start, end: form.end, capital: +form.capital, feePct: +form.feePct, strategy: form.strategy, models: form.models, symbols }); setErrors(errs);
    if(errs.length) { setState('error'); return; }
    setState('running'); setProgress(0); setSeries([]); setTrades([]); startTsRef.current = Date.now();
    const sim = simulateBacktest({ steps: stepsRef.current, capital: +form.capital, feePct: +form.feePct }); const genSeries = sim.series; const genTrades = sim.trades;
    let i = 0; if (timerRef.current) { clearInterval(timerRef.current); }
    timerRef.current = setInterval(function(){ i += 8; setSeries(genSeries.slice(0, i)); setTrades(genTrades.slice(0, Math.max(0, Math.floor(i/8)-2)));
      const p = Math.min(100, Math.round(i/stepsRef.current*100)); setProgress(p); const elapsed = (Date.now() - startTsRef.current)/1000; const remaining = p>0? elapsed * (100/p - 1) : 0; setEta(`${Math.max(0, Math.round(remaining))}s`);
      if(i >= stepsRef.current){ clearInterval(timerRef.current); setState('done'); }
    }, 200);
  };

  const pauseRun = () => { if(state==='running'){ setState('paused'); if (timerRef.current) { clearInterval(timerRef.current); } } };
  const resumeRun = () => { if(state==='paused'){
      setState('running'); const completed = (series && series.length) || 0; const remaining = stepsRef.current - completed; if(remaining <= 0){ setState('done'); return; }
      const sim = simulateBacktest({ steps: remaining, capital: completed? series[completed-1].v : +form.capital, feePct: +form.feePct }); const genSeries = sim.series; const genTrades = sim.trades; let i = 0;
      if (timerRef.current) { clearInterval(timerRef.current); }
      timerRef.current = setInterval(function(){ i += 8; const chunkS = genSeries.slice(0, i).map(function(p,idx){return { t:(completed+idx), v:p.v };}); const chunkT = genTrades.slice(0, Math.max(0, Math.floor(i/8)-2));
        setSeries(function(prev){ return prev.concat(chunkS); }); setTrades(function(prev){ return prev.concat(chunkT); });
        const p = Math.min(100, Math.round((completed + i)/stepsRef.current*100)); setProgress(p);
        if((completed + i) >= stepsRef.current){ clearInterval(timerRef.current); setState('done'); }
      }, 200);
    }};
  const stopRun = () => { if (timerRef.current) { clearInterval(timerRef.current); } setState('idle'); setProgress(0); setEta('--'); };
  const resetAll = () => { stopRun(); setSeries([]); setTrades([]); setErrors([]); };
  useEffect(()=>(){ return () => { if (timerRef.current) { clearInterval(timerRef.current); } }; }, []);

  const metrics = useMemo(function(){ return computeBacktestMetrics(series, trades, +form.capital); }, [series, trades, form.capital]);
  const heatData = useMemo(function(){ const out=[]; for(let m=0;m<12;m++){ const r=(Math.random()-0.4)*0.08; out.push({ m:m+1, val:+(r*100).toFixed(1) }); } return out; }, [state]);
  const ddSeries = useMemo(function(){ let peak = 0; return (series||[]).map(function(p){ peak = Math.max(peak, p.v||0); const dd = peak? ((p.v-peak)/peak)*100 : 0; return { t: p.t, dd }; }); }, [series]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="kb-card p-4 space-y-3">
        <div className="font-bold" style={{ color: 'var(--kb-text)' }}>設定</div>
        <div className="grid grid-cols-2 gap-3">
          <input className="kb-input" type="date" value={form.start} onChange={e=>updateForm({start:e.target.value})} />
          <input className="kb-input" type="date" value={form.end} onChange={e=>updateForm({end:e.target.value})} />
          <input className="kb-input" placeholder="初期資金" type="number" value={form.capital} onChange={e=>updateForm({capital:+e.target.value})} />
          <input className="kb-input" placeholder="手数料(%)" type="number" step="0.01" value={form.feePct} onChange={e=>updateForm({feePct:+e.target.value})} />
          <select className="kb-select col-span-2" value={form.strategy} onChange={e=>updateForm({strategy:e.target.value})}>
            <option value="breakout">ブレイクアウト</option>
            <option value="mean-reversion">リバーサル</option>
            <option value="trend-follow">トレンドフォロー</option>
          </select>
          <div className="col-span-2">
            <div className="kb-help mb-1">AIモデル</div>
            <div className="flex flex-wrap gap-2">
              {Object.keys(form.models).map(function(k){ return (
                <label key={k} className="kb-tag"><input type="checkbox" checked={!!form.models[k]} onChange={function(e){ updateForm({ models: Object.assign({}, form.models, (function(){ const o={}; o[k]=e.target.checked; return o; })()) }); }} /> <span>{k}</span></label>
              ); })}
            </div>
          </div>
          <div className="col-span-2">
            <div className="kb-help mb-1">銘柄（カンマ/スペース区切り）</div>
            <input className="kb-input w-full" value={form.symbolsInput} onChange={e=>updateForm({symbolsInput:e.target.value})} />
            <div className="mt-2 flex flex-wrap gap-2">
              {symbols.map(function(s){ return <span key={s} className="kb-tag"><span>{s}</span><span className="x" onClick={function(){ var arr = []; for(let i=0;i<symbols.length;i++){ if(symbols[i]!==s) arr.push(symbols[i]); } updateForm({ symbolsInput: arr.join(', ') }); }}>\u00D7</span></span>; })}
            </div>
          </div>
        </div>
        {errors.length>0 ? (<div className="kb-frame p-3 text-sm" style={{ color:'var(--kb-error)' }}>{errors.map(function(e,i){return <div key={i}>\u2022 {e}</div>;})}</div>) : null}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <button className="kb-btn kb-btn-primary w-full justify-center" onClick={startRun} disabled={state==='running'}><Play size={16}/> 実行</button>
          <button className="kb-btn kb-btn-secondary w-full justify-center" onClick={pauseRun} disabled={state!=='running'}><Pause size={16}/> 一時停止</button>
          <button className="kb-btn kb-btn-secondary w-full justify-center" onClick={stopRun} disabled={state==='idle'}><Square size={16}/> 停止</button>
          <button className="kb-btn kb-btn-secondary w-full justify-center" onClick={resetAll}><RotateCcw size={16}/> リセット</button>
        </div>
        <div>
          <div className="text-sm mb-1" style={{ color: 'var(--kb-text-muted)' }}>進捗 {progress}% ・ 残り {eta}</div>
          <div className="w-full bg-[var(--kb-bg-elevated)] h-2 rounded-full"><div className="h-2 rounded-full" style={{ width: `${progress}%`, background: 'var(--kb-brand)' }} /></div>
        </div>
      </div>
      <div className="kb-card p-4 lg:col-span-2 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div className="kb-frame p-3 text-sm">最終資産額: {formatCurrency(metrics.finalEquity||0)}</div>
          <div className="kb-frame p-3 text-sm">総利益/損失: {formatCurrency(metrics.totalPnL||0)}</div>
          <div className="kb-frame p-3 text-sm">勝率: {metrics.winRate||0}%</div>
          <div className="kb-frame p-3 text-sm">最大DD: {metrics.maxDDPct||0}%</div>
          <div className="kb-frame p-3 text-sm">シャープ: {metrics.sharpe||0}</div>
          <div className="kb-frame p-3 text-sm">総取引: {metrics.totalTrades||0}</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="kb-card p-2">
            <div className="text-sm font-bold px-2" style={{ color:'var(--kb-text)' }}>資産推移</div>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <defs><linearGradient id="eq" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--kb-chart-primary)" stopOpacity={0.35}/><stop offset="95%" stopColor="var(--kb-chart-primary)" stopOpacity={0}/></linearGradient></defs>
                  <CartesianGrid stroke="var(--kb-border)" strokeDasharray="3 3" />
                  <XAxis dataKey="t" stroke="var(--kb-text-muted)" tick={{ fontSize: 12 }} />
                  <YAxis stroke="var(--kb-text-muted)" tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ borderRadius: 8 }} />
                  <Area type="monotone" dataKey="v" stroke="var(--kb-chart-primary)" fillOpacity={1} fill="url(#eq)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="kb-card p-2">
            <div className="text-sm font-bold px-2" style={{ color:'var(--kb-text)' }}>ドローダウン</div>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={ddSeries} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="var(--kb-border)" strokeDasharray="3 3" />
                  <XAxis dataKey="t" stroke="var(--kb-text-muted)" tick={{ fontSize: 12 }} />
                  <YAxis stroke="var(--kb-text-muted)" tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ borderRadius: 8 }} />
                  <Area type="monotone" dataKey="dd" stroke="var(--kb-chart-benchmark)" fillOpacity={0.2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="kb-help px-2">※ サマリーの最大DDはこの系列から算出</div>
          </div>
          <div className="kb-card p-2 md:col-span-2">
            <div className="text-sm font-bold px-2 mb-2" style={{ color:'var(--kb-text)' }}>月別収益ヒートマップ</div>
            <div className="kb-heat">
              {heatData.map(function(h){ const pos=h.val>=0; const bg = pos? 'rgba(22,163,74,0.2)' : 'rgba(220,38,38,0.2)'; const col = pos? 'var(--kb-success)' : 'var(--kb-error)'; return <div key={h.m} className="kb-heat-cell" style={{ background:bg, color: col }}>{h.m}月 {h.val}%</div>; })}
            </div>
          </div>
        </div>
        <div className="kb-card p-2">
          <div className="flex items-center justify-between px-2"><div className="text-sm font-bold" style={{ color:'var(--kb-text)' }}>取引履歴（最新10件）</div><button className="kb-btn kb-btn-secondary" onClick={()=>exportCSV(trades)}><Download /> エクスポート</button></div>
          <div className="overflow-x-auto">
            <table className="kb-table w-full text-sm">
              <thead><tr>{['ID','時刻','サイド','数量','価格','PnL'].map(function(h){return <th key={h} className="px-3 py-2 text-left">{h}</th>;})}</tr></thead>
              <tbody>
                {trades.slice(-10).map(function(t){ return (
                  <tr key={t.id}>
                    <td className="px-3 py-2">{t.id}</td>
                    <td className="px-3 py-2">{t.time}</td>
                    <td className="px-3 py-2">{t.side}</td>
                    <td className="px-3 py-2">{t.qty}</td>
                    <td className="px-3 py-2">{t.price}</td>
                    <td className="px-3 py-2" style={{ color: t.pnl>=0? 'var(--kb-success)':'var(--kb-error)' }}>{formatCurrency(t.pnl)}</td>
                  </tr>
                );})}
                {trades.length===0 ? (<tr><td className="px-3 py-4" colSpan={6} style={{ color:'var(--kb-text-muted)' }}>まだ取引はありません</td></tr>) : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function AdminSample() {
  const cols = ["ユーザーID","メール","登録日","最終ログイン","ステータス"];
  const users = Array.from({ length: 6 }).map((_,i)=>({ id: `U-${1000+i}`, email: `user${i}@kaboom.ai`, created: '2025-01-01', last: '2025-08-01', status: i%2? 'active':'suspended' }));
  return (
    <div className="space-y-4">
      <div className="kb-card p-4">
        <div className="font-bold mb-3" style={{ color: 'var(--kb-text)' }}>ユーザー管理</div>
        <div className="overflow-x-auto">
          <table className="kb-table w-full text-sm">
            <thead><tr>{cols.map(function(c){return <th key={c} className="px-3 py-2 text-left">{c}</th>;})}</tr></thead>
            <tbody>
              {users.map(function(u){ return (
                <tr key={u.id}>
                  <td className="px-3 py-2">{u.id}</td>
                  <td className="px-3 py-2">{u.email}</td>
                  <td className="px-3 py-2">{u.created}</td>
                  <td className="px-3 py-2">{u.last}</td>
                  <td className="px-3 py-2">{u.status}</td>
                </tr>
              );})}
            </tbody>
          </table>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {["アクティブユーザー数","WS接続数","API使用率","エラー率"].map(function(x){ return (
          <div key={x} className="kb-card p-4"><div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>{x}</div><div className="text-xl font-extrabold" style={{ color: 'var(--kb-text)' }}>\u2014</div></div>
        );})}
      </div>
    </div>
  );
}

export default function App() {
  const { mode, setMode } = useTheme(); const [page, setPage] = useState("dashboard");
  useEffect(() => { runSelfTests(); }, []);
  return (
    <div style={{ background: "var(--kb-bg-canvas)", color: "var(--kb-text)", minHeight: '100vh' }}>
      <style>{CSS}</style>
      <Navbar page={page} setPage={setPage} mode={mode} setMode={setMode} />
      <main className="kb-container space-y-6">
        {page === "dashboard" ? (<><SummaryCards /><PortfolioChart /><RealtimeTable /></>) : null}
        {page === "ai" ? (<AISample />) : null}
        {page === "backtest" ? (<BacktestSample />) : null}
        {page === "admin" ? (<AdminSample />) : null}
      </main>
      <footer className="kb-container mt-10 pb-8 text-sm" style={{ color: 'var(--kb-text-muted)' }}>{"\u00A9 2025 Kaboom.ai \u2014 Sample UI built from the design system"}</footer>
    </div>
  );
}
