"""ユニバース選定に必要な指標計算ロジック。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, Iterable, List, Protocol

import numpy as np
import pandas as pd
from influxdb_client_3 import InfluxDBClient3

from batch.config.loader import InfluxConfig


@dataclass
class MetricConfig:
    """スコアリング指標計算のための設定値。"""

    target_atr_pct: float
    atr_tolerance: float
    ranking_pool_size: int
    close_volume_window_days: int
    use_efficiency_ratio: bool
    use_orb_follow_through: bool
    use_vwap_persistence: bool


@dataclass
class SymbolMetrics:
    """単一銘柄の計算済み指標を保持するデータ構造。"""

    symbol: str
    latest_close: float
    adv_jpy: float
    atr_pct: float
    median_5m_range_bps: float
    close_5m_vol_share: float
    no_trade_5m_ratio: float
    efficiency_ratio: float | None = None
    orb_follow_through: float | None = None
    vwap_persistence: float | None = None


class MarketDataClient(Protocol):
    """必要なデータをInfluxDB等から取得するためのプロトコル。"""

    def fetch_intraday_metrics(
        self, symbols: Iterable[str], window_days: int
    ) -> Dict[str, Dict[str, float]]:
        """対象銘柄の5分足集計や出来高指標を取得する。"""

    def fetch_daily_metrics(
        self, symbols: Iterable[str], window_days: int
    ) -> Dict[str, Dict[str, float]]:
        """日足ベースのATRやADVなどを取得する。"""


class InfluxMarketDataClient:
    """InfluxDB v3 から株価データを取得するクライアント。"""

    def __init__(self, config: InfluxConfig) -> None:
        self._config = config
        self._client = InfluxDBClient3(
            host=config.host,
            token=config.token,
            org=config.org,
            timeout=30_000,
            max_retries=config.max_retries,
        )

    def __enter__(self) -> InfluxMarketDataClient:
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:  # pragma: no cover - resource cleanup
        self.close()

    def close(self) -> None:
        self._client.close()

    def fetch_daily_metrics(
        self, symbols: Iterable[str], window_days: int
    ) -> Dict[str, pd.DataFrame]:
        symbols_list = [s for s in symbols]
        if not symbols_list:
            return {}

        sql_template = (
            "SELECT time, symbol, close, high, low, volume FROM ohlcv_1d "
            "WHERE symbol IN ({symbols}) AND time >= now() - INTERVAL '{days} days' "
            "ORDER BY symbol, time"
        )

        data: Dict[str, pd.DataFrame] = {}
        chunk_size = 200
        for idx in range(0, len(symbols_list), chunk_size):
            chunk = symbols_list[idx : idx + chunk_size]
            placeholders = ",".join(f"'{symbol}'" for symbol in chunk)
            sql = sql_template.format(symbols=placeholders, days=int(window_days))
            df = self._client.query(sql, database=self._config.bucket_agg_1d, mode="pandas")
            if df is None or df.empty:
                continue
            df = df.rename(columns=str.lower)
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df = df.sort_values(["symbol", "time"])
            for symbol, group in df.groupby("symbol"):
                group = group.set_index("time")
                data[symbol] = group[["close", "high", "low", "volume"]]
        return data

    def fetch_intraday_metrics(
        self, symbols: Iterable[str], window_days: int
    ) -> Dict[str, pd.DataFrame]:
        symbols_list = [s for s in symbols]
        if not symbols_list:
            return {}

        sql_template = (
            "SELECT time, symbol, close, high, low, volume FROM ohlcv_5m "
            "WHERE symbol IN ({symbols}) AND time >= now() - INTERVAL '{days} days' "
            "ORDER BY symbol, time"
        )

        data: Dict[str, pd.DataFrame] = {}
        chunk_size = 60
        for idx in range(0, len(symbols_list), chunk_size):
            chunk = symbols_list[idx : idx + chunk_size]
            placeholders = ",".join(f"'{symbol}'" for symbol in chunk)
            sql = sql_template.format(symbols=placeholders, days=int(window_days))
            df = self._client.query(sql, database=self._config.bucket_agg_5m, mode="pandas")
            if df is None or df.empty:
                continue
            df = df.rename(columns=str.lower)
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df = df.sort_values(["symbol", "time"])
            for symbol, group in df.groupby("symbol"):
                group = group.set_index("time")
                data[symbol] = group[["close", "high", "low", "volume"]]
        return data


def load_metric_config(config: Dict[str, Dict[str, object]]) -> MetricConfig:
    """設定辞書から MetricConfig を生成する。"""
    params = config["scoring"]["parameters"]
    return MetricConfig(
        target_atr_pct=float(params["target_atr_pct"]),
        atr_tolerance=float(params["atr_tolerance"]),
        ranking_pool_size=int(params["ranking_pool_size"]),
        close_volume_window_days=int(params["close_volume_window_days"]),
        use_efficiency_ratio=bool(params["use_efficiency_ratio"]),
        use_orb_follow_through=bool(params["use_orb_follow_through"]),
        use_vwap_persistence=bool(params["use_vwap_persistence"]),
    )


def calculate_symbol_metrics(
    data_client: MarketDataClient,
    symbols: Iterable[str],
    metric_config: MetricConfig,
) -> Dict[str, SymbolMetrics]:
    """InfluxDBからデータを取得し主要指標を計算する。"""

    # 日足データは全銘柄で取得し、ベース指標を計算
    daily_window = max(60, metric_config.close_volume_window_days, 30)
    daily_data = data_client.fetch_daily_metrics(symbols, daily_window)

    base_metrics: Dict[str, Dict[str, float]] = {}
    for symbol, df in daily_data.items():
        if len(df) < 20:
            continue
        close = df["close"].astype(float)
        volume = df["volume"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        trading_value = (close * volume).tail(20)
        adv_jpy = float(trading_value.mean()) if not trading_value.empty else 0.0

        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1] if len(tr) >= 14 else np.nan
        latest_close = float(close.iloc[-1]) if not close.empty else np.nan
        atr_pct = float(atr / latest_close) if latest_close and not np.isnan(atr) else np.nan

        base_metrics[symbol] = {
            "adv_jpy": float(adv_jpy) if not np.isnan(adv_jpy) else 0.0,
            "atr_pct": atr_pct if not np.isnan(atr_pct) else np.nan,
            "latest_close": latest_close,
        }

    adv_sorted = sorted(
        base_metrics.items(), key=lambda item: item[1]["adv_jpy"], reverse=True
    )
    pool_size = max(metric_config.ranking_pool_size, 1)
    intraday_symbols = [
        symbol for symbol, meta in adv_sorted if meta["adv_jpy"] > 0
    ][:pool_size]

    if not intraday_symbols:
        return {}

    intraday_data = data_client.fetch_intraday_metrics(
        intraday_symbols, metric_config.close_volume_window_days
    )

    tz_local = "Asia/Tokyo"
    close_cut = time(14, 55)
    results: Dict[str, SymbolMetrics] = {}

    for symbol in intraday_symbols:
        meta = base_metrics[symbol]
        df_intra = intraday_data.get(symbol)
        if df_intra is None or df_intra.empty:
            continue

        df_intra = df_intra.copy()
        df_intra[["high", "low", "close", "volume"]] = df_intra[[
            "high",
            "low",
            "close",
            "volume",
        ]].astype(float)

        denom = df_intra["close"].replace(0, np.nan)
        range_bps = ((df_intra["high"] - df_intra["low"]) / denom).abs() * 1e4
        median_range_bps = float(range_bps.median(skipna=True)) if not range_bps.empty else np.nan

        df_intra["volume"] = df_intra["volume"].fillna(0)
        local_time = df_intra.index.tz_convert(tz_local)
        df_intra["local_time"] = local_time
        df_intra["local_date"] = local_time.date

        grouped = df_intra.groupby("local_date")
        vol_share_values = []
        for _, group in grouped:
            total_vol = group["volume"].sum()
            if total_vol <= 0:
                vol_share_values.append(0.0)
                continue
            close_slice = group[group["local_time"].dt.time >= close_cut]
            vol_share_values.append(float(close_slice["volume"].sum() / total_vol))
        close_vol_share = float(np.mean(vol_share_values)) if vol_share_values else 0.0

        zero_ratio = float((df_intra["volume"] <= 0).mean()) if not df_intra.empty else 1.0

        results[symbol] = SymbolMetrics(
            symbol=symbol,
            latest_close=meta["latest_close"],
            adv_jpy=meta["adv_jpy"],
            atr_pct=meta["atr_pct"],
            median_5m_range_bps=median_range_bps if not np.isnan(median_range_bps) else np.nan,
            close_5m_vol_share=close_vol_share,
            no_trade_5m_ratio=zero_ratio,
            efficiency_ratio=None,
            orb_follow_through=None,
            vwap_persistence=None,
        )

    return results


def calculate_volatility_score(metric: SymbolMetrics, config: MetricConfig) -> float:
    """ATR%がターゲットにどれだけ近いかをスコア化する。"""
    diff = abs(metric.atr_pct - config.target_atr_pct)
    normalized = diff / config.atr_tolerance
    return max(0.0, min(1.0, 1.0 - normalized))
