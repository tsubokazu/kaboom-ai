#!/usr/bin/env python3
"""Supabaseの銘柄マスタを対象に日次バックフィルを実行するユーティリティ。"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from influxdb_client_3 import InfluxDBClient3

from batch.config.loader import InfluxConfig, load_env, load_influx_config
from batch.ingest.backfill_yf import (
    INTERVAL_SPECS,
    dataframe_to_points,
    fetch_symbol,
    write_to_influx,
)
from batch.pipeline.supabase_sector_loader import load_symbols_from_supabase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


DEFAULT_INTERVAL_DAYS: Dict[str, int] = {
    "1m": 2,    # 直近2日分を再取得（yfinance仕様に合わせた短期ウィンドウ）
    "5m": 5,    # 直近5日分
    "1d": 730,  # 約2年分の日足を維持
}


class IngestResult(Dict[str, object]):
    """型ヒント用の簡易辞書"""


def parse_interval_days(values: Optional[Iterable[str]]) -> Dict[str, int]:
    """`interval=days` 形式の値を辞書に変換する。"""

    if not values:
        return dict(DEFAULT_INTERVAL_DAYS)

    parsed: Dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"interval指定は '1m=2' の形式で入力してください: {value}")
        interval, days = value.split("=", 1)
        interval = interval.strip()
        if interval not in INTERVAL_SPECS:
            raise ValueError(f"サポートされていないintervalです: {interval}")
        try:
            parsed[interval] = int(days)
        except ValueError as exc:
            raise ValueError(f"日数は整数で指定してください: {days}") from exc
    return parsed


def load_environment(env_file: Optional[Path]) -> None:
    """標準の .env.local と任意指定の .env を読み込む。"""

    load_env()  # batch/.env.local を既定で読み込む
    if env_file:
        load_env(env_file)


def run_daily_ingest(
    interval_days: Dict[str, int],
    market: str = "TSE_PRIME",
    symbols: Optional[List[str]] = None,
    chunk_size: int = 5_000,
) -> IngestResult:
    """Supabaseの銘柄を対象に指定intervalのバックフィルを実行する。"""

    config: InfluxConfig = load_influx_config()
    symbol_list = symbols or load_symbols_from_supabase(market)
    if not symbol_list:
        raise RuntimeError("バックフィル対象の銘柄が取得できませんでした")

    # デバッグ: InfluxDB接続情報をログ出力
    logger.info(f"InfluxDB接続情報: host={config.host}, org={config.org}, token=...{config.token[-10:] if config.token else 'None'}")
    logger.info(f"InfluxDBバケット設定: raw_1m_hot={config.bucket_raw_1m_hot}, agg_5m={config.bucket_agg_5m}, agg_1d={config.bucket_agg_1d}")

    result: IngestResult = {
        "total_symbols": len(symbol_list),
        "intervals": {},
    }

    with InfluxDBClient3(
        host=config.host,
        token=config.token,
        org=config.org,
        timeout=30_000,
        max_retries=config.max_retries,
    ) as client:
        for interval, days in interval_days.items():
            spec = INTERVAL_SPECS.get(interval)
            if spec is None:
                logger.warning("interval=%s はサポートされていません。スキップします", interval)
                continue

            bucket = getattr(config, spec.default_bucket_attr, None)
            if not bucket:
                raise RuntimeError(f"InfluxConfigに {spec.default_bucket_attr} が設定されていません")

            # デバッグ: 書き込み対象バケット情報をログ出力
            logger.info(f"interval={interval}: バケット={bucket} に書き込み開始")

            interval_summary = {
                "bucket": bucket,
                "days_requested": days,
                "symbols_processed": 0,
                "points_written": 0,
                "failures": [],
            }

            for symbol in symbol_list:
                try:
                    df = fetch_symbol(symbol, interval, days, spec)
                    if df.empty:
                        continue
                    points = dataframe_to_points(df, symbol, spec.measurement)
                    written = write_to_influx(client, bucket, points, chunk_size)
                    interval_summary["symbols_processed"] += 1
                    interval_summary["points_written"] += written
                except Exception as exc:  # pragma: no cover - ネットワークエラー等
                    logger.exception("%s: interval=%s でエラーが発生しました", symbol, interval)
                    interval_summary["failures"].append({
                        "symbol": symbol,
                        "error": str(exc),
                    })

            result["intervals"][interval] = interval_summary

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Supabase銘柄に対する日次バックフィルを実行")
    parser.add_argument(
        "--interval",
        dest="intervals",
        action="append",
        help="interval=days 形式で指定 (例: --interval 1m=2)。複数指定可。未指定ならデフォルト設定を利用",
    )
    parser.add_argument(
        "--market",
        default="TSE_PRIME",
        help="Supabaseのmarketフィールドでフィルタする値 (例: TSE_PRIME)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="明示的に対象銘柄を指定 (Supabaseを介さず実行)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5_000,
        help="InfluxDBへ書き込む際のポイントバッチサイズ",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="追加で読み込む環境変数ファイル (.env)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="結果をJSON形式で標準出力へ表示",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        interval_days = parse_interval_days(args.intervals)
    except ValueError as exc:
        parser.error(str(exc))

    load_environment(args.env_file)

    result = run_daily_ingest(
        interval_days=interval_days,
        market=args.market,
        symbols=args.symbols,
        chunk_size=args.chunk_size,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for interval, summary in result["intervals"].items():
            logger.info(
                "interval=%s processed=%d written=%d failures=%d",
                interval,
                summary["symbols_processed"],
                summary["points_written"],
                len(summary["failures"]),
            )


if __name__ == "__main__":
    main()
