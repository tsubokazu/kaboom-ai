#!/usr/bin/env python3
"""
東証Prime全銘柄のセクター情報をyfinanceから取得してCSVファイルを生成
"""
import pandas as pd
import yfinance as yf
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_symbols(csv_path: str) -> List[str]:
    """銘柄リストをCSVから読み込み"""
    df = pd.read_csv(csv_path)
    symbols = df.iloc[:, 0].tolist()  # 最初の列をシンボルとして取得
    logger.info(f"銘柄リスト読み込み: {len(symbols)}銘柄")
    return symbols


def get_sector_info(symbol: str) -> Optional[Dict[str, str]]:
    """単一銘柄のセクター・業界情報を取得"""
    try:
        ticker = yf.Ticker(symbol)

        # 基本情報を取得
        info = ticker.info

        # セクター・業界情報を抽出
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')

        # よりシンプルなセクター分類にマッピング
        sector_mapping = {
            'Technology': 'Technology',
            'Communication Services': 'Communication',
            'Financial Services': 'Financial',
            'Consumer Cyclical': 'Consumer',
            'Consumer Defensive': 'Consumer',
            'Healthcare': 'Healthcare',
            'Industrials': 'Industrial',
            'Basic Materials': 'Materials',
            'Energy': 'Energy',
            'Utilities': 'Utilities',
            'Real Estate': 'RealEstate'
        }

        simplified_sector = sector_mapping.get(sector, 'Other')

        return {
            'symbol': symbol,
            'sector': simplified_sector,
            'industry': industry,
            'raw_sector': sector
        }

    except Exception as e:
        logger.warning(f"セクター情報取得失敗 {symbol}: {str(e)}")
        return {
            'symbol': symbol,
            'sector': 'Unknown',
            'industry': 'Unknown',
            'raw_sector': 'Unknown'
        }


def batch_get_sectors(symbols: List[str], batch_size: int = 50, delay: float = 1.0) -> List[Dict[str, str]]:
    """バッチでセクター情報を取得"""
    results = []
    total_batches = (len(symbols) + batch_size - 1) // batch_size

    for i in range(0, len(symbols), batch_size):
        batch_num = i // batch_size + 1
        batch = symbols[i:i + batch_size]

        logger.info(f"バッチ {batch_num}/{total_batches} 開始: {len(batch)}銘柄")
        logger.info(f"  銘柄例: {batch[:3]}...")

        for symbol in batch:
            sector_info = get_sector_info(symbol)
            if sector_info:
                results.append(sector_info)
                if len(results) % 10 == 0:
                    logger.info(f"  進行: {len(results)}/{len(symbols)} 完了")

            # API制限対策で少し待機
            time.sleep(0.1)

        logger.info(f"  バッチ完了: {len(batch)}銘柄処理")

        # バッチ間の待機
        if batch_num < total_batches:
            logger.info(f"  {delay}秒待機...")
            time.sleep(delay)

    return results


def save_sector_map(sector_data: List[Dict[str, str]], output_path: str):
    """セクターマップをCSVファイルに保存"""
    df = pd.DataFrame(sector_data)

    # CSVに保存
    df.to_csv(output_path, index=False)
    logger.info(f"セクターマップ保存: {output_path}")

    # セクター分布を表示
    sector_counts = df['sector'].value_counts()
    logger.info("セクター分布:")
    for sector, count in sector_counts.items():
        logger.info(f"  {sector}: {count}銘柄")

    # 統計情報をJSONでも保存
    stats = {
        'total_symbols': len(df),
        'sector_distribution': sector_counts.to_dict(),
        'unknown_count': len(df[df['sector'] == 'Unknown'])
    }

    stats_path = output_path.replace('.csv', '_stats.json')
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    logger.info(f"統計情報保存: {stats_path}")


def main():
    """メイン処理"""
    # パス設定
    base_dir = Path(__file__).parent.parent
    symbols_path = base_dir / "data" / "symbols_prime.csv"
    output_path = base_dir / "data" / "sector_map.csv"

    try:
        # 銘柄リスト読み込み
        symbols = load_symbols(str(symbols_path))

        # 全銘柄での本格実行
        logger.info(f"全銘柄実行: {len(symbols)}銘柄でセクター情報を取得")

        # セクター情報をバッチで取得
        sector_data = batch_get_sectors(
            symbols,
            batch_size=50,  # 効率的なバッチサイズ
            delay=1.5       # API制限を考慮した待機時間
        )

        if sector_data:
            # セクターマップを保存
            save_sector_map(sector_data, str(output_path))
            logger.info("セクター情報取得完了")
        else:
            logger.error("セクター情報が取得できませんでした")

    except Exception as e:
        logger.error(f"処理エラー: {str(e)}")


if __name__ == "__main__":
    main()