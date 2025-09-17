"""ユニバース選定で使用する指標計算のスケルトン実装。

MVPではInfluxDBからのデータ取得や計算処理を実装予定。
このファイルは設定テンプレート（universe_settings.example.toml）を
参照しつつ、必要な関数のインターフェースを定義している。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Protocol


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
    """主要指標を計算し SymbolMetrics を返す。"""
    # TODO: InfluxDBからのデータ取得と本実装を追加
    _ = data_client, symbols, metric_config  # unused placeholder
    raise NotImplementedError("InfluxDBとの連携を実装してください")


def calculate_volatility_score(metric: SymbolMetrics, config: MetricConfig) -> float:
    """ATR%がターゲットにどれだけ近いかをスコア化する。"""
    diff = abs(metric.atr_pct - config.target_atr_pct)
    normalized = diff / config.atr_tolerance
    return max(0.0, min(1.0, 1.0 - normalized))
