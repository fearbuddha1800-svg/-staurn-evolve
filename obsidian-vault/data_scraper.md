---
slug: data_scraper
type: note
graph: gitnexus
---

"""Data Scraper Module — Signal Relay

Integrates best-in-class GitHub data scrapers for trading/market data
to feed neural training, backtesting, and live signal validation.

Sources:
  - yfinance (Yahoo Finance): stocks, forex, crypto, indices, ETFs
  - TradingView (tvkit/tv-scraper pattern): real-time quotes, screener data
  - MT5 (existing pinets_runner): live XAUUSD/EURUSD H1 bars

All data saved with timestamps to data/raw/ and data/processed/.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from tvkit import get_historical_data as tv_get_historical

BASE = Path(__file__).resolve().parent
DATA_RAW = BASE / "data" / "raw"
DATA_PROCESSED = BASE / "data" / "processed"
DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Symbols relevant to the trading system (Yahoo Finance format)
SYMBOLS_YF = {
    "forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"],
    "gold": ["GC=F"],  # Gold futures (XAUUSD equivalent on Yahoo)
    "crypto": ["BTC-USD", "ETH-USD", "XRP-USD", "SOL-USD"],
    "indices": ["^GSPC", "^IXIC", "^DJI"],
    "commodities": ["CL=F", "SI=F"],
}

# TradingView symbols (exchange:symbol format required by tvkit)
SYMBOLS_TV = {
    "forex": ["FX_IDC:EURUSD", "FX_IDC:GBPUSD", "FX_IDC:USDJPY", "FX_IDC:AUDUSD", "FX_IDC:USDCHF"],
    "crypto": ["CRYPTO:BTCUSD", "CRYPTO:ETHUSD", "CRYPTO:XRPUSD", "CRYPTO:SOLUSD"],
    "indices": ["INDEX:SPX", "INDEX:NAS100", "INDEX:DJI"],
}

INTERVALS = ["1m", "5m", "15m", "1h", "1d"]
PERIODS = {"1m": "7d", "5m": "60d", "15m": "60d", "1h": "730d", "1d": "max"}


def fetch_yahoo(symbol: str, interval: str = "1h", period: str | None = None) -> pd.DataFrame | None:
    """Fetch OHLCV data from Yahoo Finance via yfinance.

    Returns DataFrame with columns: open, high, low, close, volume, timestamp (UTC).
    """
    if period is None:
        period = PERIODS.get(interval, "1d")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=False)
        if df.empty:
            return None
        df = df.reset_index()
        # Normalize column names (yfinance uses 'Date' for daily, 'Datetime' for intraday)
        col_map = {}
        for c in df.columns:
            lc = c.lower()
            if lc in ("date", "datetime"):
                col_map[c] = "timestamp"
            elif lc == "open":
                col_map[c] = "open"
            elif lc == "high":
                col_map[c] = "high"
            elif lc == "low":
                col_map[c] = "low"
            elif lc == "close":
                col_map[c] = "close"
            elif lc == "volume":
                col_map[c] = "volume"
            else:
                col_map[c] = lc
        df = df.rename(columns=col_map)
        # Ensure timestamp is UTC-aware
        if "timestamp" in df.columns:
            ts = df["timestamp"]
            if pd.api.types.is_datetime64_any_dtype(ts):
                if ts.dt.tz is None:
                    df["timestamp"] = ts.dt.tz_localize("UTC")
                else:
                    df["timestamp"] = ts.dt.tz_convert("UTC")
        # Sort and dedupe
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
        # Add provenance
        df["source"] = "yfinance"
        df["symbol"] = symbol
        df["interval"] = interval
        df["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return df
    except Exception as exc:
        print(f"  yfinance error for {symbol} @ {interval}: {exc}")
        return None


def save_csv(df: pd.DataFrame, symbol: str, interval: str, source: str = "yfinance") -> Path:
    """Save a DataFrame to data/raw/ with a timestamped filename."""
    safe = symbol.replace("=", "_").replace("^", "").replace("-", "_").replace(":", "_")
    fname = f"{safe}_{interval}_{source}.csv"
    path = DATA_RAW / fname
    df.to_csv(path, index=False)
    return path


def scrape_yahoo(max_symbols_per_category: int | None = None) -> dict[str, Any]:
    """Scrape all configured symbols from Yahoo Finance."""
    results: dict[str, Any] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "yfinance",
        "symbols": {},
        "total_rows": 0,
        "errors": [],
    }
    import time

    for category, symbols in SYMBOLS_YF.items():
        if max_symbols_per_category:
            symbols = symbols[:max_symbols_per_category]
        for symbol in symbols:
            for interval in INTERVALS:
                df = fetch_yahoo(symbol, interval=interval)
                if df is None or df.empty:
                    results["errors"].append(f"{symbol} @ {interval}: no data")
                    continue
                path = save_csv(df, symbol, interval)
                results["symbols"][f"{symbol}_{interval}"] = {
                    "rows": len(df),
                    "path": str(path),
                    "first": str(df["timestamp"].iloc[0]),
                    "last": str(df["timestamp"].iloc[-1]),
                }
                results["total_rows"] += len(df)
                print(f"  ✓ {symbol} @ {interval}: {len(df)} rows → {path.name}")
                time.sleep(0.5)  # Rate limit courtesy
    return results


async def fetch_tradingview(symbol_tv: str, days: int = 30) -> pd.DataFrame | None:
    """Fetch historical OHLCV data from TradingView via tvkit.

    symbol_tv format: "FX_IDC:EURUSD" or "CRYPTO_IDC:BTCUSD"
    """
    try:
        bars = await tv_get_historical(symbol=symbol_tv, days=days)
        if not bars:
            return None
        rows = []
        for b in bars:
            d = b.model_dump() if hasattr(b, "model_dump") else b.__dict__
            rows.append(d)
        df = pd.DataFrame(rows)
        # Normalize timestamp
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
        df["source"] = "tradingview"
        df["symbol"] = symbol_tv
        df["interval"] = "1d"
        df["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return df
    except Exception as exc:
        print(f"  TradingView error for {symbol_tv}: {exc}")
        return None


def scrape_tradingview(days: int = 30) -> dict[str, Any]:
    """Scrape all configured symbols from TradingView."""
    results: dict[str, Any] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "tradingview",
        "symbols": {},
        "total_rows": 0,
        "errors": [],
    }

    async def _run():
        for category, symbols in SYMBOLS_TV.items():
            for symbol_tv in symbols:
                df = await fetch_tradingview(symbol_tv, days=days)
                if df is None or df.empty:
                    results["errors"].append(f"{symbol_tv}: no data")
                    continue
                safe = symbol_tv.replace(":", "_")
                fname = f"{safe}_1d_tradingview.csv"
                path = DATA_RAW / fname
                df.to_csv(path, index=False)
                results["symbols"][symbol_tv] = {
                    "rows": len(df),
                    "path": str(path),
                    "first": str(df["timestamp"].iloc[0]),
                    "last": str(df["timestamp"].iloc[-1]),
                }
                results["total_rows"] += len(df)
                print(f"  ✓ {symbol_tv}: {len(df)} rows → {path.name}")

    asyncio.run(_run())
    return results


def scrape_all(max_symbols_per_category: int | None = None, tv_days: int = 30) -> dict[str, Any]:
    """Scrape from all sources. Returns combined summary."""
    yf_results = scrape_yahoo(max_symbols_per_category=max_symbols_per_category)
    tv_results = scrape_tradingview(days=tv_days)
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "yfinance": yf_results,
            "tradingview": tv_results,
        },
        "total_rows": yf_results["total_rows"] + tv_results["total_rows"],
        "errors": yf_results["errors"] + tv_results["errors"],
    }


# ---------------------------------------------------------------------------
# Neural-training-ready processing
# ---------------------------------------------------------------------------

def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add common technical indicators for neural network training."""
    df = df.copy().sort_values("timestamp").reset_index(drop=True)

    # Returns
    df["ret_1"] = df["close"].pct_change()
    df["ret_5"] = df["close"].pct_change(5)
    df["ret_20"] = df["close"].pct_change(20)

    # Moving averages
    df["sma_10"] = df["close"].rolling(10).mean()
    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()

    # MACD
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # RSI (14)
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df["bb_mid"] = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

    # ATR (14) — needed for the 2×ATR stop logic
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    # Volatility
    df["vol_20"] = df["ret_1"].rolling(20).std()

    # Target: next-bar return (for supervised learning)
    df["target_ret_next"] = df["close"].pct_change().shift(-1)
    df["target_direction_next"] = (df["target_ret_next"] > 0).astype(int)

    return df


def process_for_training(symbol: str, interval: str, source: str = "yfinance") -> Path | None:
    """Load a raw CSV, add technical features, save to data/processed/."""
    safe = symbol.replace("=", "_").replace("^", "").replace("-", "_").replace(":", "_")
    raw_path = DATA_RAW / f"{safe}_{interval}_{source}.csv"
    if not raw_path.exists():
        print(f"  Raw file not found: {raw_path}")
        return None
    df = pd.read_csv(raw_path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = add_technical_features(df)
    # Drop rows with NaN targets
    df = df.dropna(subset=["target_ret_next"]).reset_index(drop=True)
    out_path = DATA_PROCESSED / f"{safe}_{interval}_{source}_features.csv"
    df.to_csv(out_path, index=False)
    print(f"  ✓ {symbol} @ {interval}: {len(df)} feature rows → {out_path.name}")
    return out_path


if __name__ == "__main__":
    print("=== Signal Relay Data Scraper ===")
    print(f"Raw data dir: {DATA_RAW}")
    print(f"Processed dir: {DATA_PROCESSED}")
    print()
    summary = scrape_all(max_symbols_per_category=None, tv_days=30)
    print(f"\n=== Complete: {summary['total_rows']} total rows fetched ===")

