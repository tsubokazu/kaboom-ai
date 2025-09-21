"""東証Prime市場の銘柄リストを生成するスクリプト

JPX（日本取引所グループ）の公開データを使用して、東証Prime上場銘柄の一覧を取得し、
yfinance形式（XXXX.T）でCSVファイルに保存する。
"""
from __future__ import annotations

import argparse
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests
import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# JPX公開データURL（上場会社一覧）
JPX_LISTED_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
# バックアップとして、より安定したAPIを使用
BACKUP_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OUTPUT_FILE = DATA_DIR / "symbols_prime.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate TSE Prime symbols list")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="出力CSVファイルパス")
    parser.add_argument("--format", choices=["yfinance", "raw"], default="yfinance",
                       help="出力形式 (yfinance: 7203.T, raw: 7203)")
    parser.add_argument("--include-reit", action="store_true", help="REITも含める")
    parser.add_argument("--dry-run", action="store_true", help="実際のファイル出力を行わない")
    return parser.parse_args()


def fetch_jpx_data() -> pd.DataFrame:
    """JPXから上場銘柄データを取得"""
    try:
        logger.info("JPX上場銘柄データを取得中...")

        # JPXの公開Excelファイルを直接読み込み
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(JPX_LISTED_URL, headers=headers, timeout=30)
        response.raise_for_status()

        # Excelファイルを読み込み（複数シートがある場合は最初のシートを使用）
        df = pd.read_excel(response.content, sheet_name=0, header=0)
        logger.info(f"JPXデータ取得成功: {len(df)}銘柄")

        return df

    except Exception as e:
        logger.error(f"JPXデータ取得失敗: {e}")
        logger.info("代替データソースを使用します...")
        return fetch_fallback_data()


def fetch_fallback_data() -> pd.DataFrame:
    """代替データソース: 手動で主要Prime銘柄リストを作成"""
    logger.warning("代替データを使用: 主要Prime銘柄のサンプルリスト")

    # 主要東証Prime銘柄の手動リスト（サンプル）
    sample_symbols = [
        # 日経225主要構成銘柄
        {"code": "7203", "name": "トヨタ自動車", "market": "Prime"},
        {"code": "9984", "name": "ソフトバンクグループ", "market": "Prime"},
        {"code": "6758", "name": "ソニーグループ", "market": "Prime"},
        {"code": "8035", "name": "東京エレクトロン", "market": "Prime"},
        {"code": "4063", "name": "信越化学工業", "market": "Prime"},
        {"code": "9434", "name": "ソフトバンク", "market": "Prime"},
        {"code": "8306", "name": "三菱UFJフィナンシャル・グループ", "market": "Prime"},
        {"code": "7974", "name": "任天堂", "market": "Prime"},
        {"code": "6981", "name": "村田製作所", "market": "Prime"},
        {"code": "8316", "name": "三井住友フィナンシャルグループ", "market": "Prime"},
        {"code": "4519", "name": "中外製薬", "market": "Prime"},
        {"code": "6954", "name": "ファナック", "market": "Prime"},
        {"code": "9983", "name": "ファーストリテイリング", "market": "Prime"},
        {"code": "4578", "name": "大塚ホールディングス", "market": "Prime"},
        {"code": "8031", "name": "三井物産", "market": "Prime"},
        {"code": "8058", "name": "三菱商事", "market": "Prime"},
        {"code": "7182", "name": "ゆうちょ銀行", "market": "Prime"},
        {"code": "9432", "name": "日本電信電話", "market": "Prime"},
        {"code": "4324", "name": "電通グループ", "market": "Prime"},
        {"code": "6367", "name": "ダイキン工業", "market": "Prime"},
    ]

    return pd.DataFrame(sample_symbols)


def filter_prime_symbols(df: pd.DataFrame, include_reit: bool = False) -> List[Dict[str, Any]]:
    """Prime市場銘柄のフィルタリング"""

    # 列名の正規化（JPXファイルの列名は変動する可能性があるため）
    df.columns = df.columns.str.strip()

    # 可能な列名パターンを確認
    potential_code_cols = [col for col in df.columns if 'コード' in col or 'code' in col.lower() or 'symbol' in col.lower()]
    potential_name_cols = [col for col in df.columns if '銘柄名' in col or '名称' in col or 'name' in col.lower()]
    potential_market_cols = [col for col in df.columns if '市場' in col or 'market' in col.lower()]

    logger.info(f"データ列: {list(df.columns)}")
    logger.info(f"コード列候補: {potential_code_cols}")
    logger.info(f"名称列候補: {potential_name_cols}")
    logger.info(f"市場列候補: {potential_market_cols}")

    # 代替データの場合はそのまま返す
    if 'code' in df.columns and 'name' in df.columns:
        symbols = []
        for _, row in df.iterrows():
            symbols.append({
                'code': str(row['code']).zfill(4),  # 4桁に正規化
                'name': row['name'],
                'market': row.get('market', 'Prime')
            })
        return symbols

    # JPXデータの処理（実際の列名に基づく）
    symbols = []
    for _, row in df.iterrows():
        try:
            # 銘柄コードの取得（JPXの場合は'コード'列）
            code = None
            if 'コード' in df.columns:
                code = str(row['コード']).strip()

            # 銘柄名の取得（JPXの場合は'銘柄名'列）
            name = None
            if '銘柄名' in df.columns:
                name = str(row['銘柄名']).strip()

            # 市場区分の取得（JPXの場合は'市場・商品区分'列）
            market = None
            if '市場・商品区分' in df.columns:
                market = str(row['市場・商品区分']).strip()

            if not code or not name or code == 'nan' or name == 'nan':
                continue

            # Prime市場のフィルタリング
            if market and ('プライム' in market or 'Prime' in market):
                # REITの除外（オプション）
                if not include_reit and ('REIT' in name or 'リート' in name or '投資法人' in name):
                    continue

                # 4桁の銘柄コードのみ（ETFやREIT等を除外）
                try:
                    code_num = int(code)
                    if 1000 <= code_num <= 9999:
                        symbols.append({
                            'code': str(code_num).zfill(4),  # 4桁に正規化
                            'name': name,
                            'market': market
                        })
                except ValueError:
                    continue

        except Exception as e:
            logger.debug(f"行処理エラー: {e}")
            continue

    return symbols


def format_symbols(symbols: List[Dict[str, Any]], format_type: str) -> List[str]:
    """銘柄リストのフォーマット"""
    formatted = []

    for symbol in symbols:
        code = symbol['code']

        if format_type == "yfinance":
            # yfinance形式: XXXX.T
            formatted.append(f"{code}.T")
        else:
            # raw形式: XXXX
            formatted.append(code)

    return sorted(formatted)


def save_symbols_csv(symbols: List[str], output_path: Path, dry_run: bool = False) -> None:
    """銘柄リストをCSVファイルに保存"""
    if dry_run:
        logger.info(f"DRY RUN: {len(symbols)}銘柄を{output_path}に保存予定")
        logger.info(f"サンプル: {symbols[:10]}")
        return

    # ディレクトリ作成
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # CSVファイル作成
    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # ヘッダー
        writer.writerow(['symbol'])

        # データ
        for symbol in symbols:
            writer.writerow([symbol])

    logger.info(f"銘柄リスト保存完了: {output_path} ({len(symbols)}銘柄)")


def main() -> None:
    args = parse_args()

    try:
        # JPXデータ取得
        df = fetch_jpx_data()

        # Prime銘柄フィルタリング
        symbols_data = filter_prime_symbols(df, args.include_reit)
        logger.info(f"Prime市場銘柄: {len(symbols_data)}銘柄")

        # フォーマット変換
        formatted_symbols = format_symbols(symbols_data, args.format)

        # CSV保存
        save_symbols_csv(formatted_symbols, args.output, args.dry_run)

        # サマリー表示
        logger.info(f"生成完了: {len(formatted_symbols)}銘柄")
        if formatted_symbols:
            logger.info(f"サンプル: {formatted_symbols[:5]}")

    except Exception as e:
        logger.error(f"銘柄リスト生成失敗: {e}")
        raise


if __name__ == "__main__":
    main()