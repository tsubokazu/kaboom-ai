"""Supabase統合ローダー."""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - supabase未インストール環境
    create_client = None  # type: ignore
    Client = object  # type: ignore
    logger.warning("supabase-py not found. Using CSV fallback only.")


def _create_supabase_client() -> Client | None:
    """環境変数からSupabaseクライアントを生成"""
    if create_client is None:
        return None

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SECRET_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )

    if not supabase_url or not supabase_key:
        logger.warning("Supabase環境変数が未設定。CSVフォールバックを使用")
        return None

    try:
        return create_client(supabase_url, supabase_key)
    except Exception as exc:  # pragma: no cover - ネットワーク系例外
        logger.error("Supabaseクライアント作成に失敗しました: %s", exc)
        return None


def load_sector_map_from_supabase() -> Dict[str, str]:
    """Supabaseのsymbol_metadataテーブルからセクターマップを取得"""
    client = _create_supabase_client()
    if client is None:
        return {}

    try:
        response = (
            client.table("symbol_metadata")
            .select("symbol,sector")
            .neq("symbol", None)
            .execute()
        )
    except Exception as exc:  # pragma: no cover - API失敗
        logger.error("Supabaseセクター取得エラー: %s", exc)
        return {}

    data = getattr(response, "data", None) or []
    if not data:
        logger.warning("Supabaseからセクターデータが取得できませんでした")
        return {}

    mapping = {
        str(record.get("symbol")).strip(): str(record.get("sector")).strip()
        for record in data
        if record.get("symbol") and record.get("sector")
    }
    logger.info("Supabaseからセクター情報取得: %d銘柄", len(mapping))
    return mapping


def load_sector_map_csv_fallback(csv_path: str) -> Dict[str, str]:
    """CSVフォールバック版セクターローダー"""
    try:
        import pandas as pd
        from pathlib import Path

        if not csv_path:
            return {}

        sector_path = Path(csv_path)
        if not sector_path.exists():
            logger.warning(f"CSVファイルが見つかりません: {csv_path}")
            return {}

        df = pd.read_csv(sector_path)
        if "symbol" not in df.columns or "sector" not in df.columns:
            logger.warning("CSVファイルに必要なカラムがありません")
            return {}

        mapping = {
            str(row.symbol).strip(): str(row.sector).strip()
            for row in df.itertuples(index=False)
        }

        logger.info(f"CSVからセクター情報取得: {len(mapping)}銘柄")
        return mapping

    except Exception as e:
        logger.error(f"CSVセクター取得エラー: {str(e)}")
        return {}


def load_sector_map_smart(csv_fallback_path: Optional[str] = None) -> Dict[str, str]:
    """
    スマートセクターローダー：Supabase優先、CSVフォールバック

    Args:
        csv_fallback_path: CSVファイルパス（フォールバック用）

    Returns:
        セクターマッピング辞書 {symbol: sector}
    """
    # 1. Supabaseから取得試行
    sector_map = load_sector_map_from_supabase()

    # 2. 成功した場合はそのまま返す
    if sector_map:
        return sector_map

    # 3. 失敗した場合はCSVフォールバック
    if csv_fallback_path:
        logger.info("Supabase取得失敗。CSVフォールバックを使用")
        return load_sector_map_csv_fallback(csv_fallback_path)

    # 4. どちらも失敗
    logger.warning("セクター情報の取得に失敗しました")
    return {}


# 後方互換性のためのエイリアス
def load_sector_map(path: str | None) -> Dict[str, str]:
    """後方互換性のための関数"""
    return load_sector_map_smart(path)


def load_symbols_from_supabase(market: Optional[str] = None) -> List[str]:
    """Supabaseのsymbol_metadataから銘柄コード一覧を取得"""
    client = _create_supabase_client()
    if client is None:
        return []

    try:
        query = client.table("symbol_metadata").select("symbol,market")
        if market:
            query = query.eq("market", market)
        response = query.neq("symbol", None).execute()
    except Exception as exc:  # pragma: no cover
        logger.error("Supabase銘柄取得エラー: %s", exc)
        return []

    data = getattr(response, "data", None) or []
    symbols = {
        str(record.get("symbol")).strip()
        for record in data
        if record.get("symbol")
    }

    result = sorted(symbol for symbol in symbols if symbol)
    if not result:
        logger.warning("Supabaseから有効な銘柄が取得できませんでした")
    else:
        logger.info("Supabaseから銘柄リスト取得: %d件", len(result))
    return result
