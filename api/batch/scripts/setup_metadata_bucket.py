#!/usr/bin/env python3
"""
InfluxDBメタデータバケット作成・セクター情報投入スクリプト
"""
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

from influxdb_client_3 import InfluxDBClient3, WriteOptions, write_client_options
from batch.config.loader import load_influx_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class MetadataBucketManager:
    """InfluxDBメタデータバケット管理クラス"""

    def __init__(self):
        self.config = load_influx_config()
        self.client = InfluxDBClient3(
            host=self.config.host,
            token=self.config.token,
            org=self.config.org,
            timeout=30_000,
            max_retries=self.config.max_retries
        )
        self.metadata_bucket = "metadata_static"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """接続クローズ"""
        if self.client:
            self.client.close()

    def check_bucket_exists(self) -> bool:
        """メタデータバケットの存在確認"""
        try:
            # バケット一覧を取得して確認
            # InfluxDB Cloud Serverlessではバケット管理APIが制限されているため
            # 実際にクエリを実行して存在確認
            test_query = f"SELECT COUNT(*) FROM symbol_info"
            result = self.client.query(test_query, database=self.metadata_bucket, mode="pandas")
            logger.info(f"メタデータバケット '{self.metadata_bucket}' が存在します")
            return True
        except Exception as e:
            logger.info(f"メタデータバケット '{self.metadata_bucket}' が存在しません: {str(e)}")
            return False

    def create_bucket_note(self):
        """バケット作成の注意事項を表示"""
        logger.info("=" * 60)
        logger.info("InfluxDB Cloud Serverlessバケット作成")
        logger.info("=" * 60)
        logger.info("InfluxDB Cloud Serverlessでは、バケットをWeb UIから手動作成する必要があります：")
        logger.info("")
        logger.info("1. InfluxDB Cloud にログイン")
        logger.info("2. Load Data → Buckets → Create Bucket")
        logger.info(f"3. バケット名: {self.metadata_bucket}")
        logger.info("4. 保持期間: Never (静的データのため永続保存)")
        logger.info("5. Create Bucket をクリック")
        logger.info("")
        logger.info("バケット作成後、このスクリプトを再実行してください。")
        logger.info("=" * 60)

    def load_sector_data(self, csv_path: str) -> List[Dict]:
        """CSVファイルからセクター情報を読み込み"""
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"セクターマップファイルが見つかりません: {csv_path}")

        df = pd.read_csv(csv_path)
        logger.info(f"セクター情報読み込み: {len(df)}銘柄")

        # InfluxDB用のデータ形式に変換
        sector_data = []
        for _, row in df.iterrows():
            record = {
                "measurement": "symbol_info",
                "tags": {
                    "symbol": row["symbol"],
                    "market": "TSE_PRIME"
                },
                "fields": {
                    "sector": row["sector"],
                    "industry": row["industry"],
                    "raw_sector": row["raw_sector"]
                },
                "time": datetime.utcnow()
            }
            sector_data.append(record)

        return sector_data

    def write_sector_data(self, sector_data: List[Dict]) -> bool:
        """セクター情報をInfluxDBに書き込み"""
        try:
            logger.info(f"セクター情報をInfluxDBに書き込み開始: {len(sector_data)}件")

            # バッチ書き込み設定
            write_options = WriteOptions(
                batch_size=100,
                flush_interval=10_000,
                jitter_interval=2_000,
                retry_interval=5_000,
                max_retries=3
            )

            # Point形式に変換して書き込み
            points = []
            for record in sector_data:
                # InfluxDB Line Protocolフォーマット
                tags_str = ",".join([f"{k}={v}" for k, v in record["tags"].items()])
                fields_str = ",".join([f"{k}=\"{v}\"" for k, v in record["fields"].items()])
                timestamp = int(record["time"].timestamp() * 1000000000)  # ナノ秒

                line = f"{record['measurement']},{tags_str} {fields_str} {timestamp}"
                points.append(line)

            # バッチごとに書き込み
            batch_size = 50
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                batch_data = "\n".join(batch)

                self.client.write(
                    database=self.metadata_bucket,
                    record=batch_data,
                    write_precision="ns"
                )

                logger.info(f"バッチ書き込み完了: {i + len(batch)}/{len(points)}")

            logger.info("セクター情報の書き込み完了")
            return True

        except Exception as e:
            logger.error(f"セクター情報書き込みエラー: {str(e)}")
            return False

    def verify_data(self) -> bool:
        """書き込んだデータの検証"""
        try:
            # 件数確認
            count_query = "SELECT COUNT(*) as count FROM symbol_info"
            count_result = self.client.query(count_query, database=self.metadata_bucket, mode="pandas")
            count = count_result["count"].iloc[0] if not count_result.empty else 0

            logger.info(f"書き込み済みレコード数: {count}件")

            # セクター分布確認
            sector_query = """
            SELECT sector, COUNT(*) as count
            FROM symbol_info
            GROUP BY sector
            ORDER BY count DESC
            """
            sector_result = self.client.query(sector_query, database=self.metadata_bucket, mode="pandas")

            if not sector_result.empty:
                logger.info("セクター分布:")
                for _, row in sector_result.iterrows():
                    logger.info(f"  {row['sector']}: {row['count']}銘柄")

            # サンプルデータ確認
            sample_query = """
            SELECT symbol, sector, industry
            FROM symbol_info
            LIMIT 5
            """
            sample_result = self.client.query(sample_query, database=self.metadata_bucket, mode="pandas")

            if not sample_result.empty:
                logger.info("サンプルデータ:")
                for _, row in sample_result.iterrows():
                    logger.info(f"  {row['symbol']}: {row['sector']} / {row['industry']}")

            return count > 0

        except Exception as e:
            logger.error(f"データ検証エラー: {str(e)}")
            return False


def main():
    """メイン処理"""
    base_dir = Path(__file__).parent.parent
    sector_csv_path = base_dir / "data" / "sector_map.csv"

    try:
        with MetadataBucketManager() as manager:
            # バケット存在確認
            if not manager.check_bucket_exists():
                manager.create_bucket_note()
                return

            # セクター情報読み込み
            logger.info("セクター情報をCSVから読み込み中...")
            sector_data = manager.load_sector_data(str(sector_csv_path))

            # InfluxDBに書き込み
            logger.info("InfluxDBへの書き込み開始...")
            if manager.write_sector_data(sector_data):
                logger.info("書き込み成功")

                # データ検証
                logger.info("データ検証中...")
                if manager.verify_data():
                    logger.info("✅ メタデータバケットのセットアップ完了")
                else:
                    logger.error("❌ データ検証に失敗")
            else:
                logger.error("❌ データ書き込みに失敗")

    except Exception as e:
        logger.error(f"処理エラー: {str(e)}")


if __name__ == "__main__":
    main()