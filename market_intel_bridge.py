import json
import os
from functools import lru_cache

# Base path for market-trackers-data
BASE_DATA_PATH = "C:/Users/voidk/.hermes/workspace/luxalgo/market-trackers-data"

# Mapping from kind to (relative path, ticker extraction function)
KIND_CONFIG = {
    "congress": (
        "congress/trades/latest.json",
        lambda row: row.get("ticker")
    ),
    "insider": (
        "insider/transactions/latest.json",
        lambda row: row.get("ticker")
    ),
    "contracts": (
        "contracts/awards/latest.json",
        lambda row: row.get("recipient", {}).get("tickers", [])
    ),
    "lobbying": (
        "lobbying/filings/latest.json",
        lambda row: row.get("client", {}).get("tickers", [])
    ),
    "short_volume": (
        "short-volume/daily/latest.json",
        lambda row: row.get("ticker")
    ),
}

def _get_data_path(kind):
    """Return the absolute path to the data file for the given kind."""
    if kind not in KIND_CONFIG:
        return None
    relative_path, _ = KIND_CONFIG[kind]
    return os.path.join(BASE_DATA_PATH, relative_path)

@lru_cache(maxsize=None)
def _load_data(kind):
    """Load and cache the JSON data for the given kind.
    Returns the list of rows, or None if the file does not exist or is invalid.
    """
    data_path = _get_data_path(kind)
    if data_path is None or not os.path.exists(data_path):
        return None
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Ensure it's a list
        if not isinstance(data, list):
            return None
        return data
    except (json.JSONDecodeError, IOError):
        return None

def _filter_by_symbol(rows, kind, symbol):
    """Filter rows by symbol using the ticker extraction function for the kind."""
    if symbol is None:
        return rows
    _, ticker_extractor = KIND_CONFIG[kind]
    filtered = []
    for row in rows:
        ticker_val = ticker_extractor(row)
        # ticker_val might be a string, None, or a list (for contracts and lobbying)
        if isinstance(ticker_val, list):
            if symbol in ticker_val:
                filtered.append(row)
        else:
            if ticker_val == symbol:
                filtered.append(row)
    return filtered

def get_market_intel(kind, symbol=None, limit=20):
    """
    Get market intelligence data for the given kind.
    
    Args:
        kind (str): One of 'congress', 'insider', 'contracts', 'lobbying', 'short_volume'
        symbol (str, optional): Filter rows by ticker symbol. Defaults to None.
        limit (int, optional): Maximum number of rows to return. Defaults to 20.
    
    Returns:
        dict: {
            'rows': list of data rows (each row includes provenance.sourceUrl),
            'available': bool indicating if data was successfully loaded,
            'reason': str explaining why data is not available (if available is False)
        }
    """
    if kind not in KIND_CONFIG:
        return {
            "rows": [],
            "available": False,
            "reason": f"Unknown kind: {kind}"
        }
    
    data = _load_data(kind)
    if data is None:
        data_path = _get_data_path(kind)
        return {
            "rows": [],
            "available": False,
            "reason": f"Data not found for kind: {kind} (path: {data_path})"
        }
    
    # Filter by symbol if provided
    filtered_data = _filter_by_symbol(data, kind, symbol)
    
    # Apply limit
    limited_data = filtered_data[:limit]
    
    return {
        "rows": limited_data,
        "available": True,
        "reason": ""
    }