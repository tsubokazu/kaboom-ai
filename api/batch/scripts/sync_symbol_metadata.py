#!/usr/bin/env python3
"""東証Prime銘柄のメタデータをyfinance経由で取得しSupabaseに同期するスクリプト"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests
import yfinance as yf
from supabase import Client, create_client
from dotenv import load_dotenv

# 既存スクリプトの再利用
from batch.scripts.generate_prime_symbols import (
    fetch_jpx_data,
    filter_prime_symbols,
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


SIMPLIFIED_SECTOR_MAP = {
    "Communication Services": "Communication",
    "Consumer Defensive": "Consumer",
    "Consumer Cyclical": "Consumer",
    "Energy": "Energy",
    "Financial Services": "Financial",
    "Healthcare": "Healthcare",
    "Industrials": "Industrial",
    "Real Estate": "RealEstate",
    "Technology": "Technology",
    "Basic Materials": "Materials",
    "Utilities": "Utilities",
}


def load_prime_symbols(include_reit: bool) -> List[Dict[str, Any]]:
    """JPX公開データから東証Prime銘柄の基本情報を取得"""

    df = fetch_jpx_data()
    symbols = filter_prime_symbols(df, include_reit)
    if not symbols:
        raise RuntimeError("Prime銘柄リストを取得できませんでした")
    return symbols


def to_yfinance_symbol(code: str) -> str:
    return f"{code}.T"


def simplify_sector(raw_sector: Optional[str]) -> str:
    if not raw_sector:
        return "Unknown"
    return SIMPLIFIED_SECTOR_MAP.get(raw_sector, raw_sector or "Unknown")


def fetch_symbol_metadata(symbol: str, fallback_name: str | None = None) -> Dict[str, Any]:
    """単一銘柄のyfinanceメタデータを取得"""

    ticker = yf.Ticker(symbol)
    info: Dict[str, Any] = {}
    try:
        info = ticker.get_info()
    except Exception as exc:  # pragma: no cover - network failures are reported to logs
        logger.warning("yfinance情報取得失敗 %s: %s", symbol, exc)

    raw_sector = info.get("sector") or "Unknown"
    industry = info.get("industry") or "Unknown"
    name = (
        info.get("longName")
        or info.get("shortName")
        or info.get("name")
        or fallback_name
        or symbol
    )
    currency = info.get("currency") or "JPY"

    return {
        "symbol": symbol,
        "sector": simplify_sector(raw_sector),
        "industry": industry,
        "raw_sector": raw_sector,
        "market": "TSE_PRIME",
        "company_name": name,
        "currency": currency,
        "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def chunked(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def load_environment(explicit: Optional[Path]) -> None:
    """`.env` などを読み込んで環境変数を準備"""

    repo_root = Path(__file__).resolve().parents[2]
    candidates: List[Path] = []

    if explicit:
        explicit_path = explicit if explicit.is_absolute() else repo_root / explicit
        candidates.append(explicit_path)

    # よく使う .env 候補
    default_paths = [
        repo_root / ".env",
        repo_root / "api/.env",
        repo_root / "batch/.env",
        repo_root / "batch/.env.local",
    ]
    candidates.extend(default_paths)

    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)


def init_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SECRET_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    if not url or not key:
        raise RuntimeError("Supabase接続情報が環境変数に設定されていません")
    return create_client(url, key)


def prepare_supabase_payload(row: Dict[str, Any], include_optional: bool) -> Dict[str, Any]:
    base_keys = {"symbol", "sector", "industry", "raw_sector", "market", "updated_at"}
    payload = {key: row[key] for key in base_keys if key in row}
    if include_optional:
        optional_keys = {"company_name", "currency"}
        for key in optional_keys:
            if key in row:
                payload[key] = row[key]
    return payload


def upsert_metadata(
    client: Client,
    rows: List[Dict[str, Any]],
    batch_size: int,
    pause: float,
    include_optional: bool,
) -> None:
    total = len(rows)
    total_batches = (total + batch_size - 1) // batch_size if batch_size else 1
    for idx, batch in enumerate(chunked(rows, batch_size or total), start=1):
        logger.info("Supabase upsert %d/%d (batch=%d)", idx, total_batches, len(batch))
        payload = [prepare_supabase_payload(item, include_optional) for item in batch]
        response = client.table("symbol_metadata").upsert(
            payload,
            on_conflict="symbol",
            returning="minimal",
        ).execute()
        if getattr(response, "status_code", 200) >= 400:
            logger.error("Supabase upsert失敗: %s", getattr(response, "data", response))
            raise RuntimeError("Supabase upsertに失敗しました")
        if pause:
            time.sleep(pause)


def export_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("CSVにエクスポートしました: %s", output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="東証Primeメタデータ同期スクリプト")
    parser.add_argument("--include-reit", action="store_true", help="REIT銘柄を含める")
    parser.add_argument("--sleep", type=float, default=0.2, help="各銘柄取得間の待機秒数")
    parser.add_argument("--batch-delay", type=float, default=1.0, help="Supabaseバッチ間の待機秒数")
    parser.add_argument("--supabase-batch-size", type=int, default=200, help="Supabase upsertのバッチ件数")
    parser.add_argument("--max-symbols", type=int, default=0, help="テスト用: 先頭N銘柄のみ処理")
    parser.add_argument("--export-csv", type=Path, help="同期前にCSVへ出力するパス")
    parser.add_argument("--include-optional", action="store_true", help="company_name等の任意カラムも同期する")
    parser.add_argument("--env-file", type=Path, help="先に読み込む .env ファイルを指定")
    parser.add_argument("--dry-run", action="store_true", help="Supabaseへ書き込まず処理内容のみ表示")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    load_environment(args.env_file)

    logger.info("Prime銘柄リスト取得開始")
    symbols_meta = load_prime_symbols(include_reit=args.include_reit)
    if args.max_symbols:
        symbols_meta = symbols_meta[: args.max_symbols]
    logger.info("Prime銘柄件数: %d", len(symbols_meta))

    records: List[Dict[str, Any]] = []
    for idx, item in enumerate(symbols_meta, start=1):
        code = str(item.get("code"))
        name = str(item.get("name") or code)
        symbol = to_yfinance_symbol(code)
        logger.debug("(%d/%d) %s メタデータ取得", idx, len(symbols_meta), symbol)
        record = fetch_symbol_metadata(symbol, fallback_name=name)
        records.append(record)
        if idx % 25 == 0:
            logger.info("%d/%d 件取得完了", idx, len(symbols_meta))
        if args.sleep:
            time.sleep(args.sleep)

    logger.info("メタデータ取得完了: %d件", len(records))

    if args.export_csv:
        export_csv(records, args.export_csv)

    if args.dry_run:
        logger.info("DRY RUN: Supabase同期をスキップします")
        logger.info("サンプル: %s", records[:3])
        return

    client = init_supabase()
    logger.info("Supabase同期開始 (バッチサイズ=%d)", args.supabase_batch_size)
    upsert_metadata(
        client,
        records,
        args.supabase_batch_size,
        args.batch_delay,
        include_optional=args.include_optional,
    )
    logger.info("Supabase同期完了")


if __name__ == "__main__":
    main()
