"""Core20 + Bench5 のユニバースを選定するスクリプト。"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

# ルートディレクトリを import path に追加
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from batch.config.loader import load_env, load_influx_config, load_universe_settings
from batch.pipeline.metrics import (
    InfluxMarketDataClient,
    MetricConfig,
    SymbolMetrics,
    calculate_symbol_metrics,
    load_metric_config,
)
from batch.pipeline.score_universe import (
    UniverseSettings,
    calculate_scores,
    load_sector_map,
    load_universe_settings_struct,
    select_universe,
)
from batch.pipeline.supabase_sector_loader import load_symbols_from_supabase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_symbols_from_csv(path: Path) -> List[str]:
    df = pd.read_csv(path)
    column = df.columns[0]
    return [str(value).strip() for value in df[column].dropna().unique()]


def apply_hard_filters(
    metrics: Dict[str, SymbolMetrics],
    thresholds: Dict[str, float],
) -> Dict[str, SymbolMetrics]:
    filtered: Dict[str, SymbolMetrics] = {}
    adv_min = float(thresholds.get("adv_jpy_min", 0))
    price_min = float(thresholds.get("price_min", 0))
    price_max = float(thresholds.get("price_max", float("inf")))
    atr_min = float(thresholds.get("atr_pct_min", 0))
    atr_max = float(thresholds.get("atr_pct_max", float("inf")))
    zero_ratio_max = float(thresholds.get("zero_volume_ratio_max", 1))

    for symbol, metric in metrics.items():
        if metric.adv_jpy < adv_min:
            continue
        if not (price_min <= metric.latest_close <= price_max):
            continue
        if metric.atr_pct is None or not (atr_min <= metric.atr_pct <= atr_max):
            continue
        if metric.no_trade_5m_ratio > zero_ratio_max:
            continue
        filtered[symbol] = metric

    return filtered


def load_existing_list(path: Path) -> List[str]:
    if not path.exists():
        return []
    df = pd.read_csv(path)
    column = df.columns[0]
    return [str(value).strip() for value in df[column].dropna().tolist()]


def save_list(path: Path, symbols: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"symbol": list(symbols)}).to_csv(path, index=False)


def save_snapshot(path: Path, data: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data).to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Select Core20 and Bench5 universe")
    parser.add_argument(
        "--symbol-source",
        choices=["supabase", "csv"],
        default="supabase",
        help="銘柄リストの取得元。supabase または csv",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=Path("batch/config/universe_settings.example.toml"),
        help="ユニバース選定設定ファイル",
    )
    parser.add_argument(
        "--symbols",
        type=Path,
        default=Path("batch/data/symbols_prime.csv"),
        help="対象銘柄リスト (CSV)。--symbol-source=csv の場合に使用",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("batch/data/universe_snapshot.csv"),
        help="メトリクスとスコアを出力するCSV",
    )
    parser.add_argument(
        "--market",
        type=str,
        default="TSE_PRIME",
        help="Supabaseから取得するmarket値 (--symbol-source=supabase時)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="追加で読み込む環境変数ファイル (.env)",
    )
    args = parser.parse_args()

    # 環境変数の読み込み（デフォルト .env.local → 任意指定）
    load_env()
    if args.env_file:
        load_env(args.env_file)

    settings_raw = load_universe_settings(args.settings)
    metric_config = load_metric_config(settings_raw)
    universe_settings = load_universe_settings_struct(settings_raw)
    thresholds = settings_raw.get("thresholds", {})
    output_cfg = settings_raw.get("output", {})

    symbols: List[str] = []
    if args.symbol_source == "supabase":
        symbols = load_symbols_from_supabase(args.market)
        if not symbols:
            logger.warning("Supabaseから銘柄を取得できませんでした。CSVへフォールバックします")
            symbols = load_symbols_from_csv(args.symbols)
    else:
        symbols = load_symbols_from_csv(args.symbols)

    logger.info("loaded %d symbols", len(symbols))

    influx_config = load_influx_config()

    with InfluxMarketDataClient(influx_config) as client:
        metrics = calculate_symbol_metrics(client, symbols, metric_config)

    logger.info("calculated metrics for %d symbols", len(metrics))
    metrics = apply_hard_filters(metrics, thresholds)
    logger.info("after hard filters %d symbols remain", len(metrics))

    if not metrics:
        logger.error("no symbols passed hard filters")
        return

    scores, breakdown = calculate_scores(metrics, universe_settings.weights, metric_config)

    sector_map = load_sector_map(universe_settings.sector_cap.definition_path)

    existing_core = []
    core_path = Path(output_cfg.get("core_list_path", "batch/data/core20.csv"))
    if core_path.exists():
        existing_core = load_existing_list(core_path)

    selection = select_universe(scores, universe_settings, existing_core, sector_map)

    bench_path = Path(output_cfg.get("bench_list_path", "batch/data/bench5.csv"))
    save_list(core_path, selection["core"])
    save_list(bench_path, selection["bench"])

    snapshot_rows: List[Dict[str, object]] = []
    for symbol, metric in metrics.items():
        row = {
            "symbol": symbol,
            "latest_close": metric.latest_close,
            "adv_jpy": metric.adv_jpy,
            "atr_pct": metric.atr_pct,
            "median_5m_range_bps": metric.median_5m_range_bps,
            "close_5m_vol_share": metric.close_5m_vol_share,
            "no_trade_5m_ratio": metric.no_trade_5m_ratio,
            "score": scores.get(symbol, 0.0),
            "score_total": breakdown.get(symbol, {}).get("total", scores.get(symbol, 0.0)),
        }
        row.update({f"score_{k}": v for k, v in breakdown.get(symbol, {}).items() if k != "total"})
        snapshot_rows.append(row)

    save_snapshot(args.snapshot, snapshot_rows)

    print(json.dumps(selection, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
