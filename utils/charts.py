import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ============================================================
# STOCK CHARTS
# ============================================================

def plot_price_chart(prices: pd.DataFrame):
    """
    Gráfico de preços de fecho.
    """

    if prices is None or prices.empty:
        return None

    fig = px.line(
        prices,
        x=prices.index,
        y=prices.columns,
        title="Stock Prices",
        labels={
            "value": "Close Price",
            "Date": "Date",
            "variable": "Ticker"
        }
    )

    fig.update_layout(
        legend_title_text="Ticker",
        hovermode="x unified"
    )

    return fig


def plot_performance_base_100(performance: pd.DataFrame):
    """
    Gráfico de performance acumulada em base 100.
    """

    if performance is None or performance.empty:
        return None

    fig = px.line(
        performance,
        x=performance.index,
        y=performance.columns,
        title="Performance Base 100",
        labels={
            "value": "Base 100",
            "Date": "Date",
            "variable": "Ticker"
        }
    )

    fig.update_layout(
        legend_title_text="Ticker",
        hovermode="x unified"
    )

    return fig


def plot_drawdowns(drawdowns: pd.DataFrame):
    """
    Gráfico de drawdowns.
    """

    if drawdowns is None or drawdowns.empty:
        return None

    fig = px.line(
        drawdowns,
        x=drawdowns.index,
        y=drawdowns.columns,
        title="Drawdowns",
        labels={
            "value": "Drawdown",
            "Date": "Date",
            "variable": "Ticker"
        }
    )

    fig.update_layout(
        legend_title_text="Ticker",
        hovermode="x unified"
    )

    fig.update_yaxes(
        tickformat=".0%"
    )

    return fig


def plot_returns_histogram(returns: pd.DataFrame):
    """
    Histograma dos retornos diários.
    """

    if returns is None or returns.empty:
        return None

    returns_long = returns.reset_index().melt(
        id_vars="Date",
        var_name="Ticker",
        value_name="Daily Return"
    )

    fig = px.histogram(
        returns_long,
        x="Daily Return",
        color="Ticker",
        nbins=50,
        title="Daily Returns Distribution",
        barmode="overlay"
    )

    fig.update_layout(
        hovermode="x unified"
    )

    fig.update_xaxes(
        tickformat=".2%"
    )

    return fig


def plot_risk_return_scatter(summary: pd.DataFrame):
    """
    Gráfico risco-retorno.
    """

    if summary is None or summary.empty:
        return None

    fig = px.scatter(
        summary,
        x="Annualized Volatility",
        y="Annualized Return",
        text="Ticker",
        title="Risk vs Return",
        labels={
            "Annualized Volatility": "Annualized Volatility",
            "Annualized Return": "Annualized Return"
        }
    )

    fig.update_traces(
        textposition="top center",
        marker=dict(size=12)
    )

    fig.update_xaxes(
        tickformat=".0%"
    )

    fig.update_yaxes(
        tickformat=".0%"
    )

    return fig


def plot_correlation_heatmap(correlation_matrix: pd.DataFrame):
    """
    Heatmap da matriz de correlação.
    """

    if correlation_matrix is None or correlation_matrix.empty:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Correlation")
        )
    )

    fig.update_layout(
        title="Returns Correlation Matrix"
    )

    return fig


# ============================================================
# TECHNICAL INDICATORS CHARTS
# ============================================================

def plot_technical_price_sma(
    technical_df: pd.DataFrame,
    ticker: str,
    sma_short_window: int = 20,
    sma_long_window: int = 50
):
    """
    Gráfico de preço de fecho com SMA curta e SMA longa.
    """

    if technical_df is None or technical_df.empty:
        return None

    if "Close" not in technical_df.columns:
        return None

    short_column = f"SMA_{sma_short_window}"
    long_column = f"SMA_{sma_long_window}"

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=technical_df.index,
            y=technical_df["Close"],
            mode="lines",
            name="Close"
        )
    )

    if short_column in technical_df.columns:
        fig.add_trace(
            go.Scatter(
                x=technical_df.index,
                y=technical_df[short_column],
                mode="lines",
                name=short_column
            )
        )

    if long_column in technical_df.columns:
        fig.add_trace(
            go.Scatter(
                x=technical_df.index,
                y=technical_df[long_column],
                mode="lines",
                name=long_column
            )
        )

    fig.update_layout(
        title=f"{ticker} - Close Price and Moving Averages",
        xaxis_title="Date",
        yaxis_title="Price",
        hovermode="x unified",
        legend_title_text="Indicator"
    )

    return fig


def plot_rsi(
    technical_df: pd.DataFrame,
    ticker: str,
    rsi_period: int = 14
):
    """
    Gráfico RSI.
    """

    if technical_df is None or technical_df.empty:
        return None

    rsi_column = f"RSI_{rsi_period}"

    if rsi_column not in technical_df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=technical_df.index,
            y=technical_df[rsi_column],
            mode="lines",
            name=rsi_column
        )
    )

    fig.add_hline(
        y=70,
        line_dash="dash",
        annotation_text="Overbought 70"
    )

    fig.add_hline(
        y=30,
        line_dash="dash",
        annotation_text="Oversold 30"
    )

    fig.update_layout(
        title=f"{ticker} - RSI {rsi_period}",
        xaxis_title="Date",
        yaxis_title="RSI",
        hovermode="x unified",
        legend_title_text="Indicator"
    )

    fig.update_yaxes(
        range=[0, 100]
    )

    return fig


def plot_macd(
    technical_df: pd.DataFrame,
    ticker: str
):
    """
    Gráfico MACD, MACD Signal e MACD Histogram.
    """

    if technical_df is None or technical_df.empty:
        return None

    required_columns = [
        "MACD",
        "MACD_Signal",
        "MACD_Histogram"
    ]

    for column in required_columns:
        if column not in technical_df.columns:
            return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=technical_df.index,
            y=technical_df["MACD"],
            mode="lines",
            name="MACD"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=technical_df.index,
            y=technical_df["MACD_Signal"],
            mode="lines",
            name="MACD Signal"
        )
    )

    fig.add_trace(
        go.Bar(
            x=technical_df.index,
            y=technical_df["MACD_Histogram"],
            name="MACD Histogram"
        )
    )

    fig.update_layout(
        title=f"{ticker} - MACD",
        xaxis_title="Date",
        yaxis_title="MACD",
        hovermode="x unified",
        legend_title_text="Indicator"
    )

    return fig


# ============================================================
# FUNDAMENTAL ANALYSIS CHARTS
# ============================================================

def plot_fundamental_bar(
    df: pd.DataFrame,
    metric: str,
    title: str,
    y_axis_title: str,
    y_tickformat: str | None = None
):
    """
    Cria gráfico de barras para uma métrica fundamental.
    """

    if df is None or df.empty:
        return None

    if "Symbol" not in df.columns or metric not in df.columns:
        return None

    chart_df = df[["Symbol", metric]].copy()

    chart_df[metric] = pd.to_numeric(
        chart_df[metric],
        errors="coerce"
    )

    chart_df = chart_df.dropna(subset=[metric])

    if chart_df.empty:
        return None

    chart_df = chart_df.sort_values(
        by=metric,
        ascending=False
    )

    fig = px.bar(
        chart_df,
        x="Symbol",
        y=metric,
        title=title,
        text=metric,
        labels={
            metric: y_axis_title,
            "Symbol": "Ticker"
        }
    )

    if y_tickformat:
        fig.update_yaxes(
            tickformat=y_tickformat
        )

    fig.update_layout(
        hovermode="x unified"
    )

    return fig


def plot_fundamental_grouped_bars(
    df: pd.DataFrame,
    metrics: list[str],
    title: str,
    y_axis_title: str,
    y_tickformat: str | None = None
):
    """
    Cria gráfico de barras agrupadas para várias métricas fundamentais.
    """

    if df is None or df.empty:
        return None

    if "Symbol" not in df.columns:
        return None

    available_metrics = [
        metric
        for metric in metrics
        if metric in df.columns
    ]

    if not available_metrics:
        return None

    chart_df = df[
        ["Symbol"] + available_metrics
    ].copy()

    for metric in available_metrics:
        chart_df[metric] = pd.to_numeric(
            chart_df[metric],
            errors="coerce"
        )

    chart_long = chart_df.melt(
        id_vars="Symbol",
        value_vars=available_metrics,
        var_name="Metric",
        value_name="Value"
    )

    chart_long = chart_long.dropna(subset=["Value"])

    if chart_long.empty:
        return None

    fig = px.bar(
        chart_long,
        x="Symbol",
        y="Value",
        color="Metric",
        barmode="group",
        title=title,
        labels={
            "Value": y_axis_title,
            "Symbol": "Ticker"
        }
    )

    if y_tickformat:
        fig.update_yaxes(
            tickformat=y_tickformat
        )

    fig.update_layout(
        hovermode="x unified"
    )

    return fig

   
# ============================================================
# COMMODITIES CHARTS
# ============================================================

def plot_commodity_values(commodity_values: pd.DataFrame):
    """
    Gráfico dos valores das commodities.
    """

    if commodity_values is None or commodity_values.empty:
        return None

    fig = px.line(
        commodity_values,
        x=commodity_values.index,
        y=commodity_values.columns,
        title="Commodity Values",
        labels={
            "value": "Value",
            "Date": "Date",
            "variable": "Commodity"
        }
    )

    fig.update_layout(
        legend_title_text="Commodity",
        hovermode="x unified"
    )

    return fig


def plot_commodity_performance(performance: pd.DataFrame):
    """
    Gráfico de performance base 100 das commodities.
    """

    if performance is None or performance.empty:
        return None

    fig = px.line(
        performance,
        x=performance.index,
        y=performance.columns,
        title="Commodities Performance Base 100",
        labels={
            "value": "Base 100",
            "Date": "Date",
            "variable": "Commodity"
        }
    )

    fig.update_layout(
        legend_title_text="Commodity",
        hovermode="x unified"
    )

    return fig


def plot_commodity_drawdowns(drawdowns: pd.DataFrame):
    """
    Gráfico de drawdowns das commodities.
    """

    if drawdowns is None or drawdowns.empty:
        return None

    fig = px.line(
        drawdowns,
        x=drawdowns.index,
        y=drawdowns.columns,
        title="Commodities Drawdowns",
        labels={
            "value": "Drawdown",
            "Date": "Date",
            "variable": "Commodity"
        }
    )

    fig.update_layout(
        legend_title_text="Commodity",
        hovermode="x unified"
    )

    fig.update_yaxes(
        tickformat=".0%"
    )

    return fig


def plot_commodity_correlation(correlation_matrix: pd.DataFrame):
    """
    Heatmap de correlação das commodities.
    """

    if correlation_matrix is None or correlation_matrix.empty:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Correlation")
        )
    )

    fig.update_layout(
        title="Commodities Returns Correlation Matrix"
    )

    return fig


def plot_commodity_summary_bar(
    summary: pd.DataFrame,
    metric: str,
    title: str,
    y_axis_title: str,
    y_tickformat: str | None = None
):
    """
    Gráfico de barras para métricas de commodities.
    """

    if summary is None or summary.empty:
        return None

    if "Commodity" not in summary.columns or metric not in summary.columns:
        return None

    chart_df = summary[
        ["Commodity", metric]
    ].copy()

    chart_df[metric] = pd.to_numeric(
        chart_df[metric],
        errors="coerce"
    )

    chart_df = chart_df.dropna(subset=[metric])

    if chart_df.empty:
        return None

    chart_df = chart_df.sort_values(
        by=metric,
        ascending=False
    )

    fig = px.bar(
        chart_df,
        x="Commodity",
        y=metric,
        title=title,
        text=metric,
        labels={
            "Commodity": "Commodity",
            metric: y_axis_title
        }
    )

    if y_tickformat:
        fig.update_yaxes(
            tickformat=y_tickformat
        )

    fig.update_layout(
        hovermode="x unified"
    )

    return fig



# ============================================================
# FX CHARTS
# ============================================================

def plot_fx_rates(fx_close_prices: pd.DataFrame):
    """
    Gráfico dos câmbios de fecho.
    """

    if fx_close_prices is None or fx_close_prices.empty:
        return None

    fig = px.line(
        fx_close_prices,
        x=fx_close_prices.index,
        y=fx_close_prices.columns,
        title="FX Exchange Rates",
        labels={
            "value": "Exchange Rate",
            "Date": "Date",
            "variable": "FX Pair"
        }
    )

    fig.update_layout(
        legend_title_text="FX Pair",
        hovermode="x unified"
    )

    return fig


def plot_fx_performance(performance: pd.DataFrame):
    """
    Gráfico de performance base 100 dos pares cambiais.
    """

    if performance is None or performance.empty:
        return None

    fig = px.line(
        performance,
        x=performance.index,
        y=performance.columns,
        title="FX Performance Base 100",
        labels={
            "value": "Base 100",
            "Date": "Date",
            "variable": "FX Pair"
        }
    )

    fig.update_layout(
        legend_title_text="FX Pair",
        hovermode="x unified"
    )

    return fig


def plot_fx_drawdowns(drawdowns: pd.DataFrame):
    """
    Gráfico de drawdowns dos pares cambiais.
    """

    if drawdowns is None or drawdowns.empty:
        return None

    fig = px.line(
        drawdowns,
        x=drawdowns.index,
        y=drawdowns.columns,
        title="FX Drawdowns",
        labels={
            "value": "Drawdown",
            "Date": "Date",
            "variable": "FX Pair"
        }
    )

    fig.update_layout(
        legend_title_text="FX Pair",
        hovermode="x unified"
    )

    fig.update_yaxes(
        tickformat=".0%"
    )

    return fig


def plot_fx_correlation(correlation_matrix: pd.DataFrame):
    """
    Heatmap de correlação dos retornos cambiais.
    """

    if correlation_matrix is None or correlation_matrix.empty:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Correlation")
        )
    )

    fig.update_layout(
        title="FX Returns Correlation Matrix"
    )

    return fig


def plot_fx_summary_bar(
    summary: pd.DataFrame,
    metric: str,
    title: str,
    y_axis_title: str,
    y_tickformat: str | None = None
):
    """
    Gráfico de barras para métricas FX.
    """

    if summary is None or summary.empty:
        return None

    if "Pair" not in summary.columns or metric not in summary.columns:
        return None

    chart_df = summary[
        ["Pair", metric]
    ].copy()

    chart_df[metric] = pd.to_numeric(
        chart_df[metric],
        errors="coerce"
    )

    chart_df = chart_df.dropna(subset=[metric])

    if chart_df.empty:
        return None

    chart_df = chart_df.sort_values(
        by=metric,
        ascending=False
    )

    fig = px.bar(
        chart_df,
        x="Pair",
        y=metric,
        title=title,
        text=metric,
        labels={
            "Pair": "FX Pair",
            metric: y_axis_title
        }
    )

    if y_tickformat:
        fig.update_yaxes(
            tickformat=y_tickformat
        )

    fig.update_layout(
        hovermode="x unified"
    )

    return fig



# ============================================================
# CRYPTO CHARTS
# ============================================================

def plot_crypto_prices(crypto_close_prices: pd.DataFrame):
    """
    Gráfico dos preços de fecho dos criptoativos.
    """

    if crypto_close_prices is None or crypto_close_prices.empty:
        return None

    fig = px.line(
        crypto_close_prices,
        x=crypto_close_prices.index,
        y=crypto_close_prices.columns,
        title="Crypto Close Prices",
        labels={
            "value": "Close Price",
            "Date": "Date",
            "variable": "Crypto Pair"
        }
    )

    fig.update_layout(
        legend_title_text="Crypto Pair",
        hovermode="x unified"
    )

    return fig


def plot_crypto_performance(performance: pd.DataFrame):
    """
    Gráfico de performance base 100 dos criptoativos.
    """

    if performance is None or performance.empty:
        return None

    fig = px.line(
        performance,
        x=performance.index,
        y=performance.columns,
        title="Crypto Performance Base 100",
        labels={
            "value": "Base 100",
            "Date": "Date",
            "variable": "Crypto Pair"
        }
    )

    fig.update_layout(
        legend_title_text="Crypto Pair",
        hovermode="x unified"
    )

    return fig


def plot_crypto_drawdowns(drawdowns: pd.DataFrame):
    """
    Gráfico de drawdowns dos criptoativos.
    """

    if drawdowns is None or drawdowns.empty:
        return None

    fig = px.line(
        drawdowns,
        x=drawdowns.index,
        y=drawdowns.columns,
        title="Crypto Drawdowns",
        labels={
            "value": "Drawdown",
            "Date": "Date",
            "variable": "Crypto Pair"
        }
    )

    fig.update_layout(
        legend_title_text="Crypto Pair",
        hovermode="x unified"
    )

    fig.update_yaxes(
        tickformat=".0%"
    )

    return fig


def plot_crypto_correlation(correlation_matrix: pd.DataFrame):
    """
    Heatmap de correlação dos retornos crypto.
    """

    if correlation_matrix is None or correlation_matrix.empty:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Correlation")
        )
    )

    fig.update_layout(
        title="Crypto Returns Correlation Matrix"
    )

    return fig


def plot_crypto_summary_bar(
    summary: pd.DataFrame,
    metric: str,
    title: str,
    y_axis_title: str,
    y_tickformat: str | None = None
):
    """
    Gráfico de barras para métricas Crypto.
    """

    if summary is None or summary.empty:
        return None

    if "Pair" not in summary.columns or metric not in summary.columns:
        return None

    chart_df = summary[
        ["Pair", metric]
    ].copy()

    chart_df[metric] = pd.to_numeric(
        chart_df[metric],
        errors="coerce"
    )

    chart_df = chart_df.dropna(subset=[metric])

    if chart_df.empty:
        return None

    chart_df = chart_df.sort_values(
        by=metric,
        ascending=False
    )

    fig = px.bar(
        chart_df,
        x="Pair",
        y=metric,
        title=title,
        text=metric,
        labels={
            "Pair": "Crypto Pair",
            metric: y_axis_title
        }
    )

    if y_tickformat:
        fig.update_yaxes(
            tickformat=y_tickformat
        )

    fig.update_layout(
        hovermode="x unified"
    )

    return fig




# ============================================================
# MACROECONOMIC CHARTS
# ============================================================

def plot_macro_values(macro_values: pd.DataFrame):
    """
    Gráfico dos valores dos indicadores macroeconómicos.
    """

    if macro_values is None or macro_values.empty:
        return None

    fig = px.line(
        macro_values,
        x=macro_values.index,
        y=macro_values.columns,
        title="Macroeconomic Indicators",
        labels={
            "value": "Value",
            "Date": "Date",
            "variable": "Indicator"
        }
    )

    fig.update_layout(
        legend_title_text="Indicator",
        hovermode="x unified"
    )

    return fig


def plot_macro_yoy_change(macro_changes_long: pd.DataFrame):
    """
    Gráfico da variação YoY dos indicadores macroeconómicos.
    """

    if macro_changes_long is None or macro_changes_long.empty:
        return None

    if "Date" not in macro_changes_long.columns:
        return None

    if "Indicator" not in macro_changes_long.columns:
        return None

    if "YoY Change" not in macro_changes_long.columns:
        return None

    chart_df = macro_changes_long.dropna(
        subset=["YoY Change"]
    ).copy()

    if chart_df.empty:
        return None

    fig = px.line(
        chart_df,
        x="Date",
        y="YoY Change",
        color="Indicator",
        title="Macroeconomic Indicators - YoY Change",
        labels={
            "Date": "Date",
            "YoY Change": "YoY Change",
            "Indicator": "Indicator"
        }
    )

    fig.update_layout(
        hovermode="x unified"
    )

    return fig


def plot_macro_yoy_percent_change(macro_changes_long: pd.DataFrame):
    """
    Gráfico da variação percentual YoY dos indicadores macroeconómicos.
    """

    if macro_changes_long is None or macro_changes_long.empty:
        return None

    if "Date" not in macro_changes_long.columns:
        return None

    if "Indicator" not in macro_changes_long.columns:
        return None

    if "YoY % Change" not in macro_changes_long.columns:
        return None

    chart_df = macro_changes_long.dropna(
        subset=["YoY % Change"]
    ).copy()

    if chart_df.empty:
        return None

    fig = px.line(
        chart_df,
        x="Date",
        y="YoY % Change",
        color="Indicator",
        title="Macroeconomic Indicators - YoY % Change",
        labels={
            "Date": "Date",
            "YoY % Change": "YoY % Change",
            "Indicator": "Indicator"
        }
    )

    fig.update_layout(
        hovermode="x unified"
    )

    fig.update_yaxes(
        tickformat=".0%"
    )

    return fig


def plot_macro_latest_values(summary: pd.DataFrame):
    """
    Gráfico de barras com o valor mais recente de cada indicador macro.

    Nota:
    CPI é um índice, enquanto Fed Funds, Treasury Yield e Unemployment
    são taxas percentuais. Por isso, este gráfico é útil para leitura rápida,
    mas não deve ser interpretado como comparação direta entre indicadores.
    """

    if summary is None or summary.empty:
        return None

    if "Indicator" not in summary.columns or "Latest Value" not in summary.columns:
        return None

    chart_df = summary[
        ["Indicator", "Latest Value"]
    ].copy()

    chart_df["Latest Value"] = pd.to_numeric(
        chart_df["Latest Value"],
        errors="coerce"
    )

    chart_df = chart_df.dropna(subset=["Latest Value"])

    if chart_df.empty:
        return None

    chart_df["Formatted Value"] = chart_df["Latest Value"].apply(
        lambda value: f"{value:,.2f}"
    )

    fig = px.bar(
        chart_df,
        x="Indicator",
        y="Latest Value",
        title="Latest Macroeconomic Values",
        text="Formatted Value",
        labels={
            "Indicator": "Indicator",
            "Latest Value": "Latest Value"
        }
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        hovermode="x unified",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
        yaxis_title="Latest Value"
    )

    return fig

def plot_macro_summary_bar(
    summary: pd.DataFrame,
    metric: str,
    title: str,
    y_axis_title: str
):
    """
    Gráfico de barras para métricas macroeconómicas.

    Melhoria:
    - arredonda valores;
    - evita etiquetas com demasiadas casas decimais;
    - coloca os valores fora das barras para melhor leitura.
    """

    if summary is None or summary.empty:
        return None

    if "Indicator" not in summary.columns or metric not in summary.columns:
        return None

    chart_df = summary[
        ["Indicator", metric]
    ].copy()

    chart_df[metric] = pd.to_numeric(
        chart_df[metric],
        errors="coerce"
    )

    chart_df = chart_df.dropna(subset=[metric])

    if chart_df.empty:
        return None

    chart_df["Formatted Value"] = chart_df[metric].apply(
        lambda value: f"{value:,.2f}"
    )

    fig = px.bar(
        chart_df,
        x="Indicator",
        y=metric,
        title=title,
        text="Formatted Value",
        labels={
            "Indicator": "Indicator",
            metric: y_axis_title
        }
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        hovermode="x unified",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
        yaxis_title=y_axis_title
    )

    return fig