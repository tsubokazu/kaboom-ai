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

from batch.config.loader import load_env, load_universe_settings
from batch.pipeline.supabase_sector_loader import load_symbols_from_supabase
from app.services.universe_selection_service import (
    UniverseSelectionRequest,
    UniverseSelectionService,
    UniverseSelectionError,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_symbols_from_csv(path: Path) -> List[str]:
    df = pd.read_csv(path)
    column = df.columns[0]
    return [str(value).strip() for value in df[column].dropna().unique()]


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
    output_cfg = settings_raw.get(
        "output",
        {"core_list_path": "batch/data/core20.csv", "bench_list_path": "batch/data/bench5.csv"},
    )
    existing_core: List[str] = []
    core_path = Path(output_cfg.get("core_list_path", "batch/data/core20.csv"))
    if core_path.exists():
        existing_core = load_existing_list(core_path)

    bench_path = Path(output_cfg.get("bench_list_path", "batch/data/bench5.csv"))
    symbols: List[str] = []
    resolved_source = args.symbol_source
    if args.symbol_source == "supabase":
        symbols = load_symbols_from_supabase(args.market)
        logger.info("loaded %d symbols from Supabase", len(symbols))
        if not symbols:
            logger.warning("Supabaseから銘柄を取得できませんでした。CSVへフォールバックします")
            symbols = load_symbols_from_csv(args.symbols)
            resolved_source = "list"
    else:
        symbols = load_symbols_from_csv(args.symbols)
        resolved_source = "list"

    service = UniverseSelectionService()
    request = UniverseSelectionRequest(
        settings_path=args.settings,
        market=args.market,
        symbol_source=resolved_source,
        symbols=symbols,
        existing_core=existing_core,
    )

    try:
        result = service.run_selection(request)
    except UniverseSelectionError as exc:
        logger.error("universe selection failed: %s", exc)
        return

    logger.info(
        "metrics calculated for %d symbols → %d after filters",
        result.total_symbols,
        result.filtered_symbols,
    )

    save_list(core_path, result.core)
    save_list(bench_path, result.bench)
    save_snapshot(args.snapshot, result.snapshot_rows)

    print(
        json.dumps(
            {
                "core": result.core,
                "bench": result.bench,
                "total_symbols": result.total_symbols,
                "filtered_symbols": result.filtered_symbols,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
