// Utility functions for the Kaboom.ai application

/**
 * Format currency in Japanese Yen
 */
export function formatCurrency(amount: number): string {
  return amount.toLocaleString("ja-JP", {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 0,
  });
}

/**
 * Format percentage
 */
export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Format price with comma separators
 */
export function formatPrice(price: number): string {
  return price.toLocaleString("ja-JP");
}

/**
 * Compute Risk/Reward ratio
 */
export function computeRiskReward({
  side,
  entry,
  stop,
  takeProfit,
}: {
  side: "BUY" | "SELL";
  entry: number;
  stop: number;
  takeProfit: number;
}): number {
  const isLong = side === "BUY";
  const risk = Math.max(0.0001, isLong ? entry - stop : stop - entry);
  const reward = Math.max(
    0.0001,
    isLong ? takeProfit - entry : entry - takeProfit,
  );
  return Number((reward / risk).toFixed(2));
}

/**
 * Generate mock chart data
 */
export function generateMockChartData(length: number = 40): Array<{
  t: number;
  asset: number;
  bench: number;
}> {
  const data = [];
  for (let i = 0; i < length; i++) {
    data.push({
      t: i,
      asset: 100 + Math.sin(i / 3) * 6 + Math.random() * 3,
      bench: 100 + Math.cos(i / 4) * 4,
    });
  }
  return data;
}

/**
 * Parse symbols input (comma or space separated)
 */
export function parseSymbolsInput(input: string): string[] {
  const symbols = (input || "")
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 20); // Max 20 symbols
  return symbols;
}

/**
 * Validate backtest input
 */
export function validateBacktestInput({
  start,
  end,
  capital,
  feePct,
  strategy,
  models,
  symbols,
}: {
  start: string;
  end: string;
  capital: number;
  feePct: number;
  strategy: string;
  models: Record<string, boolean>;
  symbols: string[];
}): string[] {
  const errors: string[] = [];

  const startDate = start ? new Date(start) : null;
  const endDate = end ? new Date(end) : null;

  if (!startDate) errors.push("開始日を入力してください");
  if (!endDate) errors.push("終了日を入力してください");
  if (startDate && endDate && endDate <= startDate) {
    errors.push("終了日は開始日より後にしてください");
  }
  if (!(capital > 0)) errors.push("初期資金は正の数値で入力してください");
  if (feePct < 0) errors.push("手数料は0以上で入力してください");
  if (!strategy) errors.push("取引戦略を選択してください");

  const hasSelectedModel = Object.values(models).some(Boolean);
  if (!hasSelectedModel) errors.push("AIモデルを1つ以上選択してください");

  if (!symbols || symbols.length === 0) {
    errors.push("銘柄を1つ以上入力してください");
  }

  return errors;
}

/**
 * Export data as CSV
 */
export function exportCSV(
  data: Array<Record<string, string | number>>,
  filename: string = "export.csv",
): void {
  if (data.length === 0) return;

  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(","),
    ...data.map((row) => headers.map((header) => row[header]).join(",")),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
