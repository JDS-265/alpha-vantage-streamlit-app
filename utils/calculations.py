import numpy as np
import pandas as pd


# ============================================================
# RETURNS, PERFORMANCE AND RISK
# ============================================================

def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula retornos percentuais.

    fill_method=None evita o FutureWarning do pandas e impede que valores
    em falta sejam preenchidos automaticamente antes do cálculo.
    """

    if prices is None or prices.empty:
        return pd.DataFrame()

    returns = prices.pct_change(
        fill_method=None
    ).dropna(how="all")

    return returns


def calculate_performance_base_100(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula performance acumulada em base 100.

    Exemplo:
    - valor inicial = 100
    - valor final = 150
    - interpretação = valorização acumulada de 50%
    """

    if prices is None or prices.empty:
        return pd.DataFrame()

    returns = calculate_returns(prices)

    if returns.empty:
        return pd.DataFrame()

    performance = (1 + returns).cumprod() * 100

    first_valid_date = prices.dropna(how="all").index[0]

    base_row = pd.DataFrame(
        [[100 for _ in prices.columns]],
        index=[first_valid_date],
        columns=prices.columns
    )

    performance = pd.concat([
        base_row,
        performance
    ])

    performance = performance[
        ~performance.index.duplicated(keep="first")
    ]

    performance = performance.sort_index()

    return performance


def calculate_drawdowns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula drawdowns por ativo.

    Drawdown = preço atual / máximo anterior - 1
    """

    if prices is None or prices.empty:
        return pd.DataFrame()

    drawdowns = pd.DataFrame(index=prices.index)

    for column in prices.columns:
        series = prices[column].dropna()

        if series.empty:
            continue

        running_max = series.cummax()
        drawdown = series / running_max - 1

        drawdowns[column] = drawdown

    return drawdowns


def calculate_risk_return_summary(
    prices: pd.DataFrame,
    annualization_factor: int = 252
) -> pd.DataFrame:
    """
    Calcula métricas principais de risco/retorno.

    Métricas incluídas:
    - Total Return
    - Average Daily Return
    - Daily Volatility
    - Annualized Return
    - Annualized Volatility
    - Sharpe Ratio Simplified
    - Max Drawdown
    - Best Daily Return
    - Worst Daily Return
    - Positive Days %
    - Negative Days %
    """

    if prices is None or prices.empty:
        return pd.DataFrame()

    rows = []

    for ticker in prices.columns:
        price_series = prices[ticker].dropna()

        if price_series.empty:
            continue

        returns = price_series.pct_change(
            fill_method=None
        ).dropna()

        if returns.empty:
            continue

        first_price = price_series.iloc[0]
        latest_price = price_series.iloc[-1]

        total_return = latest_price / first_price - 1

        average_daily_return = returns.mean()
        daily_volatility = returns.std()

        annualized_return = (
            (1 + average_daily_return) ** annualization_factor - 1
        )

        annualized_volatility = (
            daily_volatility * np.sqrt(annualization_factor)
        )

        if annualized_volatility != 0 and pd.notna(annualized_volatility):
            sharpe_ratio_simplified = annualized_return / annualized_volatility
        else:
            sharpe_ratio_simplified = np.nan

        running_max = price_series.cummax()
        drawdown = price_series / running_max - 1
        max_drawdown = drawdown.min()

        best_daily_return = returns.max()
        worst_daily_return = returns.min()

        positive_days = (returns > 0).sum()
        negative_days = (returns < 0).sum()
        total_days = returns.count()

        rows.append({
            "Ticker": ticker,
            "First Date": price_series.index[0],
            "Latest Date": price_series.index[-1],
            "Observations": total_days,
            "First Price": first_price,
            "Latest Price": latest_price,
            "Total Return": total_return,
            "Average Daily Return": average_daily_return,
            "Daily Volatility": daily_volatility,
            "Annualized Return": annualized_return,
            "Annualized Volatility": annualized_volatility,
            "Sharpe Ratio Simplified": sharpe_ratio_simplified,
            "Max Drawdown": max_drawdown,
            "Best Daily Return": best_daily_return,
            "Worst Daily Return": worst_daily_return,
            "Positive Days": positive_days,
            "Negative Days": negative_days,
            "Positive Days %": positive_days / total_days if total_days else np.nan,
            "Negative Days %": negative_days / total_days if total_days else np.nan
        })

    summary = pd.DataFrame(rows)

    if not summary.empty:
        summary = summary.sort_values(
            by="Total Return",
            ascending=False
        )

    return summary


def calculate_correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula matriz de correlação dos retornos.
    """

    if returns is None or returns.empty:
        return pd.DataFrame()

    return returns.corr()


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def calculate_rsi_wilder(
    close_prices: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Calcula RSI usando o método de Wilder.

    RSI:
    - acima de 70 pode indicar sobrecompra;
    - abaixo de 30 pode indicar sobrevenda.
    """

    if close_prices is None or close_prices.empty:
        return pd.Series(dtype=float)

    delta = close_prices.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    average_loss = losses.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    relative_strength = average_gain / average_loss

    rsi = 100 - (100 / (1 + relative_strength))

    return rsi


def calculate_technical_indicators(
    close_prices: pd.Series,
    sma_short_window: int = 20,
    sma_long_window: int = 50,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9
) -> pd.DataFrame:
    """
    Calcula indicadores técnicos para uma série de preços.

    Indicadores incluídos:
    - SMA curta
    - SMA longa
    - RSI
    - EMA rápida
    - EMA lenta
    - MACD
    - MACD Signal
    - MACD Histogram
    - sinais técnicos simples
    """

    if close_prices is None or close_prices.empty:
        return pd.DataFrame()

    technical_df = pd.DataFrame(index=close_prices.index)

    technical_df["Close"] = pd.to_numeric(
        close_prices,
        errors="coerce"
    )

    technical_df[f"SMA_{sma_short_window}"] = technical_df["Close"].rolling(
        window=sma_short_window
    ).mean()

    technical_df[f"SMA_{sma_long_window}"] = technical_df["Close"].rolling(
        window=sma_long_window
    ).mean()

    technical_df[f"RSI_{rsi_period}"] = calculate_rsi_wilder(
        technical_df["Close"],
        period=rsi_period
    )

    technical_df["EMA_Fast"] = technical_df["Close"].ewm(
        span=macd_fast,
        adjust=False
    ).mean()

    technical_df["EMA_Slow"] = technical_df["Close"].ewm(
        span=macd_slow,
        adjust=False
    ).mean()

    technical_df["MACD"] = (
        technical_df["EMA_Fast"] - technical_df["EMA_Slow"]
    )

    technical_df["MACD_Signal"] = technical_df["MACD"].ewm(
        span=macd_signal,
        adjust=False
    ).mean()

    technical_df["MACD_Histogram"] = (
        technical_df["MACD"] - technical_df["MACD_Signal"]
    )

    technical_df["Price vs SMA Short"] = np.where(
        technical_df["Close"] > technical_df[f"SMA_{sma_short_window}"],
        "Above short SMA",
        "Below short SMA"
    )

    technical_df["Price vs SMA Long"] = np.where(
        technical_df["Close"] > technical_df[f"SMA_{sma_long_window}"],
        "Above long SMA",
        "Below long SMA"
    )

    technical_df["RSI Signal"] = np.where(
        technical_df[f"RSI_{rsi_period}"] >= 70,
        "Overbought",
        np.where(
            technical_df[f"RSI_{rsi_period}"] <= 30,
            "Oversold",
            "Neutral"
        )
    )

    technical_df["MACD Signal Label"] = np.where(
        technical_df["MACD"] > technical_df["MACD_Signal"],
        "Bullish MACD",
        "Bearish MACD"
    )

    technical_df["Trend Summary"] = np.where(
        (
            technical_df["Close"] > technical_df[f"SMA_{sma_short_window}"]
        )
        &
        (
            technical_df["MACD"] > technical_df["MACD_Signal"]
        ),
        "Positive Trend",
        np.where(
            (
                technical_df["Close"] < technical_df[f"SMA_{sma_short_window}"]
            )
            &
            (
                technical_df["MACD"] < technical_df["MACD_Signal"]
            ),
            "Negative Trend",
            "Mixed Signal"
        )
    )

    return technical_df


def create_technical_summary(
    ticker: str,
    technical_df: pd.DataFrame,
    sma_short_window: int = 20,
    sma_long_window: int = 50,
    rsi_period: int = 14
) -> pd.DataFrame:
    """
    Cria resumo técnico com a última observação válida.
    """

    if technical_df is None or technical_df.empty:
        return pd.DataFrame()

    required_numeric_columns = [
        "Close",
        f"SMA_{sma_short_window}",
        f"SMA_{sma_long_window}",
        f"RSI_{rsi_period}",
        "MACD",
        "MACD_Signal",
        "MACD_Histogram"
    ]

    existing_required_columns = [
        column
        for column in required_numeric_columns
        if column in technical_df.columns
    ]

    if len(existing_required_columns) < len(required_numeric_columns):
        return pd.DataFrame()

    valid_df = technical_df.dropna(
        subset=[
            "Close",
            f"SMA_{sma_short_window}",
            f"SMA_{sma_long_window}",
            f"RSI_{rsi_period}",
            "MACD",
            "MACD_Signal"
        ]
    )

    if valid_df.empty:
        return pd.DataFrame()

    latest = valid_df.iloc[-1]

    summary = pd.DataFrame([{
        "Ticker": ticker,
        "Latest Date": valid_df.index[-1],
        "Close": latest["Close"],
        f"SMA_{sma_short_window}": latest[f"SMA_{sma_short_window}"],
        f"SMA_{sma_long_window}": latest[f"SMA_{sma_long_window}"],
        f"RSI_{rsi_period}": latest[f"RSI_{rsi_period}"],
        "MACD": latest["MACD"],
        "MACD Signal": latest["MACD_Signal"],
        "MACD Histogram": latest["MACD_Histogram"],
        "Price vs SMA Short": latest["Price vs SMA Short"],
        "Price vs SMA Long": latest["Price vs SMA Long"],
        "RSI Signal": latest["RSI Signal"],
        "MACD Signal Label": latest["MACD Signal Label"],
        "Trend Summary": latest["Trend Summary"]
    }])

    return summary


# ============================================================
# DISPLAY FORMATTING
# ============================================================

def format_summary_for_display(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Cria uma versão formatada em texto para leitura na app.

    Esta função é usada principalmente para tabelas de resumo.
    """

    if summary is None or summary.empty:
        return pd.DataFrame()

    display_df = summary.copy()

    percent_columns = [
        "Total Return",
        "Average Daily Return",
        "Daily Volatility",
        "Annualized Return",
        "Annualized Volatility",
        "Max Drawdown",
        "Best Daily Return",
        "Worst Daily Return",
        "Positive Days %",
        "Negative Days %"
    ]

    price_columns = [
        "First Price",
        "Latest Price",
        "Close",
        "SMA_20",
        "SMA_50"
    ]

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2%}" if pd.notna(value) else ""
            )

    for column in price_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:,.2f}" if pd.notna(value) else ""
            )

    if "Sharpe Ratio Simplified" in display_df.columns:
        display_df["Sharpe Ratio Simplified"] = display_df[
            "Sharpe Ratio Simplified"
        ].apply(
            lambda value: f"{value:.2f}" if pd.notna(value) else ""
        )

    return display_df




# ============================================================
# FUNDAMENTAL ANALYSIS
# ============================================================

def safe_rank_score(
    series: pd.Series,
    higher_is_better: bool = True
) -> pd.Series:
    """
    Cria score percentual de ranking entre 0 e 100.

    higher_is_better=True:
    - valores mais altos recebem melhor score.

    higher_is_better=False:
    - valores mais baixos recebem melhor score.
    """

    numeric_series = pd.to_numeric(
        series,
        errors="coerce"
    )

    if numeric_series.dropna().empty:
        return pd.Series(
            np.nan,
            index=series.index
        )

    if higher_is_better:
        score = numeric_series.rank(
            ascending=True,
            pct=True
        ) * 100
    else:
        score = numeric_series.rank(
            ascending=False,
            pct=True
        ) * 100

    return score


def create_fundamental_ranking(overview_df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria ranking fundamental simples com base no endpoint OVERVIEW.

    O score é educacional e não deve ser interpretado como recomendação.
    """

    if overview_df is None or overview_df.empty:
        return pd.DataFrame()

    ranking_df = overview_df.copy()

    score_definitions = {
        "MarketCap Score": {
            "Column": "MarketCapitalization",
            "Higher Is Better": True
        },
        "Revenue Score": {
            "Column": "RevenueTTM",
            "Higher Is Better": True
        },
        "Profit Margin Score": {
            "Column": "ProfitMargin",
            "Higher Is Better": True
        },
        "Operating Margin Score": {
            "Column": "OperatingMarginTTM",
            "Higher Is Better": True
        },
        "ROA Score": {
            "Column": "ReturnOnAssetsTTM",
            "Higher Is Better": True
        },
        "ROE Score": {
            "Column": "ReturnOnEquityTTM",
            "Higher Is Better": True
        },
        "Revenue Growth Score": {
            "Column": "QuarterlyRevenueGrowthYOY",
            "Higher Is Better": True
        },
        "Earnings Growth Score": {
            "Column": "QuarterlyEarningsGrowthYOY",
            "Higher Is Better": True
        },
        "PE Score": {
            "Column": "PERatio",
            "Higher Is Better": False
        },
        "Price Sales Score": {
            "Column": "PriceToSalesRatioTTM",
            "Higher Is Better": False
        },
        "Price Book Score": {
            "Column": "PriceToBookRatio",
            "Higher Is Better": False
        },
        "EV EBITDA Score": {
            "Column": "EVToEBITDA",
            "Higher Is Better": False
        },
        "Beta Score": {
            "Column": "Beta",
            "Higher Is Better": False
        }
    }

    score_columns = []

    for score_name, config in score_definitions.items():
        source_column = config["Column"]

        if source_column in ranking_df.columns:
            ranking_df[score_name] = safe_rank_score(
                ranking_df[source_column],
                higher_is_better=config["Higher Is Better"]
            )

            score_columns.append(score_name)

    if score_columns:
        ranking_df["Fundamental Score"] = ranking_df[
            score_columns
        ].mean(
            axis=1,
            skipna=True
        )
    else:
        ranking_df["Fundamental Score"] = np.nan

    display_columns = [
        "Symbol",
        "Name",
        "Sector",
        "Industry",
        "MarketCapitalization",
        "RevenueTTM",
        "PERatio",
        "PriceToSalesRatioTTM",
        "PriceToBookRatio",
        "ProfitMargin",
        "OperatingMarginTTM",
        "ReturnOnAssetsTTM",
        "ReturnOnEquityTTM",
        "QuarterlyRevenueGrowthYOY",
        "QuarterlyEarningsGrowthYOY",
        "Beta",
        "Fundamental Score"
    ]

    existing_columns = [
        column
        for column in display_columns
        if column in ranking_df.columns
    ]

    ranking_df = ranking_df[existing_columns]

    ranking_df = ranking_df.sort_values(
        by="Fundamental Score",
        ascending=False
    )

    return ranking_df


def format_fundamental_table_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Formata tabela fundamental para leitura na app.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    display_df = df.copy()

    money_columns = [
        "MarketCapitalization",
        "EBITDA",
        "RevenueTTM",
        "GrossProfitTTM",
        "AnalystTargetPrice",
        "52WeekHigh",
        "52WeekLow",
        "50DayMovingAverage",
        "200DayMovingAverage"
    ]

    percent_columns = [
        "DividendYield",
        "ProfitMargin",
        "OperatingMarginTTM",
        "ReturnOnAssetsTTM",
        "ReturnOnEquityTTM",
        "QuarterlyEarningsGrowthYOY",
        "QuarterlyRevenueGrowthYOY"
    ]

    ratio_columns = [
        "PERatio",
        "PEGRatio",
        "TrailingPE",
        "ForwardPE",
        "PriceToSalesRatioTTM",
        "PriceToBookRatio",
        "EVToRevenue",
        "EVToEBITDA",
        "Beta",
        "Fundamental Score"
    ]

    shares_columns = [
        "SharesOutstanding"
    ]

    for column in money_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"${value:,.0f}" if pd.notna(value) else ""
            )

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2%}" if pd.notna(value) else ""
            )

    for column in ratio_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2f}" if pd.notna(value) else ""
            )

    for column in shares_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:,.0f}" if pd.notna(value) else ""
            )

    return display_df


# ============================================================
# COMMODITIES ANALYSIS
# ============================================================

def calculate_commodity_summary(
    commodity_values: pd.DataFrame,
    annualization_factor: int = 12
) -> pd.DataFrame:
    """
    Calcula métricas principais para commodities.

    Como vamos usar dados mensais, o annualization_factor padrão é 12.

    Métricas:
    - First Value
    - Latest Value
    - Total Return
    - Average Monthly Return
    - Monthly Volatility
    - Annualized Return
    - Annualized Volatility
    - Sharpe Ratio Simplified
    - Max Drawdown
    - Best Monthly Return
    - Worst Monthly Return
    """

    if commodity_values is None or commodity_values.empty:
        return pd.DataFrame()

    rows = []

    for commodity in commodity_values.columns:
        value_series = commodity_values[commodity].dropna()

        if value_series.empty:
            continue

        returns = value_series.pct_change(
            fill_method=None
        ).dropna()

        if returns.empty:
            continue

        first_value = value_series.iloc[0]
        latest_value = value_series.iloc[-1]

        total_return = latest_value / first_value - 1

        average_monthly_return = returns.mean()
        monthly_volatility = returns.std()

        annualized_return = (
            (1 + average_monthly_return) ** annualization_factor - 1
        )

        annualized_volatility = (
            monthly_volatility * np.sqrt(annualization_factor)
        )

        if annualized_volatility != 0 and pd.notna(annualized_volatility):
            sharpe_ratio_simplified = annualized_return / annualized_volatility
        else:
            sharpe_ratio_simplified = np.nan

        running_max = value_series.cummax()
        drawdown = value_series / running_max - 1
        max_drawdown = drawdown.min()

        best_monthly_return = returns.max()
        worst_monthly_return = returns.min()

        positive_months = (returns > 0).sum()
        negative_months = (returns < 0).sum()
        total_months = returns.count()

        rows.append({
            "Commodity": commodity,
            "First Date": value_series.index[0],
            "Latest Date": value_series.index[-1],
            "Observations": total_months,
            "First Value": first_value,
            "Latest Value": latest_value,
            "Total Return": total_return,
            "Average Monthly Return": average_monthly_return,
            "Monthly Volatility": monthly_volatility,
            "Annualized Return": annualized_return,
            "Annualized Volatility": annualized_volatility,
            "Sharpe Ratio Simplified": sharpe_ratio_simplified,
            "Max Drawdown": max_drawdown,
            "Best Monthly Return": best_monthly_return,
            "Worst Monthly Return": worst_monthly_return,
            "Positive Months": positive_months,
            "Negative Months": negative_months,
            "Positive Months %": positive_months / total_months if total_months else np.nan,
            "Negative Months %": negative_months / total_months if total_months else np.nan
        })

    summary = pd.DataFrame(rows)

    if not summary.empty:
        summary = summary.sort_values(
            by="Total Return",
            ascending=False
        )

    return summary


def format_commodity_summary_for_display(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Formata a tabela de resumo de commodities para leitura na app.
    """

    if summary is None or summary.empty:
        return pd.DataFrame()

    display_df = summary.copy()

    value_columns = [
        "First Value",
        "Latest Value"
    ]

    percent_columns = [
        "Total Return",
        "Average Monthly Return",
        "Monthly Volatility",
        "Annualized Return",
        "Annualized Volatility",
        "Max Drawdown",
        "Best Monthly Return",
        "Worst Monthly Return",
        "Positive Months %",
        "Negative Months %"
    ]

    ratio_columns = [
        "Sharpe Ratio Simplified"
    ]

    for column in value_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:,.2f}" if pd.notna(value) else ""
            )

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2%}" if pd.notna(value) else ""
            )

    for column in ratio_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2f}" if pd.notna(value) else ""
            )

    return display_df


# ============================================================
# FX ANALYSIS
# ============================================================

def calculate_fx_summary(
    fx_close_prices: pd.DataFrame,
    annualization_factor: int = 252
) -> pd.DataFrame:
    """
    Calcula métricas principais para pares cambiais.

    Como estamos a usar dados diários, o annualization_factor padrão é 252.

    Métricas:
    - First Rate
    - Latest Rate
    - Total Return
    - Average Daily Return
    - Daily Volatility
    - Annualized Return
    - Annualized Volatility
    - Sharpe Ratio Simplified
    - Max Drawdown
    - Best Daily Return
    - Worst Daily Return

    Interpretação:
    Para EUR/USD, retorno positivo significa valorização do EUR face ao USD.
    Para USD/JPY, retorno positivo significa valorização do USD face ao JPY.
    """

    if fx_close_prices is None or fx_close_prices.empty:
        return pd.DataFrame()

    rows = []

    for pair in fx_close_prices.columns:
        rate_series = fx_close_prices[pair].dropna()

        if rate_series.empty:
            continue

        returns = rate_series.pct_change(
            fill_method=None
        ).dropna()

        if returns.empty:
            continue

        first_rate = rate_series.iloc[0]
        latest_rate = rate_series.iloc[-1]

        total_return = latest_rate / first_rate - 1

        average_daily_return = returns.mean()
        daily_volatility = returns.std()

        annualized_return = (
            (1 + average_daily_return) ** annualization_factor - 1
        )

        annualized_volatility = (
            daily_volatility * np.sqrt(annualization_factor)
        )

        if annualized_volatility != 0 and pd.notna(annualized_volatility):
            sharpe_ratio_simplified = annualized_return / annualized_volatility
        else:
            sharpe_ratio_simplified = np.nan

        running_max = rate_series.cummax()
        drawdown = rate_series / running_max - 1
        max_drawdown = drawdown.min()

        best_daily_return = returns.max()
        worst_daily_return = returns.min()

        positive_days = (returns > 0).sum()
        negative_days = (returns < 0).sum()
        total_days = returns.count()

        if "/" in pair:
            base_currency = pair.split("/")[0]
            quote_currency = pair.split("/")[1]
        else:
            base_currency = ""
            quote_currency = ""

        if total_return > 0:
            direction_interpretation = (
                f"{base_currency} strengthened vs {quote_currency}"
                if base_currency and quote_currency
                else "Pair increased"
            )
        elif total_return < 0:
            direction_interpretation = (
                f"{base_currency} weakened vs {quote_currency}"
                if base_currency and quote_currency
                else "Pair decreased"
            )
        else:
            direction_interpretation = "No change"

        rows.append({
            "Pair": pair,
            "Base Currency": base_currency,
            "Quote Currency": quote_currency,
            "First Date": rate_series.index[0],
            "Latest Date": rate_series.index[-1],
            "Observations": total_days,
            "First Rate": first_rate,
            "Latest Rate": latest_rate,
            "Total Return": total_return,
            "Average Daily Return": average_daily_return,
            "Daily Volatility": daily_volatility,
            "Annualized Return": annualized_return,
            "Annualized Volatility": annualized_volatility,
            "Sharpe Ratio Simplified": sharpe_ratio_simplified,
            "Max Drawdown": max_drawdown,
            "Best Daily Return": best_daily_return,
            "Worst Daily Return": worst_daily_return,
            "Positive Days": positive_days,
            "Negative Days": negative_days,
            "Positive Days %": positive_days / total_days if total_days else np.nan,
            "Negative Days %": negative_days / total_days if total_days else np.nan,
            "Direction Interpretation": direction_interpretation
        })

    summary = pd.DataFrame(rows)

    if not summary.empty:
        summary = summary.sort_values(
            by="Total Return",
            ascending=False
        )

    return summary


def format_fx_summary_for_display(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Formata a tabela de resumo FX para leitura na app.
    """

    if summary is None or summary.empty:
        return pd.DataFrame()

    display_df = summary.copy()

    rate_columns = [
        "First Rate",
        "Latest Rate"
    ]

    percent_columns = [
        "Total Return",
        "Average Daily Return",
        "Daily Volatility",
        "Annualized Return",
        "Annualized Volatility",
        "Max Drawdown",
        "Best Daily Return",
        "Worst Daily Return",
        "Positive Days %",
        "Negative Days %"
    ]

    ratio_columns = [
        "Sharpe Ratio Simplified"
    ]

    for column in rate_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:,.4f}" if pd.notna(value) else ""
            )

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2%}" if pd.notna(value) else ""
            )

    for column in ratio_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2f}" if pd.notna(value) else ""
            )

    return display_df



# ============================================================
# CRYPTO ANALYSIS
# ============================================================

def calculate_crypto_summary(
    crypto_close_prices: pd.DataFrame,
    annualization_factor: int = 365
) -> pd.DataFrame:
    """
    Calcula métricas principais para criptoativos.

    Como crypto negoceia todos os dias, o annualization_factor padrão é 365.

    Métricas:
    - First Price
    - Latest Price
    - Total Return
    - Average Daily Return
    - Daily Volatility
    - Annualized Return
    - Annualized Volatility
    - Sharpe Ratio Simplified
    - Max Drawdown
    - Best Daily Return
    - Worst Daily Return
    """

    if crypto_close_prices is None or crypto_close_prices.empty:
        return pd.DataFrame()

    rows = []

    for pair in crypto_close_prices.columns:
        price_series = crypto_close_prices[pair].dropna()

        if price_series.empty:
            continue

        returns = price_series.pct_change(
            fill_method=None
        ).dropna()

        if returns.empty:
            continue

        first_price = price_series.iloc[0]
        latest_price = price_series.iloc[-1]

        total_return = latest_price / first_price - 1

        average_daily_return = returns.mean()
        daily_volatility = returns.std()

        annualized_return = (
            (1 + average_daily_return) ** annualization_factor - 1
        )

        annualized_volatility = (
            daily_volatility * np.sqrt(annualization_factor)
        )

        if annualized_volatility != 0 and pd.notna(annualized_volatility):
            sharpe_ratio_simplified = annualized_return / annualized_volatility
        else:
            sharpe_ratio_simplified = np.nan

        running_max = price_series.cummax()
        drawdown = price_series / running_max - 1
        max_drawdown = drawdown.min()

        best_daily_return = returns.max()
        worst_daily_return = returns.min()

        positive_days = (returns > 0).sum()
        negative_days = (returns < 0).sum()
        total_days = returns.count()

        if "/" in pair:
            crypto_symbol = pair.split("/")[0]
            market_symbol = pair.split("/")[1]
        else:
            crypto_symbol = pair
            market_symbol = ""

        rows.append({
            "Pair": pair,
            "Crypto Symbol": crypto_symbol,
            "Market Symbol": market_symbol,
            "First Date": price_series.index[0],
            "Latest Date": price_series.index[-1],
            "Observations": total_days,
            "First Price": first_price,
            "Latest Price": latest_price,
            "Total Return": total_return,
            "Average Daily Return": average_daily_return,
            "Daily Volatility": daily_volatility,
            "Annualized Return": annualized_return,
            "Annualized Volatility": annualized_volatility,
            "Sharpe Ratio Simplified": sharpe_ratio_simplified,
            "Max Drawdown": max_drawdown,
            "Best Daily Return": best_daily_return,
            "Worst Daily Return": worst_daily_return,
            "Positive Days": positive_days,
            "Negative Days": negative_days,
            "Positive Days %": positive_days / total_days if total_days else np.nan,
            "Negative Days %": negative_days / total_days if total_days else np.nan
        })

    summary = pd.DataFrame(rows)

    if not summary.empty:
        summary = summary.sort_values(
            by="Total Return",
            ascending=False
        )

    return summary


def format_crypto_summary_for_display(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Formata a tabela de resumo Crypto para leitura na app.
    """

    if summary is None or summary.empty:
        return pd.DataFrame()

    display_df = summary.copy()

    price_columns = [
        "First Price",
        "Latest Price"
    ]

    percent_columns = [
        "Total Return",
        "Average Daily Return",
        "Daily Volatility",
        "Annualized Return",
        "Annualized Volatility",
        "Max Drawdown",
        "Best Daily Return",
        "Worst Daily Return",
        "Positive Days %",
        "Negative Days %"
    ]

    ratio_columns = [
        "Sharpe Ratio Simplified"
    ]

    for column in price_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:,.2f}" if pd.notna(value) else ""
            )

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2%}" if pd.notna(value) else ""
            )

    for column in ratio_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2f}" if pd.notna(value) else ""
            )

    return display_df




# ============================================================
# MACROECONOMIC ANALYSIS
# ============================================================

def calculate_macro_changes(
    macro_values: pd.DataFrame,
    periods_for_yoy: int = 12
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calcula variações dos indicadores macroeconómicos.

    Como os dados macro são geralmente mensais, usamos:
    - MoM Change: diferença face ao mês anterior
    - YoY Change: diferença face ao mesmo mês do ano anterior
    - YoY % Change: variação percentual face ao mesmo mês do ano anterior

    Para taxas como Fed Funds, Treasury Yield e Unemployment,
    a diferença em pontos percentuais é muitas vezes mais útil do que pct_change.
    """

    if macro_values is None or macro_values.empty:
        return pd.DataFrame(), pd.DataFrame()

    mom_change = macro_values.diff()

    yoy_change = macro_values.diff(periods=periods_for_yoy)

    yoy_percent_change = macro_values.pct_change(
        periods=periods_for_yoy,
        fill_method=None
    )

    macro_changes = pd.concat(
        {
            "Value": macro_values,
            "MoM Change": mom_change,
            "YoY Change": yoy_change,
            "YoY % Change": yoy_percent_change
        },
        axis=1
    )

    macro_changes_long = []

    for indicator in macro_values.columns:
        indicator_df = pd.DataFrame({
            "Date": macro_values.index,
            "Indicator": indicator,
            "Value": macro_values[indicator],
            "MoM Change": mom_change[indicator],
            "YoY Change": yoy_change[indicator],
            "YoY % Change": yoy_percent_change[indicator]
        })

        macro_changes_long.append(indicator_df)

    if macro_changes_long:
        macro_changes_long = pd.concat(
            macro_changes_long,
            ignore_index=True
        )
    else:
        macro_changes_long = pd.DataFrame()

    return macro_changes, macro_changes_long


def calculate_macro_summary(
    macro_values: pd.DataFrame,
    periods_for_yoy: int = 12
) -> pd.DataFrame:
    """
    Calcula uma tabela resumo para indicadores macroeconómicos.

    Métricas:
    - First Value
    - Latest Value
    - Absolute Change
    - Latest MoM Change
    - Latest YoY Change
    - Latest YoY % Change
    - Minimum Value
    - Maximum Value
    - Average Value
    """

    if macro_values is None or macro_values.empty:
        return pd.DataFrame()

    _, macro_changes_long = calculate_macro_changes(
        macro_values=macro_values,
        periods_for_yoy=periods_for_yoy
    )

    rows = []

    for indicator in macro_values.columns:
        series = macro_values[indicator].dropna()

        if series.empty:
            continue

        indicator_changes = macro_changes_long[
            macro_changes_long["Indicator"] == indicator
        ].dropna(subset=["Value"])

        latest_row = indicator_changes.sort_values(
            "Date"
        ).iloc[-1]

        first_value = series.iloc[0]
        latest_value = series.iloc[-1]

        rows.append({
            "Indicator": indicator,
            "First Date": series.index[0],
            "Latest Date": series.index[-1],
            "Observations": series.count(),
            "First Value": first_value,
            "Latest Value": latest_value,
            "Absolute Change": latest_value - first_value,
            "Latest MoM Change": latest_row.get("MoM Change"),
            "Latest YoY Change": latest_row.get("YoY Change"),
            "Latest YoY % Change": latest_row.get("YoY % Change"),
            "Minimum Value": series.min(),
            "Maximum Value": series.max(),
            "Average Value": series.mean()
        })

    summary = pd.DataFrame(rows)

    return summary


def format_macro_summary_for_display(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Formata a tabela macro para leitura na app.
    """

    if summary is None or summary.empty:
        return pd.DataFrame()

    display_df = summary.copy()

    value_columns = [
        "First Value",
        "Latest Value",
        "Absolute Change",
        "Latest MoM Change",
        "Latest YoY Change",
        "Minimum Value",
        "Maximum Value",
        "Average Value"
    ]

    percent_columns = [
        "Latest YoY % Change"
    ]

    for column in value_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:,.2f}" if pd.notna(value) else ""
            )

    for column in percent_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: f"{value:.2%}" if pd.notna(value) else ""
            )

    return display_df