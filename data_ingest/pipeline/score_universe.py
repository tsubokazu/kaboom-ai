"""ユニバース選定ロジックのスケルトン実装。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

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
) -> Dict[str, float]:
    """各指標を重み付けして総合スコアを算出する。"""
    scores: Dict[str, float] = {}
    for symbol, metric in metrics.items():
        vol_score = calculate_volatility_score(metric, metric_config)
        total = 0.0
        total += weights.volatility_fit * vol_score
        # TODO: 流動性・コスト・引け流動性などのスコア計算を実装
        total += weights.liquidity * 0.0
        total += weights.cost_efficiency * 0.0
        total += weights.close_liquidity * 0.0
        total += weights.zero_volume_penalty * 0.0
        for key, weight in weights.extra.items():
            _ = key  # placeholder for future optional metrics
            total += weight * 0.0
        scores[symbol] = total
    return scores


def select_universe(
    scores: Dict[str, float],
    settings: UniverseSettings,
    existing_core: Iterable[str],
    sector_limits: Dict[str, int],
) -> Dict[str, List[str]]:
    """Core/Benchユニバースの選定ロジック（ヒステリシス対応予定）。"""
    _ = scores, settings, existing_core, sector_limits
    raise NotImplementedError("ヒステリシスとセクター制約の実装が必要です")
