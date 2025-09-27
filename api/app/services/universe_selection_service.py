"""Universe selection domain service extracted from the batch CLI."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from batch.config.loader import load_influx_config, load_universe_settings
from batch.pipeline.metrics import InfluxMarketDataClient, SymbolMetrics, calculate_symbol_metrics, load_metric_config
from batch.pipeline.score_universe import calculate_scores, load_sector_map, load_universe_settings_struct, select_universe
from batch.pipeline.supabase_sector_loader import load_symbols_from_supabase


class UniverseSelectionError(RuntimeError):
    """Raised when the universe selection flow cannot complete."""


@dataclass(slots=True)
class UniverseSelectionRequest:
    """Input parameters for universe selection."""

    settings_path: Path
    market: str = "TSE_PRIME"
    symbol_source: str = "supabase"
    symbols: Optional[Sequence[str]] = None
    existing_core: Sequence[str] = field(default_factory=list)
    thresholds_override: Optional[Dict[str, float]] = None


@dataclass(slots=True)
class UniverseSelectionResult:
    """Result payload returned by :class:`UniverseSelectionService`."""

    core: List[str]
    bench: List[str]
    snapshot_rows: List[Dict[str, object]]
    total_symbols: int
    filtered_symbols: int
    applied_thresholds: Dict[str, float]
    scores: Dict[str, float]
    breakdown: Dict[str, Dict[str, float]]


class UniverseSelectionService:
    """Orchestrates the multi-step universe selection pipeline."""

    def __init__(self, market_data_client_cls=InfluxMarketDataClient) -> None:
        self._market_data_client_cls = market_data_client_cls

    def run_selection(self, request: UniverseSelectionRequest) -> UniverseSelectionResult:
        settings_raw = load_universe_settings(request.settings_path)
        metric_config = load_metric_config(settings_raw)
        universe_settings = load_universe_settings_struct(settings_raw)

        thresholds = dict(settings_raw.get("thresholds", {}))
        if request.thresholds_override:
            thresholds.update(request.thresholds_override)

        symbols = self._resolve_symbols(request)
        if not symbols:
            raise UniverseSelectionError("No symbols available for universe selection")

        influx_config = load_influx_config()
        with self._market_data_client_cls(influx_config) as client:
            metrics = calculate_symbol_metrics(client, symbols, metric_config)

        filtered_metrics = self._apply_hard_filters(metrics, thresholds)
        if not filtered_metrics:
            raise UniverseSelectionError("No symbols passed the hard filters")

        scores, breakdown = calculate_scores(
            filtered_metrics,
            universe_settings.weights,
            metric_config,
        )

        sector_map = load_sector_map(universe_settings.sector_cap.definition_path)
        selection = select_universe(
            scores,
            universe_settings,
            list(request.existing_core),
            sector_map,
        )

        snapshot_rows = self._build_snapshot_rows(filtered_metrics, scores, breakdown)

        return UniverseSelectionResult(
            core=list(selection["core"]),
            bench=list(selection["bench"]),
            snapshot_rows=snapshot_rows,
            total_symbols=len(symbols),
            filtered_symbols=len(filtered_metrics),
            applied_thresholds=thresholds,
            scores=scores,
            breakdown=breakdown,
        )

    def _resolve_symbols(
        self,
        request: UniverseSelectionRequest,
    ) -> List[str]:
        if request.symbols:
            return list(dict.fromkeys(str(symbol) for symbol in request.symbols))

        if request.symbol_source == "supabase":
            symbols = load_symbols_from_supabase(request.market)
            return list(dict.fromkeys(symbols))

        raise UniverseSelectionError(
            "symbols must be provided when symbol_source is not 'supabase'",
        )

    @staticmethod
    def _apply_hard_filters(
        metrics: Dict[str, SymbolMetrics],
        thresholds: Dict[str, float],
    ) -> Dict[str, SymbolMetrics]:
        filtered: Dict[str, SymbolMetrics] = {}
        adv_min = float(thresholds.get("adv_jpy_min", 0))
        price_min = float(thresholds.get("price_min", 0))
        price_max = float(thresholds.get("price_max", float("inf")))
        atr_min = float(thresholds.get("atr_pct_min", 0))
        atr_max = float(thresholds.get("atr_pct_max", float("inf")))
        zero_ratio_max = float(thresholds.get("zero_volume_ratio_max", 1))

        for symbol, metric in metrics.items():
            if metric.adv_jpy < adv_min:
                continue
            if not (price_min <= metric.latest_close <= price_max):
                continue
            if metric.atr_pct is None or not (atr_min <= metric.atr_pct <= atr_max):
                continue
            if metric.no_trade_5m_ratio > zero_ratio_max:
                continue
            filtered[symbol] = metric

        return filtered

    @staticmethod
    def _build_snapshot_rows(
        metrics: Dict[str, SymbolMetrics],
        scores: Dict[str, float],
        breakdown: Dict[str, Dict[str, float]],
    ) -> List[Dict[str, object]]:
        snapshot_rows: List[Dict[str, object]] = []
        for symbol, metric in metrics.items():
            row: Dict[str, object] = {
                "symbol": symbol,
                "latest_close": metric.latest_close,
                "adv_jpy": metric.adv_jpy,
                "atr_pct": metric.atr_pct,
                "median_5m_range_bps": metric.median_5m_range_bps,
                "close_5m_vol_share": metric.close_5m_vol_share,
                "no_trade_5m_ratio": metric.no_trade_5m_ratio,
                "score": scores.get(symbol, 0.0),
                "score_total": breakdown.get(symbol, {}).get(
                    "total",
                    scores.get(symbol, 0.0),
                ),
            }
            row.update(
                {
                    f"score_{component}": value
                    for component, value in breakdown.get(symbol, {}).items()
                    if component != "total"
                }
            )
            snapshot_rows.append(row)
        return snapshot_rows


__all__ = [
    "UniverseSelectionError",
    "UniverseSelectionRequest",
    "UniverseSelectionResult",
    "UniverseSelectionService",
]
