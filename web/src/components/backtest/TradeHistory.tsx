"use client";

import React, { useState, useMemo } from "react";
import { Search, ArrowUpDown, Eye } from "lucide-react";
import { useBacktestStore } from "@/stores/backtestStore";

type SortField = 'date' | 'symbol' | 'profit' | 'price';
type SortDirection = 'asc' | 'desc';
type FilterType = 'all' | 'buy' | 'sell' | 'profit' | 'loss';

export function TradeHistory() {
  const { results, openTradeDetail } = useBacktestStore();
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [filterType, setFilterType] = useState<FilterType>('all');

  // フィルタリング・ソート処理
  const filteredAndSortedTrades = useMemo(() => {
    const trades = results?.trades || [];
    const filtered = trades.filter(trade => {
      // 検索フィルター
      const matchesSearch = trade.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           trade.entryReason.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           trade.exitReason.toLowerCase().includes(searchTerm.toLowerCase());

      // タイプフィルター
      const matchesFilter = filterType === 'all' ||
                           (filterType === 'buy' && trade.type === 'buy') ||
                           (filterType === 'sell' && trade.type === 'sell') ||
                           (filterType === 'profit' && (trade.profit || 0) > 0) ||
                           (filterType === 'loss' && (trade.profit || 0) < 0);

      return matchesSearch && matchesFilter;
    });

    // ソート処理
    filtered.sort((a, b) => {
      let aValue: string | number | Date;
      let bValue: string | number | Date;

      switch (sortField) {
        case 'date':
          aValue = new Date(a.date);
          bValue = new Date(b.date);
          break;
        case 'symbol':
          aValue = a.symbol;
          bValue = b.symbol;
          break;
        case 'profit':
          aValue = a.profit || 0;
          bValue = b.profit || 0;
          break;
        case 'price':
          aValue = a.price;
          bValue = b.price;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [results?.trades, searchTerm, sortField, sortDirection, filterType]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const formatCurrency = (value: number) => {
    return `¥${new Intl.NumberFormat('ja-JP').format(value)}`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ja-JP');
  };

  if (!results || !results.trades || results.trades.length === 0) {
    return (
      <div
        className="p-6 rounded-lg text-center"
        style={{
          background: "var(--kb-bg-surface)",
          border: "1px solid var(--kb-border)",
        }}
      >
        <p style={{ color: "var(--kb-text-muted)" }}>
          取引履歴はバックテスト完了後に表示されます
        </p>
      </div>
    );
  }

  return (
    <div
      className="p-6 rounded-lg space-y-4"
      style={{
        background: "var(--kb-bg-surface)",
        border: "1px solid var(--kb-border)",
      }}
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-1 h-5 bg-[var(--kb-brand)] rounded-full" />
        <h3 className="text-lg font-semibold">取引履歴</h3>
        <span className="text-sm px-2 py-1 rounded" style={{ 
          background: "var(--kb-bg-elevated)", 
          color: "var(--kb-text-secondary)" 
        }}>
          {filteredAndSortedTrades.length}件
        </span>
      </div>

      {/* フィルター・検索バー */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* 検索 */}
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2" 
                  style={{ color: "var(--kb-text-muted)" }} />
          <input
            type="text"
            placeholder="銘柄・理由で検索..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-3 py-2 rounded border text-sm"
            style={{
              background: "var(--kb-bg-elevated)",
              border: "1px solid var(--kb-border)",
              color: "var(--kb-text-primary)",
            }}
          />
        </div>

        {/* フィルター */}
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as FilterType)}
          className="px-3 py-2 rounded border text-sm"
          style={{
            background: "var(--kb-bg-elevated)",
            border: "1px solid var(--kb-border)",
            color: "var(--kb-text-primary)",
          }}
        >
          <option value="all">すべて</option>
          <option value="buy">買い注文</option>
          <option value="sell">売り注文</option>
          <option value="profit">利益</option>
          <option value="loss">損失</option>
        </select>
      </div>

      {/* 取引テーブル */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: "1px solid var(--kb-border)" }}>
              <th 
                className="text-left p-3 cursor-pointer hover:bg-opacity-50"
                onClick={() => handleSort('date')}
                style={{ color: "var(--kb-text-secondary)" }}
              >
                <div className="flex items-center gap-1">
                  日時
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th 
                className="text-left p-3 cursor-pointer hover:bg-opacity-50"
                onClick={() => handleSort('symbol')}
                style={{ color: "var(--kb-text-secondary)" }}
              >
                <div className="flex items-center gap-1">
                  銘柄
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th className="text-left p-3" style={{ color: "var(--kb-text-secondary)" }}>
                売買
              </th>
              <th className="text-right p-3" style={{ color: "var(--kb-text-secondary)" }}>
                数量
              </th>
              <th 
                className="text-right p-3 cursor-pointer hover:bg-opacity-50"
                onClick={() => handleSort('price')}
                style={{ color: "var(--kb-text-secondary)" }}
              >
                <div className="flex items-center justify-end gap-1">
                  価格
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th 
                className="text-right p-3 cursor-pointer hover:bg-opacity-50"
                onClick={() => handleSort('profit')}
                style={{ color: "var(--kb-text-secondary)" }}
              >
                <div className="flex items-center justify-end gap-1">
                  損益
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th className="text-center p-3" style={{ color: "var(--kb-text-secondary)" }}>
                信頼度
              </th>
              <th className="text-center p-3" style={{ color: "var(--kb-text-secondary)" }}>
                詳細
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedTrades.map((trade, index) => (
              <tr 
                key={trade.id}
                className="hover:bg-opacity-50 transition-colors"
                style={{ 
                  borderBottom: "1px solid var(--kb-border)",
                  background: index % 2 === 0 ? "transparent" : "var(--kb-bg-elevated)",
                }}
              >
                <td className="p-3" style={{ color: "var(--kb-text-primary)" }}>
                  {formatDate(trade.date)}
                </td>
                <td className="p-3 font-medium" style={{ color: "var(--kb-text-primary)" }}>
                  {trade.symbol}
                </td>
                <td className="p-3">
                  <span 
                    className="px-2 py-1 text-xs rounded font-medium"
                    style={{
                      background: trade.type === 'buy' ? "var(--kb-success)" : "var(--kb-error)",
                      color: "white",
                    }}
                  >
                    {trade.type === 'buy' ? '買い' : '売り'}
                  </span>
                </td>
                <td className="p-3 text-right" style={{ color: "var(--kb-text-primary)" }}>
                  {trade.quantity.toLocaleString()}
                </td>
                <td className="p-3 text-right font-mono" style={{ color: "var(--kb-text-primary)" }}>
                  {formatCurrency(trade.price)}
                </td>
                <td className="p-3 text-right font-mono font-medium">
                  <span style={{ 
                    color: (trade.profit || 0) >= 0 ? "var(--kb-success)" : "var(--kb-error)" 
                  }}>
                    {(trade.profit || 0) >= 0 ? '+' : ''}{formatCurrency(trade.profit || 0)}
                  </span>
                </td>
                <td className="p-3 text-center">
                  <div className="flex items-center justify-center">
                    <div 
                      className="w-8 h-2 rounded-full"
                      style={{ 
                        background: `linear-gradient(90deg, var(--kb-error) 0%, var(--kb-warning) 50%, var(--kb-success) 100%)`,
                        position: 'relative'
                      }}
                    >
                      <div 
                        className="w-1 h-2 bg-white rounded-full absolute top-0"
                        style={{ left: `${trade.confidence}%`, transform: 'translateX(-50%)' }}
                      />
                    </div>
                    <span className="ml-2 text-xs" style={{ color: "var(--kb-text-muted)" }}>
                      {trade.confidence}%
                    </span>
                  </div>
                </td>
                <td className="p-3 text-center">
                  <button
                    onClick={() => openTradeDetail(trade)}
                    className="p-1 rounded hover:bg-opacity-20 transition-colors"
                    style={{ 
                      background: "var(--kb-bg-elevated)",
                      color: "var(--kb-brand)",
                    }}
                  >
                    <Eye size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* サマリー統計 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t" style={{ borderColor: "var(--kb-border)" }}>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            表示件数
          </div>
          <div className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
            {filteredAndSortedTrades.length}件
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            利益取引
          </div>
          <div className="font-semibold" style={{ color: "var(--kb-success)" }}>
            {filteredAndSortedTrades.filter(t => (t.profit || 0) > 0).length}件
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            損失取引
          </div>
          <div className="font-semibold" style={{ color: "var(--kb-error)" }}>
            {filteredAndSortedTrades.filter(t => (t.profit || 0) < 0).length}件
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs mb-1" style={{ color: "var(--kb-text-muted)" }}>
            平均信頼度
          </div>
          <div className="font-semibold" style={{ color: "var(--kb-text-primary)" }}>
            {filteredAndSortedTrades.length > 0 
              ? Math.round(filteredAndSortedTrades.reduce((sum, t) => sum + t.confidence, 0) / filteredAndSortedTrades.length)
              : 0}%
          </div>
        </div>
      </div>
    </div>
  );
}