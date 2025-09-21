"""設定ファイルおよび環境変数を読み込むユーティリティ。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH_DEFAULT = ROOT_DIR / ".env.local"


def load_env(dotenv_path: Path | None = None) -> None:
    """`.env` または `.env.local` を読み込む。"""
    if dotenv_path is None:
        dotenv_path = ENV_PATH_DEFAULT
    if dotenv_path.exists():
        load_dotenv(dotenv_path)


def _read_toml(path: Path) -> Dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


@dataclass
class InfluxConfig:
    host: str
    org: str
    token: str
    bucket_raw_1m_hot: str
    bucket_raw_1m_backfill: str
    bucket_agg_5m: str
    bucket_agg_1d: str
    write_batch_size: int
    write_flush_interval_ms: int
    max_retries: int
    retry_backoff_seconds: int


def load_influx_config(
    toml_path: Path | None = None,
    dotenv_path: Path | None = None,
) -> InfluxConfig:
    """環境変数と設定ファイルから Influx 設定を組み立てる。"""
    load_env(dotenv_path)

    if toml_path is None:
        toml_path = ROOT_DIR / "config" / "influx_config.example.toml"
    data = _read_toml(toml_path)

    connection = data.get("connection", {})
    buckets = data.get("buckets", {})
    options = data.get("options", {})

    env_host = os.getenv("INFLUXDB_HOST", connection.get("host"))
    env_org = os.getenv("INFLUXDB_ORG", connection.get("org"))
    env_token = os.getenv("INFLUXDB_TOKEN") or os.getenv("INFLUXDB_API_TOKEN")

    if not all([env_host, env_org, env_token]):  # pragma: no cover - runtime guard
        raise RuntimeError("INFLUXDB_HOST / ORG / TOKEN が設定されていません")

    return InfluxConfig(
        host=str(env_host),
        org=str(env_org),
        token=str(env_token),
        bucket_raw_1m_hot=os.getenv(
            "INFLUXDB_BUCKET_RAW_1M_HOT", buckets.get("raw_1m_hot", "raw_1m_hot")
        ),
        bucket_raw_1m_backfill=os.getenv(
            "INFLUXDB_BUCKET_RAW_1M_BACKFILL",
            buckets.get("raw_1m_backfill", "raw_1m_backfill"),
        ),
        bucket_agg_5m=os.getenv(
            "INFLUXDB_BUCKET_AGG_5M", buckets.get("agg_5m", "agg_5m")
        ),
        bucket_agg_1d=os.getenv(
            "INFLUXDB_BUCKET_AGG_1D", buckets.get("agg_1d", "agg_1d")
        ),
        write_batch_size=int(
            os.getenv("INFLUXDB_WRITE_BATCH_SIZE", options.get("write_batch_size", 5000))
        ),
        write_flush_interval_ms=int(
            os.getenv(
                "INFLUXDB_WRITE_FLUSH_INTERVAL_MS",
                options.get("write_flush_interval_ms", 1000),
            )
        ),
        max_retries=int(
            os.getenv("INFLUXDB_MAX_RETRIES", options.get("max_retries", 3))
        ),
        retry_backoff_seconds=int(
            os.getenv(
                "INFLUXDB_RETRY_BACKOFF_SECONDS",
                options.get("retry_backoff_seconds", 5),
            )
        ),
    )


def load_universe_settings(path: Path | None = None) -> Dict[str, Any]:
    """ユニバース設定 TOML を読み込む。"""
    if path is None:
        path = ROOT_DIR / "config" / "universe_settings.example.toml"
    return _read_toml(path)
