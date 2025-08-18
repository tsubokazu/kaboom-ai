"use client";
import React from "react";
import { Search, Play, Pause, Square, RotateCcw, Download } from "./icons";

export function AISample() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="kb-card p-4 lg:col-span-2">
          <div className="flex items-center gap-2 mb-3">
            <Search size={16} />
            <input className="kb-input w-full" placeholder="銘柄コード / 名前を検索" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {["1分足","5分足","1時間足","4時間足"].map(t => (
              <div key={t} className="kb-frame h-36 flex items-center justify-center text-sm text-muted">{t}（画像）</div>
            ))}
          </div>
        </div>
        <div className="kb-card p-4 space-y-3">
          <div className="font-bold">AI判断結果</div>
          <div>
            総合判断: <span className="kb-badge badge-buy">BUY</span>
          </div>
          <div className="text-sm text-muted">モデル: kaboom-v1</div>
          <ul className="list-disc pl-5 text-sm">
            <li>上昇トレンド継続</li>
            <li>出来高増加</li>
            <li>MACD ゴールデンクロス</li>
          </ul>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button className="kb-btn kb-btn-primary w-full justify-center">成行で買い</button>
            <button className="kb-btn kb-btn-secondary w-full justify-center">ウォッチに追加</button>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {["RSI","MACD","BBANDS","MA","VOL"].map(x => (
          <div key={x} className="kb-card p-4">
            <div className="text-sm font-bold">{x}</div>
            <div className="kb-frame h-20 mt-2 flex items-center justify-center text-xs text-muted">ゲージ/ミニグラフ</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function BacktestSample() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="kb-card p-4 space-y-3">
        <div className="font-bold">設定</div>
        <div className="grid grid-cols-2 gap-3">
          <input className="kb-input" type="date" />
          <input className="kb-input" type="date" />
          <input className="kb-input" placeholder="初期資金" />
          <input className="kb-input" placeholder="手数料(%)" />
          <input className="kb-input col-span-2" placeholder="銘柄（カンマ区切り）" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <button className="kb-btn kb-btn-primary w-full justify-center"><Play size={16}/> 実行</button>
          <button className="kb-btn kb-btn-secondary w-full justify-center"><Pause size={16}/> 一時停止</button>
          <button className="kb-btn kb-btn-secondary w-full justify-center"><Square size={16}/> 停止</button>
          <button className="kb-btn kb-btn-secondary w-full justify-center"><RotateCcw size={16}/> リセット</button>
        </div>
        <div>
          <div className="text-sm mb-1 text-muted">進捗</div>
          <div className="w-full bg-[var(--kb-bg-elevated)] h-2 rounded-full">
            <div className="h-2 rounded-full" style={{ width: '48%', background: 'var(--kb-brand)' }} />
          </div>
        </div>
      </div>
      <div className="kb-card p-4 lg:col-span-2 space-y-3">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {["最終資産額","総利益/損失","勝率","最大DD","シャープレシオ","総取引回数"].map(x => (
            <div key={x} className="kb-frame p-3 text-sm">{x}: サンプル</div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {['資産推移','ドローダウン'].map(t => (
            <div key={t} className="kb-frame h-40 flex items-center justify-center text-muted">{t}（画像）</div>
          ))}
          <div className="kb-frame h-40 flex items-center justify-center text-muted">月別収益ヒートマップ（画像）</div>
        </div>
        <div className="flex justify-end">
          <button className="kb-btn kb-btn-secondary"><Download /> エクスポート</button>
        </div>
      </div>
    </div>
  );
}

export function AdminSample() {
  const cols = ["ユーザーID","メール","登録日","最終ログイン","ステータス"];
  const users = Array.from({ length: 6 }).map((_,i)=>({ id: `U-${1000+i}`, email: `user${i}@kaboom.ai`, created: '2025-01-01', last: '2025-08-01', status: i%2? 'active':'suspended' }));
  return (
    <div className="space-y-4">
      <div className="kb-card p-4">
        <div className="font-bold mb-3">ユーザー管理</div>
        <div className="overflow-x-auto">
          <table className="kb-table w-full text-sm">
            <thead><tr>{cols.map(c=> <th key={c} className="px-3 py-2 text-left">{c}</th>)}</tr></thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td className="px-3 py-2">{u.id}</td>
                  <td className="px-3 py-2">{u.email}</td>
                  <td className="px-3 py-2">{u.created}</td>
                  <td className="px-3 py-2">{u.last}</td>
                  <td className="px-3 py-2">{u.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {["アクティブユーザー数","WS接続数","API使用率","エラー率"].map(x => (
          <div key={x} className="kb-card p-4">
            <div className="text-sm text-muted">{x}</div>
            <div className="text-xl font-extrabold">—</div>
          </div>
        ))}
      </div>
    </div>
  );
}

