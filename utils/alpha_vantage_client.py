from pathlib import Path
import time

import pandas as pd
import requests


def call_alpha_vantage(base_url: str, api_key: str, params: dict) -> dict:
    """
    Calls the Alpha Vantage API and returns JSON data.

    This function also cleans common Alpha Vantage error messages so the
    Streamlit app displays user-friendly messages instead of long API text.
    """

    if api_key is None or str(api_key).strip() == "":
        raise ValueError("API key not found. Check your .env file.")

    request_params = params.copy()
    request_params["apikey"] = api_key

    response = requests.get(
        base_url,
        params=request_params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "Error Message" in data:
        raise ValueError(f"API error: {data['Error Message']}")

    if "Note" in data:
        note_message = str(data["Note"])

        if "rate limit" in note_message.lower() or "frequency" in note_message.lower():
            raise ValueError(
                "API request limit reached. Use local cache or try again later."
            )

        raise ValueError(f"API note: {note_message}")

    if "Information" in data:
        information_message = str(data["Information"])

        if "rate limit" in information_message.lower():
            raise ValueError(
                "API daily limit reached. Use cached data or try again later."
            )

        if "premium" in information_message.lower():
            raise ValueError(
                "This endpoint may require a premium Alpha Vantage plan."
            )

        raise ValueError(f"API information: {information_message}")

    return data


def get_stock_daily_prices(
    ticker: str,
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    outputsize: str = "compact"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Downloads daily stock prices from Alpha Vantage.

    Uses local cache when available to avoid unnecessary API requests.

    Returns:
    - prices_df: OHLCV daily prices
    - metadata_df: API/source metadata
    """

    clean_ticker = ticker.strip().upper()

    if clean_ticker == "":
        raise ValueError("Ticker cannot be empty.")

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = cache_dir / f"stock_daily_{clean_ticker}.csv"
    metadata_cache_path = cache_dir / f"stock_daily_metadata_{clean_ticker}.csv"

    if cache_path.exists() and metadata_cache_path.exists() and not force_refresh:
        prices_df = pd.read_csv(
            cache_path,
            parse_dates=["Date"]
        )

        metadata_df = pd.read_csv(
            metadata_cache_path
        )

        return prices_df, metadata_df

    data = call_alpha_vantage(
        base_url=base_url,
        api_key=api_key,
        params={
            "function": "TIME_SERIES_DAILY",
            "symbol": clean_ticker,
            "outputsize": outputsize
        }
    )

    time_series_key = "Time Series (Daily)"

    if time_series_key not in data:
        raise ValueError(
            f"Daily time series not found for {clean_ticker}. "
            f"Received keys: {list(data.keys())}"
        )

    raw_series = data[time_series_key]

    prices_df = pd.DataFrame.from_dict(
        raw_series,
        orient="index"
    )

    prices_df = prices_df.reset_index()

    prices_df = prices_df.rename(columns={
        "index": "Date",
        "1. open": "Open",
        "2. high": "High",
        "3. low": "Low",
        "4. close": "Close",
        "5. volume": "Volume"
    })

    expected_columns = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]

    missing_columns = [
        column
        for column in expected_columns
        if column not in prices_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing expected columns for {clean_ticker}: {missing_columns}"
        )

    prices_df["Date"] = pd.to_datetime(
        prices_df["Date"],
        errors="coerce"
    )

    numeric_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]

    for column in numeric_columns:
        prices_df[column] = pd.to_numeric(
            prices_df[column],
            errors="coerce"
        )

    prices_df = prices_df.dropna(
        subset=["Date", "Close"]
    )

    prices_df = prices_df.sort_values("Date")

    prices_df["Ticker"] = clean_ticker

    metadata = data.get("Meta Data", {})

    metadata_df = pd.DataFrame([{
        "Ticker": clean_ticker,
        "Information": metadata.get("1. Information"),
        "Symbol": metadata.get("2. Symbol"),
        "Last Refreshed": metadata.get("3. Last Refreshed"),
        "Output Size": metadata.get("4. Output Size"),
        "Time Zone": metadata.get("5. Time Zone"),
        "Rows": len(prices_df),
        "First Date": prices_df["Date"].min(),
        "Latest Date": prices_df["Date"].max(),
        "Cache File": str(cache_path),
        "Metadata Cache File": str(metadata_cache_path)
    }])

    prices_df.to_csv(
        cache_path,
        index=False
    )

    metadata_df.to_csv(
        metadata_cache_path,
        index=False
    )

    return prices_df, metadata_df


def get_multiple_stock_prices(
    tickers: list[str],
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    outputsize: str = "compact",
    api_sleep_seconds: int = 15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Downloads daily stock prices for multiple tickers.

    Returns:
    - close_prices: wide DataFrame with Close prices
    - prices_long: long DataFrame with OHLCV prices
    - metadata: metadata for each ticker
    - status: success/error status for each ticker
    """

    price_data_list = []
    metadata_list = []
    status_rows = []

    clean_tickers = []

    for ticker in tickers:
        clean_ticker = str(ticker).strip().upper()

        if clean_ticker and clean_ticker not in clean_tickers:
            clean_tickers.append(clean_ticker)

    if not clean_tickers:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame([{
                "Ticker": "-",
                "Status": "Error",
                "Rows": 0,
                "Message": "No valid tickers provided."
            }])
        )

    for index, ticker in enumerate(clean_tickers):

        cache_path = cache_dir / f"stock_daily_{ticker}.csv"
        metadata_cache_path = cache_dir / f"stock_daily_metadata_{ticker}.csv"

        cache_exists_before_call = (
            cache_path.exists()
            and metadata_cache_path.exists()
            and not force_refresh
        )

        try:
            prices_df, metadata_df = get_stock_daily_prices(
                ticker=ticker,
                base_url=base_url,
                api_key=api_key,
                cache_dir=cache_dir,
                force_refresh=force_refresh,
                outputsize=outputsize
            )

            price_data_list.append(prices_df)
            metadata_list.append(metadata_df)

            data_source = (
                "Local cache"
                if cache_exists_before_call
                else "Alpha Vantage API"
            )

            status_rows.append({
                "Ticker": ticker,
                "Status": "Available",
                "Rows": len(prices_df),
                "Source": data_source,
                "Message": "Data loaded successfully."
            })

            should_sleep = (
                not cache_exists_before_call
                and index < len(clean_tickers) - 1
            )

            if should_sleep:
                time.sleep(api_sleep_seconds)

        except Exception as error:
            status_rows.append({
                "Ticker": ticker,
                "Status": "Error",
                "Rows": 0,
                "Source": "Alpha Vantage API",
                "Message": str(error)
            })

    if price_data_list:
        prices_long = pd.concat(
            price_data_list,
            ignore_index=True
        )

        close_prices = prices_long.pivot_table(
            index="Date",
            columns="Ticker",
            values="Close",
            aggfunc="last"
        )

        close_prices = close_prices.sort_index()

    else:
        prices_long = pd.DataFrame()
        close_prices = pd.DataFrame()

    if metadata_list:
        metadata = pd.concat(
            metadata_list,
            ignore_index=True
        )
    else:
        metadata = pd.DataFrame()

    status = pd.DataFrame(status_rows)

    return close_prices, prices_long, metadata, status

# ============================================================
# COMPANY FUNDAMENTALS - OVERVIEW ENDPOINT
# ============================================================

def clean_company_overview_data(overview_df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa e converte campos numéricos do endpoint OVERVIEW.
    """

    if overview_df is None or overview_df.empty:
        return pd.DataFrame()

    cleaned_df = overview_df.copy()

    numeric_columns = [
        "MarketCapitalization",
        "EBITDA",
        "PERatio",
        "PEGRatio",
        "BookValue",
        "DividendPerShare",
        "DividendYield",
        "EPS",
        "RevenuePerShareTTM",
        "ProfitMargin",
        "OperatingMarginTTM",
        "ReturnOnAssetsTTM",
        "ReturnOnEquityTTM",
        "RevenueTTM",
        "GrossProfitTTM",
        "DilutedEPSTTM",
        "QuarterlyEarningsGrowthYOY",
        "QuarterlyRevenueGrowthYOY",
        "AnalystTargetPrice",
        "TrailingPE",
        "ForwardPE",
        "PriceToSalesRatioTTM",
        "PriceToBookRatio",
        "EVToRevenue",
        "EVToEBITDA",
        "Beta",
        "52WeekHigh",
        "52WeekLow",
        "50DayMovingAverage",
        "200DayMovingAverage",
        "SharesOutstanding",
        "AnalystRatingStrongBuy",
        "AnalystRatingBuy",
        "AnalystRatingHold",
        "AnalystRatingSell",
        "AnalystRatingStrongSell"
    ]

    for column in numeric_columns:
        if column in cleaned_df.columns:
            cleaned_df[column] = (
                cleaned_df[column]
                .replace(["None", "none", "N/A", "-", ""], pd.NA)
            )

            cleaned_df[column] = pd.to_numeric(
                cleaned_df[column],
                errors="coerce"
            )

    date_columns = [
        "LatestQuarter"
    ]

    for column in date_columns:
        if column in cleaned_df.columns:
            cleaned_df[column] = pd.to_datetime(
                cleaned_df[column],
                errors="coerce"
            )

    return cleaned_df


def get_company_overview(
    ticker: str,
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtém o Company Overview de uma empresa através da Alpha Vantage.

    Usa cache local para evitar requests repetidos.
    """

    clean_ticker = ticker.strip().upper()

    if clean_ticker == "":
        raise ValueError("Ticker cannot be empty.")

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = cache_dir / f"company_overview_{clean_ticker}.csv"
    metadata_cache_path = cache_dir / f"company_overview_metadata_{clean_ticker}.csv"

    if cache_path.exists() and metadata_cache_path.exists() and not force_refresh:
        overview_df = pd.read_csv(cache_path)
        metadata_df = pd.read_csv(metadata_cache_path)

        overview_df = clean_company_overview_data(overview_df)

        return overview_df, metadata_df

    data = call_alpha_vantage(
        base_url=base_url,
        api_key=api_key,
        params={
            "function": "OVERVIEW",
            "symbol": clean_ticker
        }
    )

    if not isinstance(data, dict) or not data:
        raise ValueError(f"No company overview data found for {clean_ticker}.")

    if "Symbol" not in data or str(data.get("Symbol", "")).strip() == "":
        raise ValueError(
            f"Company overview not found for {clean_ticker}. "
            f"Received keys: {list(data.keys())}"
        )

    overview_df = pd.DataFrame([data])

    overview_df = clean_company_overview_data(overview_df)

    metadata_df = pd.DataFrame([{
        "Ticker": clean_ticker,
        "Symbol": data.get("Symbol"),
        "Name": data.get("Name"),
        "AssetType": data.get("AssetType"),
        "Exchange": data.get("Exchange"),
        "Currency": data.get("Currency"),
        "Country": data.get("Country"),
        "Sector": data.get("Sector"),
        "Industry": data.get("Industry"),
        "LatestQuarter": data.get("LatestQuarter"),
        "Rows": len(overview_df),
        "Cache File": str(cache_path),
        "Metadata Cache File": str(metadata_cache_path)
    }])

    overview_df.to_csv(
        cache_path,
        index=False
    )

    metadata_df.to_csv(
        metadata_cache_path,
        index=False
    )

    return overview_df, metadata_df


def get_multiple_company_overviews(
    tickers: list[str],
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    api_sleep_seconds: int = 15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Obtém Company Overview para múltiplos tickers.

    Returns:
    - overview: tabela consolidada de fundamentos;
    - metadata: metadata por ticker;
    - status: estado por ticker.
    """

    overview_list = []
    metadata_list = []
    status_rows = []

    clean_tickers = []

    for ticker in tickers:
        clean_ticker = str(ticker).strip().upper()

        if clean_ticker and clean_ticker not in clean_tickers:
            clean_tickers.append(clean_ticker)

    if not clean_tickers:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame([{
                "Ticker": "-",
                "Status": "Error",
                "Rows": 0,
                "Source": "-",
                "Message": "No valid tickers provided."
            }])
        )

    for index, ticker in enumerate(clean_tickers):

        cache_path = cache_dir / f"company_overview_{ticker}.csv"
        metadata_cache_path = cache_dir / f"company_overview_metadata_{ticker}.csv"

        cache_exists_before_call = (
            cache_path.exists()
            and metadata_cache_path.exists()
            and not force_refresh
        )

        try:
            overview_df, metadata_df = get_company_overview(
                ticker=ticker,
                base_url=base_url,
                api_key=api_key,
                cache_dir=cache_dir,
                force_refresh=force_refresh
            )

            overview_list.append(overview_df)
            metadata_list.append(metadata_df)

            data_source = (
                "Local cache"
                if cache_exists_before_call
                else "Alpha Vantage API"
            )

            status_rows.append({
                "Ticker": ticker,
                "Status": "Available",
                "Rows": len(overview_df),
                "Source": data_source,
                "Message": "Company overview loaded successfully."
            })

            should_sleep = (
                not cache_exists_before_call
                and index < len(clean_tickers) - 1
            )

            if should_sleep:
                time.sleep(api_sleep_seconds)

        except Exception as error:
            status_rows.append({
                "Ticker": ticker,
                "Status": "Error",
                "Rows": 0,
                "Source": "Alpha Vantage API",
                "Message": str(error)
            })

    if overview_list:
        overview = pd.concat(
            overview_list,
            ignore_index=True
        )

        overview = clean_company_overview_data(overview)

    else:
        overview = pd.DataFrame()

    if metadata_list:
        metadata = pd.concat(
            metadata_list,
            ignore_index=True
        )
    else:
        metadata = pd.DataFrame()

    status = pd.DataFrame(status_rows)

    return overview, metadata, status


# ============================================================
# COMMODITIES DATA
# ============================================================

def get_commodity_data(
    commodity_function: str,
    commodity_name: str,
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    interval: str = "monthly"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtém dados de uma commodity através da Alpha Vantage.

    Exemplos de commodity_function:
    - WTI
    - BRENT
    - NATURAL_GAS
    """

    clean_function = commodity_function.strip().upper()
    clean_name = commodity_name.strip()

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = cache_dir / f"commodity_{clean_function.lower()}_{interval}.csv"
    metadata_cache_path = cache_dir / f"commodity_{clean_function.lower()}_{interval}_metadata.csv"

    if cache_path.exists() and metadata_cache_path.exists() and not force_refresh:
        commodity_df = pd.read_csv(
            cache_path,
            parse_dates=["Date"]
        )

        metadata_df = pd.read_csv(
            metadata_cache_path
        )

        return commodity_df, metadata_df

    data = call_alpha_vantage(
        base_url=base_url,
        api_key=api_key,
        params={
            "function": clean_function,
            "interval": interval
        }
    )

    if "data" not in data:
        raise ValueError(
            f"Commodity data not found for {clean_function}. "
            f"Received keys: {list(data.keys())}"
        )

    raw_data = data["data"]

    if not raw_data:
        raise ValueError(f"No data returned for {clean_function}.")

    commodity_df = pd.DataFrame(raw_data)

    if "date" not in commodity_df.columns or "value" not in commodity_df.columns:
        raise ValueError(
            f"Expected columns 'date' and 'value' not found for {clean_function}."
        )

    commodity_df = commodity_df.rename(columns={
        "date": "Date",
        "value": "Value"
    })

    commodity_df["Date"] = pd.to_datetime(
        commodity_df["Date"],
        errors="coerce"
    )

    commodity_df["Value"] = (
        commodity_df["Value"]
        .replace([".", "None", "none", "N/A", "-", ""], pd.NA)
    )

    commodity_df["Value"] = pd.to_numeric(
        commodity_df["Value"],
        errors="coerce"
    )

    commodity_df = commodity_df.dropna(
        subset=["Date", "Value"]
    )

    commodity_df = commodity_df.sort_values("Date")

    commodity_df["Commodity"] = clean_name
    commodity_df["Function"] = clean_function
    commodity_df["Interval"] = interval

    metadata_df = pd.DataFrame([{
        "Commodity": clean_name,
        "Function": clean_function,
        "Interval": interval,
        "Name": data.get("name"),
        "Unit": data.get("unit"),
        "Rows": len(commodity_df),
        "First Date": commodity_df["Date"].min(),
        "Latest Date": commodity_df["Date"].max(),
        "Cache File": str(cache_path),
        "Metadata Cache File": str(metadata_cache_path)
    }])

    commodity_df.to_csv(
        cache_path,
        index=False
    )

    metadata_df.to_csv(
        metadata_cache_path,
        index=False
    )

    return commodity_df, metadata_df


def get_multiple_commodities(
    commodities: list[dict],
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    interval: str = "monthly",
    api_sleep_seconds: int = 15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Obtém dados para múltiplas commodities.

    Returns:
    - commodity_values: DataFrame wide com valores por commodity
    - commodity_long: DataFrame long com todos os dados
    - metadata: metadata consolidada
    - status: estado por commodity
    """

    commodity_data_list = []
    metadata_list = []
    status_rows = []

    if not commodities:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame([{
                "Commodity": "-",
                "Function": "-",
                "Status": "Error",
                "Rows": 0,
                "Source": "-",
                "Message": "No commodities provided."
            }])
        )

    for index, commodity in enumerate(commodities):
        commodity_function = commodity["function"]
        commodity_name = commodity["name"]

        cache_path = cache_dir / f"commodity_{commodity_function.lower()}_{interval}.csv"
        metadata_cache_path = cache_dir / f"commodity_{commodity_function.lower()}_{interval}_metadata.csv"

        cache_exists_before_call = (
            cache_path.exists()
            and metadata_cache_path.exists()
            and not force_refresh
        )

        try:
            commodity_df, metadata_df = get_commodity_data(
                commodity_function=commodity_function,
                commodity_name=commodity_name,
                base_url=base_url,
                api_key=api_key,
                cache_dir=cache_dir,
                force_refresh=force_refresh,
                interval=interval
            )

            commodity_data_list.append(commodity_df)
            metadata_list.append(metadata_df)

            data_source = (
                "Local cache"
                if cache_exists_before_call
                else "Alpha Vantage API"
            )

            status_rows.append({
                "Commodity": commodity_name,
                "Function": commodity_function,
                "Status": "Available",
                "Rows": len(commodity_df),
                "Source": data_source,
                "Message": "Commodity data loaded successfully."
            })

            should_sleep = (
                not cache_exists_before_call
                and index < len(commodities) - 1
            )

            if should_sleep:
                time.sleep(api_sleep_seconds)

        except Exception as error:
            status_rows.append({
                "Commodity": commodity_name,
                "Function": commodity_function,
                "Status": "Error",
                "Rows": 0,
                "Source": "Alpha Vantage API",
                "Message": str(error)
            })

    if commodity_data_list:
        commodity_long = pd.concat(
            commodity_data_list,
            ignore_index=True
        )

        commodity_values = commodity_long.pivot_table(
            index="Date",
            columns="Commodity",
            values="Value",
            aggfunc="last"
        )

        commodity_values = commodity_values.sort_index()

    else:
        commodity_long = pd.DataFrame()
        commodity_values = pd.DataFrame()

    if metadata_list:
        metadata = pd.concat(
            metadata_list,
            ignore_index=True
        )
    else:
        metadata = pd.DataFrame()

    status = pd.DataFrame(status_rows)

    return commodity_values, commodity_long, metadata, status



# ============================================================
# FX DATA
# ============================================================

def get_fx_daily_data(
    from_symbol: str,
    to_symbol: str,
    pair_name: str,
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    outputsize: str = "compact"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtém dados diários de um par cambial através da Alpha Vantage.

    Endpoint usado:
    - FX_DAILY

    Exemplos:
    - EUR/USD
    - GBP/USD
    - USD/JPY
    """

    clean_from_symbol = from_symbol.strip().upper()
    clean_to_symbol = to_symbol.strip().upper()
    clean_pair_name = pair_name.strip().upper().replace("/", "_")

    if clean_from_symbol == "" or clean_to_symbol == "":
        raise ValueError("FX symbols cannot be empty.")

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = cache_dir / f"fx_daily_{clean_pair_name}.csv"
    metadata_cache_path = cache_dir / f"fx_daily_metadata_{clean_pair_name}.csv"

    if cache_path.exists() and metadata_cache_path.exists() and not force_refresh:
        fx_df = pd.read_csv(
            cache_path,
            parse_dates=["Date"]
        )

        metadata_df = pd.read_csv(
            metadata_cache_path
        )

        return fx_df, metadata_df

    data = call_alpha_vantage(
        base_url=base_url,
        api_key=api_key,
        params={
            "function": "FX_DAILY",
            "from_symbol": clean_from_symbol,
            "to_symbol": clean_to_symbol,
            "outputsize": outputsize
        }
    )

    time_series_key = "Time Series FX (Daily)"

    if time_series_key not in data:
        raise ValueError(
            f"FX daily time series not found for {clean_from_symbol}/{clean_to_symbol}. "
            f"Received keys: {list(data.keys())}"
        )

    raw_series = data[time_series_key]

    if not raw_series:
        raise ValueError(
            f"No FX data returned for {clean_from_symbol}/{clean_to_symbol}."
        )

    fx_df = pd.DataFrame.from_dict(
        raw_series,
        orient="index"
    )

    fx_df = fx_df.reset_index()

    fx_df = fx_df.rename(columns={
        "index": "Date",
        "1. open": "Open",
        "2. high": "High",
        "3. low": "Low",
        "4. close": "Close"
    })

    expected_columns = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close"
    ]

    missing_columns = [
        column
        for column in expected_columns
        if column not in fx_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing expected FX columns for {clean_from_symbol}/{clean_to_symbol}: "
            f"{missing_columns}"
        )

    fx_df["Date"] = pd.to_datetime(
        fx_df["Date"],
        errors="coerce"
    )

    numeric_columns = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    for column in numeric_columns:
        fx_df[column] = pd.to_numeric(
            fx_df[column],
            errors="coerce"
        )

    fx_df = fx_df.dropna(
        subset=["Date", "Close"]
    )

    fx_df = fx_df.sort_values("Date")

    fx_df["From Symbol"] = clean_from_symbol
    fx_df["To Symbol"] = clean_to_symbol
    fx_df["Pair"] = f"{clean_from_symbol}/{clean_to_symbol}"
    fx_df["Pair Name"] = clean_pair_name

    metadata = data.get("Meta Data", {})

    metadata_df = pd.DataFrame([{
        "Pair": f"{clean_from_symbol}/{clean_to_symbol}",
        "Pair Name": clean_pair_name,
        "From Symbol": clean_from_symbol,
        "To Symbol": clean_to_symbol,
        "Information": metadata.get("1. Information"),
        "From Symbol Metadata": metadata.get("2. From Symbol"),
        "To Symbol Metadata": metadata.get("3. To Symbol"),
        "Output Size": metadata.get("4. Output Size"),
        "Last Refreshed": metadata.get("5. Last Refreshed"),
        "Time Zone": metadata.get("6. Time Zone"),
        "Rows": len(fx_df),
        "First Date": fx_df["Date"].min(),
        "Latest Date": fx_df["Date"].max(),
        "Cache File": str(cache_path),
        "Metadata Cache File": str(metadata_cache_path)
    }])

    fx_df.to_csv(
        cache_path,
        index=False
    )

    metadata_df.to_csv(
        metadata_cache_path,
        index=False
    )

    return fx_df, metadata_df


def get_multiple_fx_pairs(
    fx_pairs: list[dict],
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    outputsize: str = "compact",
    api_sleep_seconds: int = 15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Obtém dados diários para múltiplos pares cambiais.

    Returns:
    - fx_close_prices: DataFrame wide com Close por par cambial
    - fx_long: DataFrame long com OHLC por par cambial
    - metadata: metadata consolidada
    - status: estado por par cambial
    """

    fx_data_list = []
    metadata_list = []
    status_rows = []

    if not fx_pairs:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame([{
                "Pair": "-",
                "Status": "Error",
                "Rows": 0,
                "Source": "-",
                "Message": "No FX pairs provided."
            }])
        )

    for index, pair_config in enumerate(fx_pairs):
        from_symbol = pair_config["from_symbol"]
        to_symbol = pair_config["to_symbol"]
        pair_name = pair_config["pair_name"]

        clean_pair_name = pair_name.strip().upper().replace("/", "_")

        cache_path = cache_dir / f"fx_daily_{clean_pair_name}.csv"
        metadata_cache_path = cache_dir / f"fx_daily_metadata_{clean_pair_name}.csv"

        cache_exists_before_call = (
            cache_path.exists()
            and metadata_cache_path.exists()
            and not force_refresh
        )

        try:
            fx_df, metadata_df = get_fx_daily_data(
                from_symbol=from_symbol,
                to_symbol=to_symbol,
                pair_name=pair_name,
                base_url=base_url,
                api_key=api_key,
                cache_dir=cache_dir,
                force_refresh=force_refresh,
                outputsize=outputsize
            )

            fx_data_list.append(fx_df)
            metadata_list.append(metadata_df)

            data_source = (
                "Local cache"
                if cache_exists_before_call
                else "Alpha Vantage API"
            )

            status_rows.append({
                "Pair": f"{from_symbol.upper()}/{to_symbol.upper()}",
                "Pair Name": clean_pair_name,
                "Status": "Available",
                "Rows": len(fx_df),
                "Source": data_source,
                "Message": "FX data loaded successfully."
            })

            should_sleep = (
                not cache_exists_before_call
                and index < len(fx_pairs) - 1
            )

            if should_sleep:
                time.sleep(api_sleep_seconds)

        except Exception as error:
            status_rows.append({
                "Pair": f"{from_symbol.upper()}/{to_symbol.upper()}",
                "Pair Name": clean_pair_name,
                "Status": "Error",
                "Rows": 0,
                "Source": "Alpha Vantage API",
                "Message": str(error)
            })

    if fx_data_list:
        fx_long = pd.concat(
            fx_data_list,
            ignore_index=True
        )

        fx_close_prices = fx_long.pivot_table(
            index="Date",
            columns="Pair",
            values="Close",
            aggfunc="last"
        )

        fx_close_prices = fx_close_prices.sort_index()

    else:
        fx_long = pd.DataFrame()
        fx_close_prices = pd.DataFrame()

    if metadata_list:
        metadata = pd.concat(
            metadata_list,
            ignore_index=True
        )
    else:
        metadata = pd.DataFrame()

    status = pd.DataFrame(status_rows)

    return fx_close_prices, fx_long, metadata, status



# ============================================================
# CRYPTO DATA
# ============================================================

def get_crypto_daily_data(
    crypto_symbol: str,
    market_symbol: str,
    crypto_name: str,
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtém dados diários de uma criptomoeda através da Alpha Vantage.

    Endpoint usado:
    - DIGITAL_CURRENCY_DAILY

    Exemplos:
    - BTC/USD
    - ETH/USD
    """

    clean_crypto_symbol = crypto_symbol.strip().upper()
    clean_market_symbol = market_symbol.strip().upper()
    clean_crypto_name = crypto_name.strip().upper().replace("/", "_")

    if clean_crypto_symbol == "" or clean_market_symbol == "":
        raise ValueError("Crypto symbol and market symbol cannot be empty.")

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = cache_dir / f"crypto_daily_{clean_crypto_name}.csv"
    metadata_cache_path = cache_dir / f"crypto_daily_metadata_{clean_crypto_name}.csv"

    if cache_path.exists() and metadata_cache_path.exists() and not force_refresh:
        crypto_df = pd.read_csv(
            cache_path,
            parse_dates=["Date"]
        )

        metadata_df = pd.read_csv(
            metadata_cache_path
        )

        return crypto_df, metadata_df

    data = call_alpha_vantage(
        base_url=base_url,
        api_key=api_key,
        params={
            "function": "DIGITAL_CURRENCY_DAILY",
            "symbol": clean_crypto_symbol,
            "market": clean_market_symbol
        }
    )

    time_series_key = "Time Series (Digital Currency Daily)"

    if time_series_key not in data:
        raise ValueError(
            f"Crypto daily time series not found for {clean_crypto_symbol}/{clean_market_symbol}. "
            f"Received keys: {list(data.keys())}"
        )

    raw_series = data[time_series_key]

    if not raw_series:
        raise ValueError(
            f"No crypto data returned for {clean_crypto_symbol}/{clean_market_symbol}."
        )

    crypto_df = pd.DataFrame.from_dict(
        raw_series,
        orient="index"
    )

    crypto_df = crypto_df.reset_index()

    crypto_df = crypto_df.rename(columns={
        "index": "Date",
        "1. open": "Open",
        "2. high": "High",
        "3. low": "Low",
        "4. close": "Close",
        "5. volume": "Volume",
        "6. market cap": "Market Cap"
    })

    expected_columns = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close"
    ]

    missing_columns = [
        column
        for column in expected_columns
        if column not in crypto_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing expected crypto columns for {clean_crypto_symbol}/{clean_market_symbol}: "
            f"{missing_columns}"
        )

    crypto_df["Date"] = pd.to_datetime(
        crypto_df["Date"],
        errors="coerce"
    )

    numeric_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Market Cap"
    ]

    for column in numeric_columns:
        if column in crypto_df.columns:
            crypto_df[column] = pd.to_numeric(
                crypto_df[column],
                errors="coerce"
            )

    crypto_df = crypto_df.dropna(
        subset=["Date", "Close"]
    )

    crypto_df = crypto_df.sort_values("Date")

    crypto_df["Crypto Symbol"] = clean_crypto_symbol
    crypto_df["Market Symbol"] = clean_market_symbol
    crypto_df["Pair"] = f"{clean_crypto_symbol}/{clean_market_symbol}"
    crypto_df["Crypto Name"] = clean_crypto_name

    metadata = data.get("Meta Data", {})

    metadata_df = pd.DataFrame([{
        "Pair": f"{clean_crypto_symbol}/{clean_market_symbol}",
        "Crypto Name": clean_crypto_name,
        "Crypto Symbol": clean_crypto_symbol,
        "Market Symbol": clean_market_symbol,
        "Information": metadata.get("1. Information"),
        "Digital Currency Code": metadata.get("2. Digital Currency Code"),
        "Digital Currency Name": metadata.get("3. Digital Currency Name"),
        "Market Code": metadata.get("4. Market Code"),
        "Market Name": metadata.get("5. Market Name"),
        "Last Refreshed": metadata.get("6. Last Refreshed"),
        "Time Zone": metadata.get("7. Time Zone"),
        "Rows": len(crypto_df),
        "First Date": crypto_df["Date"].min(),
        "Latest Date": crypto_df["Date"].max(),
        "Cache File": str(cache_path),
        "Metadata Cache File": str(metadata_cache_path)
    }])

    crypto_df.to_csv(
        cache_path,
        index=False
    )

    metadata_df.to_csv(
        metadata_cache_path,
        index=False
    )

    return crypto_df, metadata_df


def get_multiple_crypto_assets(
    crypto_assets: list[dict],
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    api_sleep_seconds: int = 15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Obtém dados diários para múltiplas criptomoedas.

    Returns:
    - crypto_close_prices: DataFrame wide com Close por criptoativo
    - crypto_long: DataFrame long com OHLCV por criptoativo
    - metadata: metadata consolidada
    - status: estado por criptoativo
    """

    crypto_data_list = []
    metadata_list = []
    status_rows = []

    if not crypto_assets:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame([{
                "Pair": "-",
                "Status": "Error",
                "Rows": 0,
                "Source": "-",
                "Message": "No crypto assets provided."
            }])
        )

    for index, crypto_config in enumerate(crypto_assets):
        crypto_symbol = crypto_config["crypto_symbol"]
        market_symbol = crypto_config["market_symbol"]
        crypto_name = crypto_config["crypto_name"]

        clean_crypto_name = crypto_name.strip().upper().replace("/", "_")

        cache_path = cache_dir / f"crypto_daily_{clean_crypto_name}.csv"
        metadata_cache_path = cache_dir / f"crypto_daily_metadata_{clean_crypto_name}.csv"

        cache_exists_before_call = (
            cache_path.exists()
            and metadata_cache_path.exists()
            and not force_refresh
        )

        try:
            crypto_df, metadata_df = get_crypto_daily_data(
                crypto_symbol=crypto_symbol,
                market_symbol=market_symbol,
                crypto_name=crypto_name,
                base_url=base_url,
                api_key=api_key,
                cache_dir=cache_dir,
                force_refresh=force_refresh
            )

            crypto_data_list.append(crypto_df)
            metadata_list.append(metadata_df)

            data_source = (
                "Local cache"
                if cache_exists_before_call
                else "Alpha Vantage API"
            )

            status_rows.append({
                "Pair": f"{crypto_symbol.upper()}/{market_symbol.upper()}",
                "Crypto Name": clean_crypto_name,
                "Status": "Available",
                "Rows": len(crypto_df),
                "Source": data_source,
                "Message": "Crypto data loaded successfully."
            })

            should_sleep = (
                not cache_exists_before_call
                and index < len(crypto_assets) - 1
            )

            if should_sleep:
                time.sleep(api_sleep_seconds)

        except Exception as error:
            status_rows.append({
                "Pair": f"{crypto_symbol.upper()}/{market_symbol.upper()}",
                "Crypto Name": clean_crypto_name,
                "Status": "Error",
                "Rows": 0,
                "Source": "Alpha Vantage API",
                "Message": str(error)
            })

    if crypto_data_list:
        crypto_long = pd.concat(
            crypto_data_list,
            ignore_index=True
        )

        crypto_close_prices = crypto_long.pivot_table(
            index="Date",
            columns="Pair",
            values="Close",
            aggfunc="last"
        )

        crypto_close_prices = crypto_close_prices.sort_index()

    else:
        crypto_long = pd.DataFrame()
        crypto_close_prices = pd.DataFrame()

    if metadata_list:
        metadata = pd.concat(
            metadata_list,
            ignore_index=True
        )
    else:
        metadata = pd.DataFrame()

    status = pd.DataFrame(status_rows)

    return crypto_close_prices, crypto_long, metadata, status


# ============================================================
# MACROECONOMIC DATA
# ============================================================

def get_macro_indicator_data(
    function_name: str,
    indicator_name: str,
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    interval: str | None = "monthly",
    maturity: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Obtém dados macroeconómicos através da Alpha Vantage.

    Exemplos de function_name:
    - TREASURY_YIELD
    - FEDERAL_FUNDS_RATE
    - CPI
    - UNEMPLOYMENT

    Alguns endpoints aceitam parâmetros adicionais:
    - TREASURY_YIELD: interval + maturity
    - FEDERAL_FUNDS_RATE: interval
    - CPI: interval
    - UNEMPLOYMENT: normalmente não precisa de interval
    """

    clean_function_name = function_name.strip().upper()
    clean_indicator_name = indicator_name.strip()

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_suffix_parts = [
        clean_function_name.lower()
    ]

    if interval:
        cache_suffix_parts.append(interval.lower())

    if maturity:
        cache_suffix_parts.append(maturity.lower())

    cache_suffix = "_".join(cache_suffix_parts)

    cache_path = cache_dir / f"macro_{cache_suffix}.csv"
    metadata_cache_path = cache_dir / f"macro_{cache_suffix}_metadata.csv"

    if cache_path.exists() and metadata_cache_path.exists() and not force_refresh:
        macro_df = pd.read_csv(
            cache_path,
            parse_dates=["Date"]
        )

        metadata_df = pd.read_csv(
            metadata_cache_path
        )

        return macro_df, metadata_df

    params = {
        "function": clean_function_name
    }

    if interval:
        params["interval"] = interval

    if maturity:
        params["maturity"] = maturity

    data = call_alpha_vantage(
        base_url=base_url,
        api_key=api_key,
        params=params
    )

    if "data" not in data:
        raise ValueError(
            f"Macro data not found for {clean_function_name}. "
            f"Received keys: {list(data.keys())}"
        )

    raw_data = data["data"]

    if not raw_data:
        raise ValueError(
            f"No macro data returned for {clean_function_name}."
        )

    macro_df = pd.DataFrame(raw_data)

    if "date" not in macro_df.columns or "value" not in macro_df.columns:
        raise ValueError(
            f"Expected columns 'date' and 'value' not found for {clean_function_name}."
        )

    macro_df = macro_df.rename(columns={
        "date": "Date",
        "value": "Value"
    })

    macro_df["Date"] = pd.to_datetime(
        macro_df["Date"],
        errors="coerce"
    )

    macro_df["Value"] = (
        macro_df["Value"]
        .replace([".", "None", "none", "N/A", "-", ""], pd.NA)
    )

    macro_df["Value"] = pd.to_numeric(
        macro_df["Value"],
        errors="coerce"
    )

    macro_df = macro_df.dropna(
        subset=["Date", "Value"]
    )

    macro_df = macro_df.sort_values("Date")

    macro_df["Indicator"] = clean_indicator_name
    macro_df["Function"] = clean_function_name
    macro_df["Interval"] = interval if interval else ""
    macro_df["Maturity"] = maturity if maturity else ""

    metadata_df = pd.DataFrame([{
        "Indicator": clean_indicator_name,
        "Function": clean_function_name,
        "Interval": interval if interval else "",
        "Maturity": maturity if maturity else "",
        "Name": data.get("name"),
        "Unit": data.get("unit"),
        "Rows": len(macro_df),
        "First Date": macro_df["Date"].min(),
        "Latest Date": macro_df["Date"].max(),
        "Cache File": str(cache_path),
        "Metadata Cache File": str(metadata_cache_path)
    }])

    macro_df.to_csv(
        cache_path,
        index=False
    )

    metadata_df.to_csv(
        metadata_cache_path,
        index=False
    )

    return macro_df, metadata_df


def get_multiple_macro_indicators(
    macro_indicators: list[dict],
    base_url: str,
    api_key: str,
    cache_dir: Path,
    force_refresh: bool = False,
    api_sleep_seconds: int = 15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Obtém dados para múltiplos indicadores macroeconómicos.

    Returns:
    - macro_values: DataFrame wide com valores por indicador
    - macro_long: DataFrame long com todos os dados
    - metadata: metadata consolidada
    - status: estado por indicador
    """

    macro_data_list = []
    metadata_list = []
    status_rows = []

    if not macro_indicators:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame([{
                "Indicator": "-",
                "Function": "-",
                "Status": "Error",
                "Rows": 0,
                "Source": "-",
                "Message": "No macro indicators provided."
            }])
        )

    for index, indicator_config in enumerate(macro_indicators):
        function_name = indicator_config["function"]
        indicator_name = indicator_config["name"]
        interval = indicator_config.get("interval")
        maturity = indicator_config.get("maturity")

        clean_function_name = function_name.strip().upper()

        cache_suffix_parts = [
            clean_function_name.lower()
        ]

        if interval:
            cache_suffix_parts.append(interval.lower())

        if maturity:
            cache_suffix_parts.append(maturity.lower())

        cache_suffix = "_".join(cache_suffix_parts)

        cache_path = cache_dir / f"macro_{cache_suffix}.csv"
        metadata_cache_path = cache_dir / f"macro_{cache_suffix}_metadata.csv"

        cache_exists_before_call = (
            cache_path.exists()
            and metadata_cache_path.exists()
            and not force_refresh
        )

        try:
            macro_df, metadata_df = get_macro_indicator_data(
                function_name=function_name,
                indicator_name=indicator_name,
                base_url=base_url,
                api_key=api_key,
                cache_dir=cache_dir,
                force_refresh=force_refresh,
                interval=interval,
                maturity=maturity
            )

            macro_data_list.append(macro_df)
            metadata_list.append(metadata_df)

            data_source = (
                "Local cache"
                if cache_exists_before_call
                else "Alpha Vantage API"
            )

            status_rows.append({
                "Indicator": indicator_name,
                "Function": function_name,
                "Interval": interval if interval else "",
                "Maturity": maturity if maturity else "",
                "Status": "Available",
                "Rows": len(macro_df),
                "Source": data_source,
                "Message": "Macro data loaded successfully."
            })

            should_sleep = (
                not cache_exists_before_call
                and index < len(macro_indicators) - 1
            )

            if should_sleep:
                time.sleep(api_sleep_seconds)

        except Exception as error:
            status_rows.append({
                "Indicator": indicator_name,
                "Function": function_name,
                "Interval": interval if interval else "",
                "Maturity": maturity if maturity else "",
                "Status": "Error",
                "Rows": 0,
                "Source": "Alpha Vantage API",
                "Message": str(error)
            })

    if macro_data_list:
        macro_long = pd.concat(
            macro_data_list,
            ignore_index=True
        )

        macro_values = macro_long.pivot_table(
            index="Date",
            columns="Indicator",
            values="Value",
            aggfunc="last"
        )

        macro_values = macro_values.sort_index()

    else:
        macro_long = pd.DataFrame()
        macro_values = pd.DataFrame()

    if metadata_list:
        metadata = pd.concat(
            metadata_list,
            ignore_index=True
        )
    else:
        metadata = pd.DataFrame()

    status = pd.DataFrame(status_rows)

    return macro_values, macro_long, metadata, status