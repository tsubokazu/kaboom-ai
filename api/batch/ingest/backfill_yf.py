"""yfinance を使用して東証銘柄の分足データを取得し InfluxDB に書き込む。"""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from influxdb_client_3 import InfluxDBClient3, Point

from batch.config.loader import InfluxConfig, load_influx_config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@dataclass(frozen=True)
class IntervalSpec:
    measurement: str
    chunk_days: int
    max_days: int
    default_bucket_attr: str


INTERVAL_SPECS: Dict[str, IntervalSpec] = {
    "1m": IntervalSpec("ohlcv_1m", chunk_days=7, max_days=29, default_bucket_attr="bucket_raw_1m_hot"),
    "2m": IntervalSpec("ohlcv_2m", chunk_days=30, max_days=60, default_bucket_attr="bucket_agg_5m"),
    "5m": IntervalSpec("ohlcv_5m", chunk_days=30, max_days=60, default_bucket_attr="bucket_agg_5m"),
    "15m": IntervalSpec("ohlcv_15m", chunk_days=30, max_days=60, default_bucket_attr="bucket_agg_5m"),
    "30m": IntervalSpec("ohlcv_30m", chunk_days=30, max_days=60, default_bucket_attr="bucket_agg_5m"),
    "60m": IntervalSpec("ohlcv_60m", chunk_days=365, max_days=730, default_bucket_attr="bucket_agg_5m"),
    "1d": IntervalSpec("ohlcv_1d", chunk_days=365, max_days=1825, default_bucket_attr="bucket_agg_1d"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill intraday data via yfinance")
    parser.add_argument("--symbols", nargs="+", required=True, help="対象銘柄 (例: 7203.T 9984.T)")
    parser.add_argument("--days", type=int, default=30, help="取得日数 (最大60)")
    parser.add_argument(
        "--interval",
        choices=sorted(INTERVAL_SPECS.keys()),
        default="1m",
        help="yfinanceの取得間隔",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="書き込み先バケット (未指定なら interval に応じた設定値を使用)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="InfluxDBへ書き込む際のポイント件数",
    )
    return parser.parse_args()


def fetch_symbol(symbol: str, interval: str, days: int, spec: IntervalSpec) -> pd.DataFrame:
    logger.info("fetching %s interval=%s days=%d", symbol, interval, days)

    tz_local = ZoneInfo("Asia/Tokyo")
    now_local = datetime.now(tz_local)

    if days > spec.max_days:
        logger.warning(
            "%s: %s interval supports up to ~%d days; trimming from %d days",
            symbol,
            interval,
            spec.max_days,
            days,
        )
        days = spec.max_days

    start_local = now_local - timedelta(days=days)

    frames: List[pd.DataFrame] = []
    chunk_start = start_local
    while chunk_start < now_local:
        chunk_end = min(chunk_start + timedelta(days=spec.chunk_days), now_local)
        df_chunk = yf.download(
            tickers=symbol,
            interval=interval,
            start=chunk_start,
            end=chunk_end,
            group_by="column",
            auto_adjust=False,
            progress=False,
        )
        if df_chunk.empty:
            logger.debug("%s: chunk %s - %s returned empty", symbol, chunk_start, chunk_end)
        else:
            frames.append(df_chunk)
        chunk_start = chunk_end

    if not frames:
        logger.warning("%s: no data returned", symbol)
        return pd.DataFrame()

    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()

    # yfinanceはindexを終値時刻(通常はUTC)で返す。必要に応じてタイムゾーンを付与してUTCへ変換。
    if df.index.tzinfo is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert(timezone.utc)

    df = df.rename(columns=str.lower)
    df["symbol"] = symbol
    return df


def _to_float(value) -> float:
    """pandasシリーズやnumpy型を安全にfloat化する。"""
    if isinstance(value, pd.Series):
        value = value.iloc[0]
    if hasattr(value, "item"):
        value = value.item()
    return float(value)


def dataframe_to_points(df: pd.DataFrame, symbol: str, measurement: str) -> List[Point]:
    points: List[Point] = []
    for ts, row in df.iterrows():
        point = (
            Point(measurement)
            .tag("symbol", symbol)
            .tag("exchange", "TSE")
            .tag("currency", "JPY")
            .tag("source", "yf")
            .field("open", _to_float(row["open"]))
            .field("high", _to_float(row["high"]))
            .field("low", _to_float(row["low"]))
            .field("close", _to_float(row["close"]))
            .field("volume", _to_float(row.get("volume", 0.0)))
            .time(datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc))
        )
        points.append(point)
    return points


def chunked(iterable: Iterable[Point], size: int) -> Iterable[List[Point]]:
    chunk: List[Point] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def write_to_influx(client: InfluxDBClient3, bucket: str, points: Iterable[Point], chunk_size: int) -> int:
    total = 0
    for batch in chunked(points, chunk_size):
        client.write(database=bucket, record=batch)
        total += len(batch)
    return total


def main() -> None:
    args = parse_args()
    config: InfluxConfig = load_influx_config()
    spec = INTERVAL_SPECS[args.interval]

    default_bucket = getattr(config, spec.default_bucket_attr, None)
    if default_bucket is None:
        raise RuntimeError(f"InfluxConfig is missing attribute {spec.default_bucket_attr}")

    bucket = args.bucket or default_bucket

    with InfluxDBClient3(
        host=config.host,
        token=config.token,
        org=config.org,
        timeout=30_000,
        max_retries=config.max_retries,
    ) as client:
        total_points = 0
        for symbol in args.symbols:
            df = fetch_symbol(symbol, args.interval, args.days, spec)
            if df.empty:
                continue
            points = dataframe_to_points(df, symbol, spec.measurement)
            written = write_to_influx(client, bucket, points, args.chunk_size)
            logger.info("%s: wrote %d points to %s", symbol, written, bucket)
            total_points += written
        logger.info("completed. total points=%d", total_points)


if __name__ == "__main__":
    main()
