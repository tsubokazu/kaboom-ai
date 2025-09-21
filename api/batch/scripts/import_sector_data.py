#!/usr/bin/env python3
"""
セクターデータCSVからSupabaseのsymbol_metadataテーブルへのデータ投入スクリプト
"""

import csv
import sys
import os
from typing import List, Dict, Any

# パスを追加してSupabaseクライアントにアクセス
sys.path.append('/Users/kazusa/Develop/kaboom/api')

from app.core.supabase import get_supabase_client

def read_csv_data(file_path: str) -> List[Dict[str, Any]]:
    """CSVファイルを読み込んでディクショナリのリストを返す"""
    data = []

    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append({
                'symbol': row['symbol'],
                'sector': row['sector'],
                'industry': row['industry'],
                'raw_sector': row['raw_sector'],
                'market': 'TSE_PRIME'  # デフォルト値
            })

    return data

def create_batch_insert_sql(batch_data: List[Dict[str, Any]]) -> str:
    """バッチデータからINSERT SQLを生成"""

    values_list = []
    for row in batch_data:
        # SQLインジェクション対策のためシングルクォートをエスケープ
        symbol = row['symbol'].replace("'", "''")
        sector = row['sector'].replace("'", "''")
        industry = row['industry'].replace("'", "''")
        raw_sector = row['raw_sector'].replace("'", "''")
        market = row['market'].replace("'", "''")

        values_list.append(f"('{symbol}', '{sector}', '{industry}', '{raw_sector}', '{market}')")

    values_str = ',\n    '.join(values_list)

    sql = f"""
INSERT INTO symbol_metadata (symbol, sector, industry, raw_sector, market)
VALUES
    {values_str}
ON CONFLICT (symbol) DO UPDATE SET
    sector = EXCLUDED.sector,
    industry = EXCLUDED.industry,
    raw_sector = EXCLUDED.raw_sector,
    market = EXCLUDED.market,
    updated_at = now();
"""

    return sql

def main():
    """メイン処理"""
    csv_file_path = '/Users/kazusa/Develop/kaboom/batch/data/sector_map.csv'

    print("CSVファイルからデータを読み込み中...")
    data = read_csv_data(csv_file_path)
    print(f"読み込み完了: {len(data)}件のレコード")

    # バッチサイズ（100件ずつ処理）
    batch_size = 100
    total_inserted = 0

    # Supabaseクライアントを取得
    supabase = get_supabase_client()

    print(f"バッチ処理開始（バッチサイズ: {batch_size}）...")

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        print(f"バッチ {batch_num}: {len(batch)}件処理中...")

        # SQLを生成
        sql = create_batch_insert_sql(batch)

        try:
            # SQLを実行
            result = supabase.rpc('execute_sql_command', {'sql_command': sql}).execute()
            total_inserted += len(batch)
            print(f"バッチ {batch_num}: 完了 ({total_inserted}/{len(data)})")

        except Exception as e:
            print(f"バッチ {batch_num}: エラー - {str(e)}")
            return False

    print(f"全データ投入完了: {total_inserted}件")

    # 投入確認
    print("投入結果を確認中...")
    count_result = supabase.rpc('execute_sql_command', {
        'sql_command': 'SELECT COUNT(*) as count FROM symbol_metadata;'
    }).execute()

    if count_result.data:
        actual_count = count_result.data[0]['count']
        print(f"テーブル内レコード数: {actual_count}件")

        if actual_count == len(data):
            print("✅ 全データの投入が正常に完了しました！")
        else:
            print(f"⚠️ データ数が一致しません。期待値: {len(data)}, 実際: {actual_count}")

    return True

if __name__ == "__main__":
    main()