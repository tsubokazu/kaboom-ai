"""ユニバース選定ロジックのスケルトン実装。"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import math
import numpy as np
import pandas as pd

from .metrics import MetricConfig, SymbolMetrics, calculate_volatility_score


@dataclass
class ScoringWeights:
    liquidity: float
    volatility_fit: float
    cost_efficiency: float
    close_liquidity: float
    zero_volume_penalty: float
    extra: Dict[str, float]


@dataclass
class HysteresisConfig:
    maintain_rank_max: int
    add_rank_max: int


@dataclass
class SectorCapConfig:
    max_ratio: float
    definition_path: str


@dataclass
class UniverseSettings:
    core_size: int
    bench_size: int
    weights: ScoringWeights
    hysteresis: HysteresisConfig
    sector_cap: SectorCapConfig


def load_scoring_weights(config: Dict[str, Dict[str, Dict[str, float]]]) -> ScoringWeights:
    weights = config["scoring"]["weights"]
    reserved = {"liquidity", "volatility_fit", "cost_efficiency", "close_liquidity", "zero_volume_penalty"}
    extra = {k: float(v) for k, v in weights.items() if k not in reserved}
    return ScoringWeights(
        liquidity=float(weights["liquidity"]),
        volatility_fit=float(weights["volatility_fit"]),
        cost_efficiency=float(weights["cost_efficiency"]),
        close_liquidity=float(weights["close_liquidity"]),
        zero_volume_penalty=float(weights["zero_volume_penalty"]),
        extra=extra,
    )


def calculate_scores(
    metrics: Dict[str, SymbolMetrics],
    weights: ScoringWeights,
    metric_config: MetricConfig,
) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
    """各指標を重み付けして総合スコアを算出する。"""
    if not metrics:
        return {}, {}

    adv_values = {s: m.adv_jpy for s, m in metrics.items()}
    pool_size = metric_config.ranking_pool_size or len(metrics)
    adv_sorted = sorted(adv_values.items(), key=lambda x: x[1], reverse=True)
    adv_pool = {s for s, _ in adv_sorted[:pool_size]}

    def normalize(values: Dict[str, float], reverse: bool) -> Dict[str, float]:
        filtered = {s: v for s, v in values.items() if v is not None and not np.isnan(v)}
        if not filtered:
            return {}
        ordered = sorted(filtered.items(), key=lambda x: x[1], reverse=reverse)
        n = len(ordered)
        if n == 1:
            symbol, _ = ordered[0]
            return {symbol: 1.0}
        return {
            symbol: 1.0 - idx / (n - 1)
            for idx, (symbol, _) in enumerate(ordered)
        }

    liquidity_score = normalize(adv_values, reverse=True)
    cost_score = normalize(
        {s: m.median_5m_range_bps for s, m in metrics.items() if s in adv_pool},
        reverse=False,
    )
    close_liquidity_score = normalize(
        {s: m.close_5m_vol_share for s, m in metrics.items() if s in adv_pool},
        reverse=True,
    )
    zero_penalty_score = normalize(
        {s: m.no_trade_5m_ratio for s, m in metrics.items() if s in adv_pool},
        reverse=False,
    )

    extra_scores: Dict[str, Dict[str, float]] = {}
    for key, _ in weights.extra.items():
        values = {s: getattr(metrics[s], key, None) for s in metrics}
        extra_scores[key] = normalize(values, reverse=True)

    scores: Dict[str, float] = {}
    breakdown: Dict[str, Dict[str, float]] = {}
    for symbol, metric in metrics.items():
        vol_score = calculate_volatility_score(metric, metric_config)
        liquidity = liquidity_score.get(symbol, 0.0)
        cost = cost_score.get(symbol, 0.0)
        close = close_liquidity_score.get(symbol, 0.0)
        zero = zero_penalty_score.get(symbol, 0.0)
        extra_total = 0.0
        extras_detail: Dict[str, float] = {}
        for key, weight in weights.extra.items():
            value = extra_scores.get(key, {}).get(symbol, 0.0)
            extras_detail[key] = value
            extra_total += weight * value

        total = 0.0
        total += weights.liquidity * liquidity
        total += weights.volatility_fit * vol_score
        total += weights.cost_efficiency * cost
        total += weights.close_liquidity * close
        total += weights.zero_volume_penalty * zero
        total += extra_total

        scores[symbol] = total
        breakdown[symbol] = {
            "total": total,
            "liquidity": liquidity,
            "volatility": vol_score,
            "cost": cost,
            "close": close,
            "zero_penalty": zero,
            **{f"extra_{k}": v for k, v in extras_detail.items()},
        }

    return scores, breakdown


def select_universe(
    scores: Dict[str, float],
    settings: UniverseSettings,
    existing_core: Iterable[str],
    sector_map: Dict[str, str],
) -> Dict[str, List[str]]:
    """スコアに基づきCore/Benchを選定する。"""

    ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    existing_core_set = set(existing_core or [])

    def sector(symbol: str) -> str:
        return sector_map.get(symbol, "UNKNOWN")

    def select_list(size: int, max_ratio: float, allow_existing: bool) -> List[str]:
        if size <= 0:
            return []
        max_per_sector = max(1, math.floor(size * max_ratio)) if max_ratio > 0 else size
        counts: Dict[str, int] = defaultdict(int)
        selected: List[str] = []

        # 既存採用銘柄を優先的に維持
        if allow_existing and existing_core_set:
            for idx, (symbol, _) in enumerate(ranking):
                if symbol not in existing_core_set:
                    continue
                if idx >= settings.hysteresis.maintain_rank_max:
                    continue
                sec = sector(symbol)
                if counts[sec] >= max_per_sector:
                    continue
                selected.append(symbol)
                counts[sec] += 1
                if len(selected) >= size:
                    return selected

        for idx, (symbol, _) in enumerate(ranking):
            if symbol in selected:
                continue
            sec = sector(symbol)
            if counts[sec] >= max_per_sector:
                continue
            if allow_existing and symbol in existing_core_set:
                if idx >= settings.hysteresis.maintain_rank_max:
                    continue
            else:
                if allow_existing and idx >= settings.hysteresis.add_rank_max:
                    continue
            selected.append(symbol)
            counts[sec] += 1
            if len(selected) >= size:
                return selected

        # 足りない場合は制約を緩めて埋める
        if len(selected) < size:
            for symbol, _ in ranking:
                if symbol in selected:
                    continue
                sec = sector(symbol)
                if counts[sec] >= max_per_sector:
                    continue
                selected.append(symbol)
                counts[sec] += 1
                if len(selected) >= size:
                    break

        return selected

    core = select_list(settings.core_size, settings.sector_cap.max_ratio, allow_existing=True)
    bench_candidates = [s for s, _ in ranking if s not in core]
    bench_scores = {s: scores[s] for s in bench_candidates}
    bench_ranking = sorted(bench_scores.items(), key=lambda x: x[1], reverse=True)

    def select_bench(ranking_list: List[Tuple[str, float]]) -> List[str]:
        size = settings.bench_size
        if size <= 0:
            return []
        max_per_sector = max(1, math.floor(size * settings.sector_cap.max_ratio)) if settings.sector_cap.max_ratio > 0 else size
        counts: Dict[str, int] = defaultdict(int)
        bench: List[str] = []
        for symbol, _ in ranking_list:
            sec = sector(symbol)
            if counts[sec] >= max_per_sector:
                continue
            bench.append(symbol)
            counts[sec] += 1
            if len(bench) >= size:
                break
        return bench

    bench = select_bench(bench_ranking)

    return {"core": core, "bench": bench}


def load_universe_settings_struct(raw: Dict[str, Dict[str, Dict[str, float]]]) -> UniverseSettings:
    universe = raw.get("universe", {})
    scoring = raw.get("scoring", {})
    weights = load_scoring_weights(raw)

    hysteresis_raw = scoring.get("hysteresis", {})
    hysteresis_cfg = HysteresisConfig(
        maintain_rank_max=int(hysteresis_raw.get("maintain_rank_max", universe.get("core_size", 20))),
        add_rank_max=int(hysteresis_raw.get("add_rank_max", universe.get("core_size", 20))),
    )

    sector_raw = scoring.get("sector_cap", {})
    sector_cfg = SectorCapConfig(
        max_ratio=float(sector_raw.get("max_ratio", 0.3)),
        definition_path=str(sector_raw.get("definition_path", "")),
    )

    return UniverseSettings(
        core_size=int(universe.get("core_size", 20)),
        bench_size=int(universe.get("bench_size", 5)),
        weights=weights,
        hysteresis=hysteresis_cfg,
        sector_cap=sector_cfg,
    )


def load_sector_map(path: str | None) -> Dict[str, str]:
    if not path:
        return {}
    sector_path = Path(path)
    if not sector_path.exists():
        return {}
    df = pd.read_csv(sector_path)
    if "symbol" not in df.columns or "sector" not in df.columns:
        return {}
    mapping = {
        str(row.symbol).strip(): str(row.sector).strip()
        for row in df.itertuples(index=False)
    }
    return mapping
