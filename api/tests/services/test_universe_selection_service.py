"""Unit tests for :mod:`app.services.universe_selection_service`."""
from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# The production module depends on ``influxdb_client_3`` which is heavy and not
# required for the unit tests. Provide a lightweight stub so the import succeeds
# without pulling the real dependency during test collection.
if "influxdb_client_3" not in sys.modules:  # pragma: no cover - import guard
    dummy_module = types.ModuleType("influxdb_client_3")

    class _DummyInfluxClient:  # pragma: no cover - simple stub
        def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - stub
            self.closed = False

        def close(self) -> None:  # pragma: no cover - simple stub
            self.closed = True

        def query(self, *args, **kwargs):  # pragma: no cover - simple stub
            return None

    dummy_module.InfluxDBClient3 = _DummyInfluxClient
    sys.modules["influxdb_client_3"] = dummy_module

from app.services.universe_selection_service import (
    UniverseSelectionError,
    UniverseSelectionRequest,
    UniverseSelectionResult,
    UniverseSelectionService,
)
from batch.pipeline.metrics import MetricConfig, SymbolMetrics
from batch.pipeline.score_universe import (
    HysteresisConfig,
    ScoringWeights,
    SectorCapConfig,
    UniverseSettings,
)


class _FakeMarketDataClient:
    """Minimal context manager compatible with :class:`UniverseSelectionService`."""

    def __init__(self, config) -> None:  # noqa: D401 - simple stub
        self.config = config
        self.entered = False
        self.exited = False

    def __enter__(self) -> "_FakeMarketDataClient":  # pragma: no cover - trivial
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:  # pragma: no cover - trivial
        self.exited = True

    def fetch_daily_metrics(self, symbols: Iterable[str], window_days: int) -> Dict[str, object]:  # noqa: D401 - stub
        return {}

    def fetch_intraday_metrics(self, symbols: Iterable[str], window_days: int) -> Dict[str, object]:  # noqa: D401 - stub
        return {}


@dataclass(slots=True)
class _DummyInfluxConfig:
    host: str = "localhost"
    org: str = "test"
    token: str = "test-token"
    bucket_raw_1m_hot: str = "hot"
    bucket_raw_1m_backfill: str = "backfill"
    bucket_agg_5m: str = "agg5m"
    bucket_agg_1d: str = "agg1d"
    write_batch_size: int = 10
    write_flush_interval_ms: int = 1000
    max_retries: int = 3
    retry_backoff_seconds: int = 5


def _setup_common_dependencies(monkeypatch):
    """Patch expensive loaders and return commonly reused objects."""
    import app.services.universe_selection_service as module

    raw_settings = {
        "thresholds": {
            "adv_jpy_min": 1_000_000,
            "price_min": 100,
            "price_max": 250,
            "atr_pct_min": 0.5,
            "atr_pct_max": 2.0,
            "zero_volume_ratio_max": 0.2,
        },
        "scoring": {
            "parameters": {
                "target_atr_pct": 1.0,
                "atr_tolerance": 0.5,
                "ranking_pool_size": 10,
                "close_volume_window_days": 30,
                "use_efficiency_ratio": False,
                "use_orb_follow_through": False,
                "use_vwap_persistence": False,
            }
        },
        "universe": {
            "core_size": 2,
            "bench_size": 1,
        },
    }

    metric_config = MetricConfig(
        target_atr_pct=1.0,
        atr_tolerance=0.5,
        ranking_pool_size=10,
        close_volume_window_days=30,
        use_efficiency_ratio=False,
        use_orb_follow_through=False,
        use_vwap_persistence=False,
    )

    weights = ScoringWeights(
        liquidity=0.4,
        volatility_fit=0.3,
        cost_efficiency=0.1,
        close_liquidity=0.1,
        zero_volume_penalty=0.1,
        extra={},
    )

    universe_settings = UniverseSettings(
        core_size=2,
        bench_size=1,
        weights=weights,
        hysteresis=HysteresisConfig(maintain_rank_max=2, add_rank_max=2),
        sector_cap=SectorCapConfig(max_ratio=0.6, definition_path="/tmp/sector.csv"),
    )

    monkeypatch.setattr(module, "load_universe_settings", lambda path: raw_settings)
    monkeypatch.setattr(module, "load_metric_config", lambda config: metric_config)
    monkeypatch.setattr(module, "load_universe_settings_struct", lambda config: universe_settings)

    return module, raw_settings, metric_config, universe_settings


def test_run_selection_supabase_flow_success(monkeypatch, tmp_path):
    module, _, metric_config, universe_settings = _setup_common_dependencies(monkeypatch)

    load_symbols_calls: List[str] = []
    monkeypatch.setattr(
        module,
        "load_symbols_from_supabase",
        lambda market: load_symbols_calls.append(market) or ["AAA", "BBB", "CCC", "AAA"],
    )
    monkeypatch.setattr(module, "load_influx_config", lambda: _DummyInfluxConfig())

    metrics = {
        "AAA": SymbolMetrics(
            symbol="AAA",
            latest_close=150.0,
            adv_jpy=2_000_000.0,
            atr_pct=0.8,
            median_5m_range_bps=12.0,
            close_5m_vol_share=0.35,
            no_trade_5m_ratio=0.05,
        ),
        "BBB": SymbolMetrics(
            symbol="BBB",
            latest_close=90.0,
            adv_jpy=500_000.0,
            atr_pct=0.7,
            median_5m_range_bps=18.0,
            close_5m_vol_share=0.25,
            no_trade_5m_ratio=0.03,
        ),
        "CCC": SymbolMetrics(
            symbol="CCC",
            latest_close=190.0,
            adv_jpy=3_000_000.0,
            atr_pct=1.5,
            median_5m_range_bps=14.0,
            close_5m_vol_share=0.28,
            no_trade_5m_ratio=0.04,
        ),
    }

    def fake_calculate_symbol_metrics(client, symbols, cfg):
        assert isinstance(client, _FakeMarketDataClient)
        assert symbols == ["AAA", "BBB", "CCC"]  # duplicates removed
        assert cfg is metric_config
        return metrics

    monkeypatch.setattr(module, "calculate_symbol_metrics", fake_calculate_symbol_metrics)

    breakdown = {"AAA": {"total": 0.9, "liquidity": 0.7}}

    def fake_calculate_scores(filtered_metrics, weights, cfg):
        # Only AAA survives the override
        assert set(filtered_metrics.keys()) == {"AAA"}
        assert weights is universe_settings.weights
        assert cfg is metric_config
        return {"AAA": 0.9}, breakdown

    monkeypatch.setattr(module, "calculate_scores", fake_calculate_scores)
    monkeypatch.setattr(module, "load_sector_map", lambda path: {"AAA": "TECH"})

    def fake_select_universe(scores, settings, existing_core, sector_map):
        assert scores == {"AAA": 0.9}
        assert existing_core == ["KEEP"]
        assert sector_map == {"AAA": "TECH"}
        assert settings is universe_settings
        return {"core": ["AAA"], "bench": []}

    monkeypatch.setattr(module, "select_universe", fake_select_universe)

    service = UniverseSelectionService(market_data_client_cls=_FakeMarketDataClient)
    request = UniverseSelectionRequest(
        settings_path=tmp_path / "settings.toml",
        market="TSE_PRIME",
        symbol_source="supabase",
        symbols=None,
        existing_core=["KEEP"],
        thresholds_override={"price_max": 180},
    )

    result = service.run_selection(request)

    assert load_symbols_calls == ["TSE_PRIME"]
    assert isinstance(result, UniverseSelectionResult)
    assert result.core == ["AAA"]
    assert result.bench == []
    assert result.total_symbols == 3
    assert result.filtered_symbols == 1
    assert result.applied_thresholds["price_max"] == 180
    assert result.scores == {"AAA": 0.9}
    assert result.breakdown == breakdown
    assert result.snapshot_rows == [
        {
            "symbol": "AAA",
            "latest_close": 150.0,
            "adv_jpy": 2_000_000.0,
            "atr_pct": 0.8,
            "median_5m_range_bps": 12.0,
            "close_5m_vol_share": 0.35,
            "no_trade_5m_ratio": 0.05,
            "score": 0.9,
            "score_total": 0.9,
            "score_liquidity": 0.7,
        }
    ]


def test_run_selection_raises_when_no_symbols(monkeypatch, tmp_path):
    module, _, _, _ = _setup_common_dependencies(monkeypatch)
    monkeypatch.setattr(module, "load_influx_config", lambda: _DummyInfluxConfig())
    monkeypatch.setattr(module, "load_symbols_from_supabase", lambda market: [])

    service = UniverseSelectionService(market_data_client_cls=_FakeMarketDataClient)
    request = UniverseSelectionRequest(settings_path=tmp_path / "settings.toml")

    with pytest.raises(UniverseSelectionError, match="No symbols available"):
        service.run_selection(request)


def test_run_selection_raises_when_all_filtered(monkeypatch, tmp_path):
    module, _, metric_config, _ = _setup_common_dependencies(monkeypatch)
    monkeypatch.setattr(module, "load_influx_config", lambda: _DummyInfluxConfig())
    monkeypatch.setattr(module, "load_symbols_from_supabase", lambda market: ["AAA"])

    failing_metric = SymbolMetrics(
        symbol="AAA",
        latest_close=50.0,  # Below price_min
        adv_jpy=100_000.0,
        atr_pct=0.2,
        median_5m_range_bps=10.0,
        close_5m_vol_share=0.1,
        no_trade_5m_ratio=0.5,
    )

    monkeypatch.setattr(
        module,
        "calculate_symbol_metrics",
        lambda client, symbols, cfg: {"AAA": failing_metric},
    )

    service = UniverseSelectionService(market_data_client_cls=_FakeMarketDataClient)
    request = UniverseSelectionRequest(settings_path=tmp_path / "settings.toml")

    with pytest.raises(UniverseSelectionError, match="No symbols passed the hard filters"):
        service.run_selection(request)


def test_run_selection_requires_symbols_for_non_supabase(monkeypatch, tmp_path):
    module, _, _, _ = _setup_common_dependencies(monkeypatch)
    monkeypatch.setattr(module, "load_influx_config", lambda: _DummyInfluxConfig())

    service = UniverseSelectionService(market_data_client_cls=_FakeMarketDataClient)
    request = UniverseSelectionRequest(
        settings_path=tmp_path / "settings.toml",
        symbol_source="csv",
        symbols=None,
    )

    with pytest.raises(UniverseSelectionError, match="symbols must be provided"):
        service.run_selection(request)
