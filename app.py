from datetime import datetime, date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.config import (
    APP_NAME,
    APP_VERSION,
    BASE_DIR,
    CACHE_DIR,
    EXPORTS_DIR,
    API_KEY,
    BASE_URL,
    DEFAULT_OUTPUTSIZE,
    API_SLEEP_SECONDS
)

from utils.alpha_vantage_client import (
    get_multiple_stock_prices,
    get_multiple_company_overviews,
    get_multiple_commodities,
    get_multiple_fx_pairs,
    get_multiple_crypto_assets,
    get_multiple_macro_indicators
)

from utils.calculations import (
    calculate_returns,
    calculate_performance_base_100,
    calculate_drawdowns,
    calculate_risk_return_summary,
    calculate_correlation_matrix,
    calculate_technical_indicators,
    create_technical_summary,
    create_fundamental_ranking,
    calculate_commodity_summary,
    calculate_fx_summary,
    calculate_crypto_summary,
    calculate_macro_changes,
    calculate_macro_summary,
    format_summary_for_display,
    format_fundamental_table_for_display,
    format_commodity_summary_for_display,
    format_fx_summary_for_display,
    format_crypto_summary_for_display,
    format_macro_summary_for_display
)

from utils.charts import (
    plot_price_chart,
    plot_performance_base_100,
    plot_drawdowns,
    plot_returns_histogram,
    plot_risk_return_scatter,
    plot_correlation_heatmap,
    plot_technical_price_sma,
    plot_rsi,
    plot_macd,
    plot_fundamental_bar,
    plot_fundamental_grouped_bars,
    plot_commodity_values,
    plot_commodity_performance,
    plot_commodity_drawdowns,
    plot_commodity_correlation,
    plot_commodity_summary_bar,
    plot_fx_rates,
    plot_fx_performance,
    plot_fx_drawdowns,
    plot_fx_correlation,
    plot_fx_summary_bar,
    plot_crypto_prices,
    plot_crypto_performance,
    plot_crypto_drawdowns,
    plot_crypto_correlation,
    plot_crypto_summary_bar,
    plot_macro_values,
    plot_macro_yoy_change,
    plot_macro_yoy_percent_change,
    plot_macro_latest_values,
    plot_macro_summary_bar
)

from utils.excel_export import (
    export_alpha_vantage_report,
    generate_export_filename
)


# ============================================================
# STREAMLIT PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Alpha Vantage Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_api_key_status(api_key: str | None) -> dict:
    """
    Checks if the API key exists locally in the .env file.
    This does not validate the key with Alpha Vantage.
    """

    if api_key is None or str(api_key).strip() == "":
        return {
            "Status": "Missing",
            "Message": "API key não encontrada no ficheiro .env.",
            "Is Valid Locally": False
        }

    return {
        "Status": "Available",
        "Message": "API key encontrada no ficheiro .env.",
        "Is Valid Locally": True
    }


def get_folder_summary(folder_path) -> pd.DataFrame:
    """
    Creates a summary of files inside a folder.
    """

    files = sorted(folder_path.glob("*"))
    rows = []

    for file_path in files:
        if file_path.is_file():
            rows.append({
                "File Name": file_path.name,
                "File Type": file_path.suffix.replace(".", "").upper(),
                "Size KB": round(file_path.stat().st_size / 1024, 2),
                "Last Modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S")
            })

    if not rows:
        return pd.DataFrame({
            "File Name": ["No files found"],
            "File Type": ["-"],
            "Size KB": [0],
            "Last Modified": ["-"]
        })

    return pd.DataFrame(rows)


def parse_tickers(ticker_text: str) -> list[str]:
    """
    Parses comma-separated tickers from sidebar input.
    Removes empty values and duplicates.
    """

    tickers = [
        ticker.strip().upper()
        for ticker in ticker_text.split(",")
        if ticker.strip()
    ]

    unique_tickers = []

    for ticker in tickers:
        if ticker not in unique_tickers:
            unique_tickers.append(ticker)

    return unique_tickers


def make_streamlit_safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts DataFrames into a safer format for st.dataframe.

    This avoids Streamlit / Arrow serialization warnings when a DataFrame
    has object columns with mixed values such as Timestamps, pd.NA, None,
    strings and numbers.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    safe_df = df.copy()

    safe_df.columns = [
        str(column)
        for column in safe_df.columns
    ]

    def clean_cell(value):
        if isinstance(value, (pd.Timestamp, datetime, date)):
            return value.strftime("%Y-%m-%d")

        if value is None:
            return ""

        try:
            if pd.isna(value):
                return ""
        except (TypeError, ValueError):
            pass

        return value

    for column in safe_df.columns:
        if pd.api.types.is_datetime64_any_dtype(safe_df[column]):
            safe_df[column] = safe_df[column].dt.strftime("%Y-%m-%d")

        elif safe_df[column].dtype == "object":
            safe_df[column] = safe_df[column].apply(clean_cell)

    return safe_df


def render_metric_explanation_table() -> pd.DataFrame:
    """
    Creates a glossary table with the main financial concepts used in the app.
    """

    rows = [
        {
            "Concept": "Close Price",
            "Python Logic": "price series",
            "Financial Interpretation": "Preço de fecho usado como base para retornos."
        },
        {
            "Concept": "Daily Return",
            "Python Logic": "pct_change(fill_method=None)",
            "Financial Interpretation": "Variação percentual diária do preço."
        },
        {
            "Concept": "Performance Base 100",
            "Python Logic": "(1 + returns).cumprod() * 100",
            "Financial Interpretation": "Compara ativos diferentes numa base comum."
        },
        {
            "Concept": "Annualized Volatility",
            "Python Logic": "std * sqrt(252)",
            "Financial Interpretation": "Volatilidade diária convertida para escala anual."
        },
        {
            "Concept": "Drawdown",
            "Python Logic": "price / price.cummax() - 1",
            "Financial Interpretation": "Queda face ao máximo anterior."
        },
        {
            "Concept": "Max Drawdown",
            "Python Logic": "drawdown.min()",
            "Financial Interpretation": "Maior queda histórica observada."
        },
        {
            "Concept": "Correlation",
            "Python Logic": "returns.corr()",
            "Financial Interpretation": "Relação entre movimentos dos ativos."
        },
        {
            "Concept": "SMA",
            "Python Logic": "rolling(window).mean()",
            "Financial Interpretation": "Média móvel simples usada para analisar tendência."
        },
        {
            "Concept": "RSI",
            "Python Logic": "Wilder RSI calculation",
            "Financial Interpretation": "Indicador de momentum; acima de 70 pode indicar sobrecompra e abaixo de 30 sobrevenda."
        },
        {
            "Concept": "MACD",
            "Python Logic": "EMA fast - EMA slow",
            "Financial Interpretation": "Indicador de tendência e momentum."
        },
        {
            "Concept": "Market Cap",
            "Python Logic": "OVERVIEW endpoint",
            "Financial Interpretation": "Valor de mercado da empresa."
        },
        {
            "Concept": "P/E Ratio",
            "Python Logic": "PERatio",
            "Financial Interpretation": "Preço dividido pelo lucro por ação."
        },
        {
            "Concept": "ROE",
            "Python Logic": "ReturnOnEquityTTM",
            "Financial Interpretation": "Rentabilidade sobre capital próprio."
        },
        {
            "Concept": "Date Filter",
            "Python Logic": "df.loc[start_date:end_date]",
            "Financial Interpretation": "Permite analisar apenas uma janela temporal específica."
        },
        {
            "Concept": "YoY Change",
            "Python Logic": "df.diff(periods=12)",
            "Financial Interpretation": "Compara um indicador macro com o mesmo período do ano anterior."
        },
        {
            "Concept": "YoY % Change",
            "Python Logic": "df.pct_change(periods=12, fill_method=None)",
            "Financial Interpretation": "Mede a variação percentual anual, útil para indicadores como CPI."
        }
    ]

    return pd.DataFrame(rows)


def render_placeholder_section(
    title: str,
    description: str,
    next_features: list[str]
) -> None:
    """
    Renders placeholder sections for modules not yet implemented.
    """

    st.subheader(title)
    st.info(description)

    st.markdown("#### Funcionalidades previstas")

    for feature in next_features:
        st.markdown(f"- {feature}")


def format_number_label(value, decimals: int = 2) -> str:
    """
    Formats numbers for chart labels.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return f"{value:,.{decimals}f}"


def plot_single_macro_indicator(
    macro_values: pd.DataFrame,
    indicator: str,
    title: str,
    y_axis_title: str
):
    """
    Creates a line chart for one macro indicator.

    This avoids mixing CPI, which is an index, with interest rates and
    unemployment, which are percentage-style indicators.
    """

    if macro_values is None or macro_values.empty:
        return None

    if indicator not in macro_values.columns:
        return None

    chart_df = macro_values[[indicator]].dropna().reset_index()

    if chart_df.empty:
        return None

    fig = px.line(
        chart_df,
        x="Date",
        y=indicator,
        title=title,
        labels={
            "Date": "Date",
            indicator: y_axis_title
        }
    )

    fig.update_layout(
        hovermode="x unified",
        yaxis_title=y_axis_title
    )

    return fig


def plot_macro_bar_clean(
    summary: pd.DataFrame,
    metric: str,
    title: str,
    y_axis_title: str
):
    """
    Creates a clean macro bar chart with rounded labels.
    """

    if summary is None or summary.empty:
        return None

    if "Indicator" not in summary.columns or metric not in summary.columns:
        return None

    chart_df = summary[["Indicator", metric]].copy()

    chart_df[metric] = pd.to_numeric(
        chart_df[metric],
        errors="coerce"
    )

    chart_df = chart_df.dropna(subset=[metric])

    if chart_df.empty:
        return None

    chart_df["Formatted Value"] = chart_df[metric].apply(
        lambda value: format_number_label(value, decimals=2)
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


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 Alpha Vantage App")
st.sidebar.caption(APP_VERSION)

st.sidebar.markdown("---")

st.sidebar.header("1. API & Cache")

api_status = get_api_key_status(API_KEY)

if api_status["Is Valid Locally"]:
    st.sidebar.success("API key encontrada")
else:
    st.sidebar.error("API key em falta")

data_mode = st.sidebar.radio(
    "Data mode",
    options=[
        "Use local cache if available",
        "Force API refresh"
    ],
    index=0
)

force_refresh = data_mode == "Force API refresh"

outputsize = st.sidebar.selectbox(
    "Stock / FX output size",
    options=["compact", "full"],
    index=0,
    help=(
        "compact usa menos dados e é mais leve. "
        "full pode gastar mais tempo e devolver série histórica completa."
    )
)

commodity_interval = st.sidebar.selectbox(
    "Commodity interval",
    options=["monthly", "weekly", "daily"],
    index=0,
    help="monthly é mais leve e recomendado para evitar gastar demasiados requests."
)

st.sidebar.markdown("---")

st.sidebar.header("2. Stocks Setup")

stock_tickers_text = st.sidebar.text_input(
    "Stock tickers",
    value="MSFT,AAPL,NVDA",
    help="Escreve os tickers separados por vírgula."
)

stock_tickers = parse_tickers(stock_tickers_text)

st.sidebar.markdown("#### Stock Date Range")

stock_start_date = st.sidebar.date_input(
    "Stock start date",
    value=date(2020, 1, 1),
    help="Data inicial usada para filtrar a análise de ações."
)

stock_end_date = st.sidebar.date_input(
    "Stock end date",
    value=date.today(),
    help="Data final usada para filtrar a análise de ações."
)

if stock_start_date > stock_end_date:
    st.sidebar.error("A data inicial Stock não pode ser superior à data final Stock.")

st.sidebar.markdown("---")

st.sidebar.header("3. Market Date Ranges")

st.sidebar.markdown("#### Commodity Date Range")

commodity_start_date = st.sidebar.date_input(
    "Commodity start date",
    value=date(2020, 1, 1),
    help="Data inicial usada para filtrar a análise de commodities."
)

commodity_end_date = st.sidebar.date_input(
    "Commodity end date",
    value=date.today(),
    help="Data final usada para filtrar a análise de commodities."
)

if commodity_start_date > commodity_end_date:
    st.sidebar.error("A data inicial Commodity não pode ser superior à data final Commodity.")

st.sidebar.markdown("#### FX Date Range")

fx_start_date = st.sidebar.date_input(
    "FX start date",
    value=date(2020, 1, 1),
    help="Data inicial usada para filtrar a análise cambial."
)

fx_end_date = st.sidebar.date_input(
    "FX end date",
    value=date.today(),
    help="Data final usada para filtrar a análise cambial."
)

if fx_start_date > fx_end_date:
    st.sidebar.error("A data inicial FX não pode ser superior à data final FX.")

st.sidebar.markdown("#### Crypto Date Range")

crypto_start_date = st.sidebar.date_input(
    "Crypto start date",
    value=date(2020, 1, 1),
    help="Data inicial usada para filtrar a análise crypto."
)

crypto_end_date = st.sidebar.date_input(
    "Crypto end date",
    value=date.today(),
    help="Data final usada para filtrar a análise crypto."
)

if crypto_start_date > crypto_end_date:
    st.sidebar.error("A data inicial Crypto não pode ser superior à data final Crypto.")

st.sidebar.markdown("#### Macro Date Range")

macro_start_date = st.sidebar.date_input(
    "Macro start date",
    value=date(2020, 1, 1),
    help="Data inicial usada para filtrar a análise macroeconómica."
)

macro_end_date = st.sidebar.date_input(
    "Macro end date",
    value=date.today(),
    help="Data final usada para filtrar a análise macroeconómica."
)

if macro_start_date > macro_end_date:
    st.sidebar.error("A data inicial Macro não pode ser superior à data final Macro.")

st.sidebar.markdown("---")

st.sidebar.header("4. Data Actions")

load_stock_button = st.sidebar.button(
    "Load Stock Data",
    help="Carrega preços diários dos tickers selecionados.",
    key="load_stock_data_sidebar_button"
)

load_fundamentals_button = st.sidebar.button(
    "Load Fundamental Data",
    help="Carrega dados fundamentais dos tickers selecionados.",
    key="load_fundamental_data_sidebar_button"
)

load_commodities_button = st.sidebar.button(
    "Load Commodities Data",
    help="Carrega dados de commodities.",
    key="load_commodities_data_sidebar_button"
)

load_fx_button = st.sidebar.button(
    "Load FX Data",
    help="Carrega dados cambiais para EUR/USD, GBP/USD e USD/JPY.",
    key="load_fx_data_sidebar_button"
)

load_crypto_button = st.sidebar.button(
    "Load Crypto Data",
    help="Carrega dados crypto para BTC/USD e ETH/USD.",
    key="load_crypto_data_sidebar_button"
)

load_macro_button = st.sidebar.button(
    "Load Macro Data",
    help="Carrega dados macroeconómicos: Treasury Yield 10Y, Fed Funds, CPI e Unemployment.",
    key="load_macro_data_sidebar_button"
)

st.sidebar.caption(
    "Usa local cache para evitar gastar requests da Alpha Vantage."
)

st.sidebar.markdown("---")

st.sidebar.header("5. Display Settings")

currency_symbol = st.sidebar.selectbox(
    "Currency display",
    options=["$", "€", "£", "¥"],
    index=0,
    help="Apenas visual. Não faz conversão cambial."
)

show_raw_data = st.sidebar.checkbox(
    "Show raw data tables",
    value=True
)

st.sidebar.markdown("---")

st.sidebar.header("6. Project Folders")

st.sidebar.write(f"Base: `{BASE_DIR.name}`")
st.sidebar.write(f"Cache: `{CACHE_DIR.relative_to(BASE_DIR)}`")
st.sidebar.write(f"Exports: `{EXPORTS_DIR.relative_to(BASE_DIR)}`")


# ============================================================
# HEADER
# ============================================================

st.title("📊 Alpha Vantage Financial Dashboard")

st.caption(
    "App Streamlit baseada no projeto Alpha Vantage Learning Project. "
    "V7 Módulo Completo."
)

col_1, col_2, col_3, col_4 = st.columns(4)

with col_1:
    st.metric("App Version", "V7.0")

with col_2:
    st.metric("API Key", api_status["Status"])

with col_3:
    st.metric("Selected Stocks", len(stock_tickers))

with col_4:
    st.metric(
        "Cache Files",
        len([file for file in CACHE_DIR.glob("*") if file.is_file()])
    )


# ============================================================
# TABS
# ============================================================

tabs = st.tabs([
    "Overview",
    "Stocks",
    "Technical Indicators",
    "Fundamentals",
    "Commodities",
    "FX",
    "Crypto",
    "Macro",
    "Export",
    "Glossary"
])


# ============================================================
# TAB 1 - OVERVIEW
# ============================================================

with tabs[0]:
    st.header("Overview")

    st.markdown(
        """
        Esta app transforma o projeto `alpha_vantage_learning_project`
        numa ferramenta interativa.

        A V7 inclui:

        - stocks: preços, retornos, performance base 100, drawdowns, risco/retorno e correlação;
        - technical indicators: SMA, RSI e MACD;
        - fundamentals: Company Overview, valuation, profitability e ranking;
        - commodities: WTI, Brent e Natural Gas;
        - FX: EUR/USD, GBP/USD e USD/JPY;
        - crypto: BTC/USD e ETH/USD;
        - macro: Treasury Yield 10Y, Federal Funds Rate, CPI e Unemployment;
        - filtros de datas separados para ações, commodities, FX, crypto e macro.
        - Excel export com relatório completo.
        """
    )

    project_status = pd.DataFrame([
        {
            "Component": "App Version",
            "Status": APP_VERSION,
            "Interpretation": "Versão atual da aplicação."
        },
        {
            "Component": ".env file",
            "Status": "Available" if (BASE_DIR / ".env").exists() else "Missing",
            "Interpretation": "Ficheiro onde está a API key."
        },
        {
            "Component": "API Key",
            "Status": api_status["Status"],
            "Interpretation": api_status["Message"]
        },
        {
            "Component": "Cache folder",
            "Status": "Available" if CACHE_DIR.exists() else "Missing",
            "Interpretation": "Pasta onde são guardados dados recolhidos da API."
        },
        {
            "Component": "Exports folder",
            "Status": "Available" if EXPORTS_DIR.exists() else "Missing",
            "Interpretation": "Pasta onde serão guardados relatórios exportados."
        }
    ])

    st.subheader("Project Status")

    st.dataframe(
        make_streamlit_safe_dataframe(project_status),
        width="stretch",
        hide_index=True
    )

    roadmap = pd.DataFrame([
        {
            "Version": "V1",
            "Status": "Done",
            "Objective": "Layout, sidebar, tabs and API key validation."
        },
        {
            "Version": "V2",
            "Status": "Done",
            "Objective": "Stocks: prices, returns, performance base 100, risk and drawdowns."
        },
        {
            "Version": "V3",
            "Status": "Done",
            "Objective": "Technical indicators: SMA, RSI and MACD."
        },
        {
            "Version": "V4",
            "Status": "Done",
            "Objective": "Fundamentals: company overview, valuation, profitability and ranking."
        },
        {
            "Version": "V5.1",
            "Status": "Done",
            "Objective": "Commodities: WTI, Brent and Natural Gas with date filtering."
        },
        {
            "Version": "V5.2",
            "Status": "Done",
            "Objective": "FX: EUR/USD, GBP/USD and USD/JPY with date filtering."
        },
        {
            "Version": "V5.3",
            "Status": "Done",
            "Objective": "Crypto: BTC/USD and ETH/USD with date filtering."
        },
        {
            "Version": "V6",
            "Status": "Done",
            "Objective": "Macro indicators with date filtering and YoY changes."
        },
        {
            "Version": "V7",
            "Status": "Done",
            "Objective": "Excel export."
        }
    ])

    st.subheader("Roadmap")

    st.dataframe(
        make_streamlit_safe_dataframe(roadmap),
        width="stretch",
        hide_index=True
    )

    st.subheader("Cache Summary")

    st.dataframe(
        make_streamlit_safe_dataframe(get_folder_summary(CACHE_DIR)),
        width="stretch",
        hide_index=True
    )


# ============================================================
# TAB 2 - STOCKS
# ============================================================

with tabs[1]:
    st.header("Stocks")

    st.markdown(
        """
        Este módulo obtém preços diários de ações com a Alpha Vantage,
        guarda os dados em cache e calcula métricas financeiras básicas.
        """
    )

    if not api_status["Is Valid Locally"]:
        st.error("API key não encontrada. Verifica o ficheiro .env antes de usar este módulo.")

    elif not stock_tickers:
        st.warning("Escreve pelo menos um ticker na sidebar.")

    elif stock_start_date > stock_end_date:
        st.error("Corrige o intervalo de datas das ações na sidebar.")

    else:
        st.subheader("Selected Tickers")
        st.write(", ".join(stock_tickers))

        st.info(
            "Usa o botão **Load Stock Data** na sidebar para carregar os dados."
        )

        if load_stock_button:
            with st.spinner("A obter dados de ações com Alpha Vantage ou cache local..."):
                close_prices, prices_long, metadata, status = get_multiple_stock_prices(
                    tickers=stock_tickers,
                    base_url=BASE_URL,
                    api_key=API_KEY,
                    cache_dir=CACHE_DIR,
                    force_refresh=force_refresh,
                    outputsize=outputsize,
                    api_sleep_seconds=API_SLEEP_SECONDS
                )

            st.session_state["stock_close_prices"] = close_prices
            st.session_state["stock_prices_long"] = prices_long
            st.session_state["stock_metadata"] = metadata
            st.session_state["stock_status"] = status

        close_prices = st.session_state.get("stock_close_prices", pd.DataFrame())
        prices_long = st.session_state.get("stock_prices_long", pd.DataFrame())
        metadata = st.session_state.get("stock_metadata", pd.DataFrame())
        status = st.session_state.get("stock_status", pd.DataFrame())

        if not status.empty:
            st.subheader("Download / Cache Status")

            st.dataframe(
                make_streamlit_safe_dataframe(status),
                width="stretch",
                hide_index=True
            )

        if close_prices.empty:
            st.info("Ainda não há dados carregados. Usa **Load Stock Data** na sidebar.")

        else:
            stock_start_timestamp = pd.to_datetime(stock_start_date)
            stock_end_timestamp = pd.to_datetime(stock_end_date)

            close_prices_filtered = close_prices.loc[
                (close_prices.index >= stock_start_timestamp)
                &
                (close_prices.index <= stock_end_timestamp)
            ]

            prices_long_filtered = prices_long.copy()

            if not prices_long_filtered.empty and "Date" in prices_long_filtered.columns:
                prices_long_filtered["Date"] = pd.to_datetime(
                    prices_long_filtered["Date"],
                    errors="coerce"
                )

                prices_long_filtered = prices_long_filtered[
                    (prices_long_filtered["Date"] >= stock_start_timestamp)
                    &
                    (prices_long_filtered["Date"] <= stock_end_timestamp)
                ]

            st.subheader("Selected Date Range")

            st.write(
                f"Análise de ações entre **{stock_start_date}** e **{stock_end_date}**."
            )

            if close_prices_filtered.empty:
                st.warning(
                    "Não existem dados de ações para o intervalo de datas selecionado."
                )

            else:
                returns = calculate_returns(close_prices_filtered)
                performance = calculate_performance_base_100(close_prices_filtered)
                drawdowns = calculate_drawdowns(close_prices_filtered)
                summary = calculate_risk_return_summary(close_prices_filtered)
                correlation_matrix = calculate_correlation_matrix(returns)

                st.subheader("Risk & Return Summary")

                display_summary = format_summary_for_display(summary)

                st.dataframe(
                    make_streamlit_safe_dataframe(display_summary),
                    width="stretch",
                    hide_index=True
                )

                if not summary.empty:
                    st.subheader("Key Metrics")

                    best_total_return = summary.sort_values(
                        "Total Return",
                        ascending=False
                    ).iloc[0]

                    lowest_volatility = summary.sort_values(
                        "Annualized Volatility",
                        ascending=True
                    ).iloc[0]

                    best_sharpe = summary.sort_values(
                        "Sharpe Ratio Simplified",
                        ascending=False
                    ).iloc[0]

                    worst_drawdown = summary.sort_values(
                        "Max Drawdown",
                        ascending=True
                    ).iloc[0]

                    metric_1, metric_2, metric_3, metric_4 = st.columns(4)

                    with metric_1:
                        st.metric(
                            "Best Total Return",
                            best_total_return["Ticker"],
                            f"{best_total_return['Total Return']:.2%}"
                        )

                    with metric_2:
                        st.metric(
                            "Lowest Volatility",
                            lowest_volatility["Ticker"],
                            f"{lowest_volatility['Annualized Volatility']:.2%}"
                        )

                    with metric_3:
                        st.metric(
                            "Best Sharpe",
                            best_sharpe["Ticker"],
                            f"{best_sharpe['Sharpe Ratio Simplified']:.2f}"
                        )

                    with metric_4:
                        st.metric(
                            "Worst Drawdown",
                            worst_drawdown["Ticker"],
                            f"{worst_drawdown['Max Drawdown']:.2%}"
                        )

                st.subheader("Charts")

                fig_prices = plot_price_chart(close_prices_filtered)

                if fig_prices is not None:
                    st.plotly_chart(fig_prices, width="stretch")

                fig_performance = plot_performance_base_100(performance)

                if fig_performance is not None:
                    st.plotly_chart(fig_performance, width="stretch")

                fig_drawdowns = plot_drawdowns(drawdowns)

                if fig_drawdowns is not None:
                    st.plotly_chart(fig_drawdowns, width="stretch")

                fig_histogram = plot_returns_histogram(returns)

                if fig_histogram is not None:
                    st.plotly_chart(fig_histogram, width="stretch")

                fig_risk_return = plot_risk_return_scatter(summary)

                if fig_risk_return is not None:
                    st.plotly_chart(fig_risk_return, width="stretch")

                fig_correlation = plot_correlation_heatmap(correlation_matrix)

                if fig_correlation is not None:
                    st.plotly_chart(fig_correlation, width="stretch")

                if show_raw_data:
                    st.subheader("Raw Data")

                    raw_tabs = st.tabs([
                        "Close Prices",
                        "Returns",
                        "Performance Base 100",
                        "Drawdowns",
                        "Correlation",
                        "Long OHLCV",
                        "Metadata"
                    ])

                    with raw_tabs[0]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(close_prices_filtered.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_tabs[1]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(returns.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_tabs[2]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(performance.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_tabs[3]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(drawdowns.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_tabs[4]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(correlation_matrix.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_tabs[5]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(prices_long_filtered),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_tabs[6]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(metadata),
                            width="stretch",
                            hide_index=True
                        )

                st.subheader("Financial Interpretation")

                st.markdown(
                    """
                    - **Total Return** mostra a valorização acumulada no período selecionado.
                    - **Annualized Volatility** mede a instabilidade histórica dos retornos.
                    - **Sharpe Ratio Simplified** compara retorno anualizado com volatilidade anualizada.
                    - **Max Drawdown** mostra a maior queda face ao máximo anterior.
                    - **Correlation Matrix** mostra se os ativos tendem a mover-se juntos.
                    - O filtro de datas altera diretamente os resultados.
                    """
                )

                st.warning(
                    "Esta análise usa preços históricos e não representa previsão nem recomendação de investimento."
                )


# ============================================================
# TAB 3 - TECHNICAL INDICATORS
# ============================================================

with tabs[2]:
    st.header("Technical Indicators")

    close_prices = st.session_state.get("stock_close_prices", pd.DataFrame())

    if close_prices.empty:
        st.warning(
            "Ainda não há preços carregados. Vai à sidebar e clica em "
            "**Load Stock Data** primeiro."
        )

    elif stock_start_date > stock_end_date:
        st.error("Corrige o intervalo de datas das ações na sidebar.")

    else:
        stock_start_timestamp = pd.to_datetime(stock_start_date)
        stock_end_timestamp = pd.to_datetime(stock_end_date)

        close_prices_filtered_for_technical = close_prices.loc[
            (close_prices.index >= stock_start_timestamp)
            &
            (close_prices.index <= stock_end_timestamp)
        ]

        if close_prices_filtered_for_technical.empty:
            st.warning(
                "Não existem dados de ações para calcular indicadores técnicos no intervalo selecionado."
            )

        else:
            st.subheader("Selected Date Range")

            st.write(
                f"Indicadores técnicos calculados entre **{stock_start_date}** e **{stock_end_date}**."
            )

            available_tickers = list(close_prices_filtered_for_technical.columns)

            selected_technical_ticker = st.selectbox(
                "Select ticker for technical analysis",
                options=available_tickers,
                index=0
            )

            st.subheader("Technical Parameters")

            param_col_1, param_col_2, param_col_3 = st.columns(3)

            with param_col_1:
                sma_short_window = st.number_input(
                    "Short SMA window",
                    min_value=5,
                    max_value=100,
                    value=20,
                    step=1
                )

            with param_col_2:
                sma_long_window = st.number_input(
                    "Long SMA window",
                    min_value=10,
                    max_value=250,
                    value=50,
                    step=1
                )

            with param_col_3:
                rsi_period = st.number_input(
                    "RSI period",
                    min_value=5,
                    max_value=50,
                    value=14,
                    step=1
                )

            macd_col_1, macd_col_2, macd_col_3 = st.columns(3)

            with macd_col_1:
                macd_fast = st.number_input(
                    "MACD fast EMA",
                    min_value=5,
                    max_value=30,
                    value=12,
                    step=1
                )

            with macd_col_2:
                macd_slow = st.number_input(
                    "MACD slow EMA",
                    min_value=10,
                    max_value=60,
                    value=26,
                    step=1
                )

            with macd_col_3:
                macd_signal = st.number_input(
                    "MACD signal EMA",
                    min_value=5,
                    max_value=30,
                    value=9,
                    step=1
                )

            if sma_short_window >= sma_long_window:
                st.warning(
                    "A short SMA deve ser inferior à long SMA para uma leitura mais clara."
                )

            close_series = close_prices_filtered_for_technical[
                selected_technical_ticker
            ].dropna()

            if close_series.empty:
                st.warning(
                    f"Não existem preços suficientes para {selected_technical_ticker}."
                )

            else:
                technical_df = calculate_technical_indicators(
                    close_prices=close_series,
                    sma_short_window=sma_short_window,
                    sma_long_window=sma_long_window,
                    rsi_period=rsi_period,
                    macd_fast=macd_fast,
                    macd_slow=macd_slow,
                    macd_signal=macd_signal
                )

                technical_summary = create_technical_summary(
                    ticker=selected_technical_ticker,
                    technical_df=technical_df,
                    sma_short_window=sma_short_window,
                    sma_long_window=sma_long_window,
                    rsi_period=rsi_period
                )

                st.subheader("Technical Summary")

                if technical_summary.empty:
                    st.info(
                        "Ainda não há dados suficientes para calcular todos os indicadores técnicos."
                    )

                else:
                    display_technical_summary = technical_summary.copy()

                    numeric_display_columns = [
                        "Close",
                        f"SMA_{sma_short_window}",
                        f"SMA_{sma_long_window}",
                        f"RSI_{rsi_period}",
                        "MACD",
                        "MACD Signal",
                        "MACD Histogram"
                    ]

                    for column in numeric_display_columns:
                        if column in display_technical_summary.columns:
                            display_technical_summary[column] = display_technical_summary[
                                column
                            ].apply(
                                lambda value: f"{value:,.2f}" if pd.notna(value) else ""
                            )

                    st.dataframe(
                        make_streamlit_safe_dataframe(display_technical_summary),
                        width="stretch",
                        hide_index=True
                    )

                    latest_signal = technical_summary.iloc[0]["Trend Summary"]
                    rsi_signal = technical_summary.iloc[0]["RSI Signal"]
                    macd_signal_label = technical_summary.iloc[0]["MACD Signal Label"]

                    metric_1, metric_2, metric_3 = st.columns(3)

                    with metric_1:
                        st.metric("Trend Summary", latest_signal)

                    with metric_2:
                        st.metric("RSI Signal", rsi_signal)

                    with metric_3:
                        st.metric("MACD Signal", macd_signal_label)

                st.subheader("Technical Charts")

                fig_technical_price = plot_technical_price_sma(
                    technical_df=technical_df,
                    ticker=selected_technical_ticker,
                    sma_short_window=sma_short_window,
                    sma_long_window=sma_long_window
                )

                if fig_technical_price is not None:
                    st.plotly_chart(fig_technical_price, width="stretch")

                fig_rsi = plot_rsi(
                    technical_df=technical_df,
                    ticker=selected_technical_ticker,
                    rsi_period=rsi_period
                )

                if fig_rsi is not None:
                    st.plotly_chart(fig_rsi, width="stretch")

                fig_macd = plot_macd(
                    technical_df=technical_df,
                    ticker=selected_technical_ticker
                )

                if fig_macd is not None:
                    st.plotly_chart(fig_macd, width="stretch")

                if show_raw_data:
                    st.subheader("Technical Raw Data")

                    st.dataframe(
                        make_streamlit_safe_dataframe(technical_df.reset_index()),
                        width="stretch",
                        hide_index=True
                    )

                st.subheader("Financial Interpretation")

                st.markdown(
                    """
                    - **SMA 20** mostra a tendência de curto prazo.
                    - **SMA 50** mostra a tendência de médio prazo.
                    - **RSI acima de 70** pode indicar zona de sobrecompra.
                    - **RSI abaixo de 30** pode indicar zona de sobrevenda.
                    - **MACD acima do MACD Signal** sugere momentum positivo.
                    - **MACD abaixo do MACD Signal** sugere momentum negativo.
                    - Os indicadores são calculados apenas no intervalo de datas selecionado para as ações.
                    """
                )

                st.warning(
                    "Indicadores técnicos são sinais históricos e não garantem movimentos futuros."
                )

# ============================================================
# TAB 4 - FUNDAMENTALS
# ============================================================

with tabs[3]:
    st.header("Fundamentals")

    st.markdown(
        """
        Este módulo usa o endpoint **OVERVIEW** da Alpha Vantage para analisar
        dados fundamentais e métricas de valuation.
        """
    )

    if not api_status["Is Valid Locally"]:
        st.error("API key não encontrada. Verifica o ficheiro .env antes de usar este módulo.")

    elif not stock_tickers:
        st.warning("Escreve pelo menos um ticker na sidebar.")

    else:
        st.subheader("Selected Companies")
        st.write(", ".join(stock_tickers))

        st.info(
            "Usa o botão **Load Fundamental Data** na sidebar para carregar os dados fundamentais."
        )

        if load_fundamentals_button:
            with st.spinner("A obter Company Overview com Alpha Vantage ou cache local..."):
                fundamentals_overview, fundamentals_metadata, fundamentals_status = (
                    get_multiple_company_overviews(
                        tickers=stock_tickers,
                        base_url=BASE_URL,
                        api_key=API_KEY,
                        cache_dir=CACHE_DIR,
                        force_refresh=force_refresh,
                        api_sleep_seconds=API_SLEEP_SECONDS
                    )
                )

            st.session_state["fundamentals_overview"] = fundamentals_overview
            st.session_state["fundamentals_metadata"] = fundamentals_metadata
            st.session_state["fundamentals_status"] = fundamentals_status

        fundamentals_overview = st.session_state.get(
            "fundamentals_overview",
            pd.DataFrame()
        )

        fundamentals_metadata = st.session_state.get(
            "fundamentals_metadata",
            pd.DataFrame()
        )

        fundamentals_status = st.session_state.get(
            "fundamentals_status",
            pd.DataFrame()
        )

        if not fundamentals_status.empty:
            st.subheader("Download / Cache Status")

            st.dataframe(
                make_streamlit_safe_dataframe(fundamentals_status),
                width="stretch",
                hide_index=True
            )

        if fundamentals_overview.empty:
            st.info("Ainda não há dados fundamentais carregados. Usa **Load Fundamental Data** na sidebar.")

        else:
            fundamental_ranking = create_fundamental_ranking(
                fundamentals_overview
            )

            st.subheader("Company Overview")

            overview_columns = [
                "Symbol",
                "Name",
                "AssetType",
                "Exchange",
                "Currency",
                "Country",
                "Sector",
                "Industry",
                "FiscalYearEnd",
                "LatestQuarter",
                "MarketCapitalization",
                "Description"
            ]

            available_overview_columns = [
                column
                for column in overview_columns
                if column in fundamentals_overview.columns
            ]

            overview_display = fundamentals_overview[
                available_overview_columns
            ]

            st.dataframe(
                make_streamlit_safe_dataframe(
                    format_fundamental_table_for_display(overview_display)
                ),
                width="stretch",
                hide_index=True
            )

            st.subheader("Key Fundamental Metrics")

            metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)

            if "MarketCapitalization" in fundamentals_overview.columns:
                market_cap_df = fundamentals_overview.dropna(
                    subset=["MarketCapitalization"]
                )

                if not market_cap_df.empty:
                    largest_market_cap = market_cap_df.sort_values(
                        "MarketCapitalization",
                        ascending=False
                    ).iloc[0]

                    with metric_col_1:
                        st.metric(
                            "Largest Market Cap",
                            largest_market_cap["Symbol"],
                            f"${largest_market_cap['MarketCapitalization']:,.0f}"
                        )

            if "ProfitMargin" in fundamentals_overview.columns:
                profit_margin_df = fundamentals_overview.dropna(
                    subset=["ProfitMargin"]
                )

                if not profit_margin_df.empty:
                    highest_profit_margin = profit_margin_df.sort_values(
                        "ProfitMargin",
                        ascending=False
                    ).iloc[0]

                    with metric_col_2:
                        st.metric(
                            "Highest Profit Margin",
                            highest_profit_margin["Symbol"],
                            f"{highest_profit_margin['ProfitMargin']:.2%}"
                        )

            if "ReturnOnEquityTTM" in fundamentals_overview.columns:
                roe_df = fundamentals_overview.dropna(
                    subset=["ReturnOnEquityTTM"]
                )

                if not roe_df.empty:
                    highest_roe = roe_df.sort_values(
                        "ReturnOnEquityTTM",
                        ascending=False
                    ).iloc[0]

                    with metric_col_3:
                        st.metric(
                            "Highest ROE",
                            highest_roe["Symbol"],
                            f"{highest_roe['ReturnOnEquityTTM']:.2%}"
                        )

            if not fundamental_ranking.empty and "Fundamental Score" in fundamental_ranking.columns:
                ranking_df = fundamental_ranking.dropna(
                    subset=["Fundamental Score"]
                )

                if not ranking_df.empty:
                    best_score = ranking_df.sort_values(
                        "Fundamental Score",
                        ascending=False
                    ).iloc[0]

                    with metric_col_4:
                        st.metric(
                            "Best Fundamental Score",
                            best_score["Symbol"],
                            f"{best_score['Fundamental Score']:.2f}"
                        )

            st.subheader("Fundamental Ranking")

            if fundamental_ranking.empty:
                st.info("Não foi possível calcular ranking fundamental com os dados disponíveis.")

            else:
                st.dataframe(
                    make_streamlit_safe_dataframe(
                        format_fundamental_table_for_display(fundamental_ranking)
                    ),
                    width="stretch",
                    hide_index=True
                )

            st.subheader("Valuation Metrics")

            valuation_columns = [
                "Symbol",
                "Name",
                "MarketCapitalization",
                "PERatio",
                "PEGRatio",
                "TrailingPE",
                "ForwardPE",
                "PriceToSalesRatioTTM",
                "PriceToBookRatio",
                "EVToRevenue",
                "EVToEBITDA",
                "EPS",
                "BookValue",
                "AnalystTargetPrice"
            ]

            available_valuation_columns = [
                column
                for column in valuation_columns
                if column in fundamentals_overview.columns
            ]

            valuation_table = fundamentals_overview[
                available_valuation_columns
            ]

            st.dataframe(
                make_streamlit_safe_dataframe(
                    format_fundamental_table_for_display(valuation_table)
                ),
                width="stretch",
                hide_index=True
            )

            st.subheader("Profitability Metrics")

            profitability_columns = [
                "Symbol",
                "Name",
                "RevenueTTM",
                "GrossProfitTTM",
                "EBITDA",
                "ProfitMargin",
                "OperatingMarginTTM",
                "ReturnOnAssetsTTM",
                "ReturnOnEquityTTM",
                "QuarterlyRevenueGrowthYOY",
                "QuarterlyEarningsGrowthYOY"
            ]

            available_profitability_columns = [
                column
                for column in profitability_columns
                if column in fundamentals_overview.columns
            ]

            profitability_table = fundamentals_overview[
                available_profitability_columns
            ]

            st.dataframe(
                make_streamlit_safe_dataframe(
                    format_fundamental_table_for_display(profitability_table)
                ),
                width="stretch",
                hide_index=True
            )

            st.subheader("Risk and Income Metrics")

            risk_income_columns = [
                "Symbol",
                "Name",
                "Beta",
                "DividendPerShare",
                "DividendYield",
                "52WeekHigh",
                "52WeekLow",
                "50DayMovingAverage",
                "200DayMovingAverage",
                "SharesOutstanding"
            ]

            available_risk_income_columns = [
                column
                for column in risk_income_columns
                if column in fundamentals_overview.columns
            ]

            risk_income_table = fundamentals_overview[
                available_risk_income_columns
            ]

            st.dataframe(
                make_streamlit_safe_dataframe(
                    format_fundamental_table_for_display(risk_income_table)
                ),
                width="stretch",
                hide_index=True
            )

            st.subheader("Fundamental Charts")

            fig_market_cap = plot_fundamental_bar(
                df=fundamentals_overview,
                metric="MarketCapitalization",
                title="Market Capitalization",
                y_axis_title="Market Cap"
            )

            if fig_market_cap is not None:
                st.plotly_chart(fig_market_cap, width="stretch")

            fig_pe = plot_fundamental_bar(
                df=fundamentals_overview,
                metric="PERatio",
                title="P/E Ratio",
                y_axis_title="P/E Ratio"
            )

            if fig_pe is not None:
                st.plotly_chart(fig_pe, width="stretch")

            fig_profitability = plot_fundamental_grouped_bars(
                df=fundamentals_overview,
                metrics=[
                    "ProfitMargin",
                    "OperatingMarginTTM",
                    "ReturnOnAssetsTTM",
                    "ReturnOnEquityTTM"
                ],
                title="Profitability Metrics",
                y_axis_title="Percentage",
                y_tickformat=".0%"
            )

            if fig_profitability is not None:
                st.plotly_chart(fig_profitability, width="stretch")

            if not fundamental_ranking.empty:
                fig_score = plot_fundamental_bar(
                    df=fundamental_ranking,
                    metric="Fundamental Score",
                    title="Fundamental Score Ranking",
                    y_axis_title="Score"
                )

                if fig_score is not None:
                    st.plotly_chart(fig_score, width="stretch")

            if show_raw_data:
                st.subheader("Raw Fundamental Data")

                raw_fundamental_tabs = st.tabs([
                    "Overview Raw",
                    "Metadata",
                    "Ranking Raw"
                ])

                with raw_fundamental_tabs[0]:
                    st.dataframe(
                        make_streamlit_safe_dataframe(fundamentals_overview),
                        width="stretch",
                        hide_index=True
                    )

                with raw_fundamental_tabs[1]:
                    st.dataframe(
                        make_streamlit_safe_dataframe(fundamentals_metadata),
                        width="stretch",
                        hide_index=True
                    )

                with raw_fundamental_tabs[2]:
                    st.dataframe(
                        make_streamlit_safe_dataframe(fundamental_ranking),
                        width="stretch",
                        hide_index=True
                    )

            st.subheader("Financial Interpretation")

            st.markdown(
                """
                - **Market Cap** mede o valor de mercado da empresa.
                - **P/E Ratio** compara preço com lucro por ação.
                - **Price/Sales** compara valor de mercado com receitas.
                - **Price/Book** compara preço com valor contabilístico.
                - **Profit Margin** mostra a percentagem das receitas que fica como lucro.
                - **ROA** mede rentabilidade sobre ativos.
                - **ROE** mede rentabilidade sobre capital próprio.
                - **Beta** mede sensibilidade histórica ao mercado.
                - **Fundamental Score** é um ranking educacional simples, não uma recomendação.
                """
            )

            st.warning(
                "Dados fundamentais devem ser analisados com contexto setorial, qualidade dos dados, ciclo económico e análise qualitativa. Esta app não representa recomendação de investimento."
            )


# ============================================================
# TAB 5 - COMMODITIES
# ============================================================

with tabs[4]:
    st.header("Commodities")

    st.markdown(
        """
        Este módulo analisa commodities através da Alpha Vantage.

        Commodities incluídas:

        - **WTI Crude Oil**
        - **Brent Crude Oil**
        - **Natural Gas**

        A análise calcula retornos, performance base 100, drawdowns,
        correlação e métricas de risco/retorno.
        """
    )

    commodities_config = [
        {
            "function": "WTI",
            "name": "WTI Crude Oil"
        },
        {
            "function": "BRENT",
            "name": "Brent Crude Oil"
        },
        {
            "function": "NATURAL_GAS",
            "name": "Natural Gas"
        }
    ]

    selected_commodities_display = pd.DataFrame(commodities_config)

    st.subheader("Selected Commodities")

    st.dataframe(
        make_streamlit_safe_dataframe(selected_commodities_display),
        width="stretch",
        hide_index=True
    )

    st.info(
        "Usa o botão **Load Commodities Data** na sidebar para carregar os dados."
    )

    if not api_status["Is Valid Locally"]:
        st.error("API key não encontrada. Verifica o ficheiro .env antes de usar este módulo.")

    elif commodity_start_date > commodity_end_date:
        st.error("Corrige o intervalo de datas na sidebar antes de analisar commodities.")

    else:
        if load_commodities_button:
            with st.spinner("A obter dados de commodities com Alpha Vantage ou cache local..."):
                commodity_values, commodity_long, commodity_metadata, commodity_status = (
                    get_multiple_commodities(
                        commodities=commodities_config,
                        base_url=BASE_URL,
                        api_key=API_KEY,
                        cache_dir=CACHE_DIR,
                        force_refresh=force_refresh,
                        interval=commodity_interval,
                        api_sleep_seconds=API_SLEEP_SECONDS
                    )
                )

            st.session_state["commodity_values"] = commodity_values
            st.session_state["commodity_long"] = commodity_long
            st.session_state["commodity_metadata"] = commodity_metadata
            st.session_state["commodity_status"] = commodity_status

        commodity_values = st.session_state.get(
            "commodity_values",
            pd.DataFrame()
        )

        commodity_long = st.session_state.get(
            "commodity_long",
            pd.DataFrame()
        )

        commodity_metadata = st.session_state.get(
            "commodity_metadata",
            pd.DataFrame()
        )

        commodity_status = st.session_state.get(
            "commodity_status",
            pd.DataFrame()
        )

        if not commodity_status.empty:
            st.subheader("Download / Cache Status")

            st.dataframe(
                make_streamlit_safe_dataframe(commodity_status),
                width="stretch",
                hide_index=True
            )

        if commodity_values.empty:
            st.info("Ainda não há dados de commodities carregados. Usa **Load Commodities Data** na sidebar.")

        else:
            commodity_start_timestamp = pd.to_datetime(commodity_start_date)
            commodity_end_timestamp = pd.to_datetime(commodity_end_date)

            commodity_values_filtered = commodity_values.loc[
                (commodity_values.index >= commodity_start_timestamp)
                &
                (commodity_values.index <= commodity_end_timestamp)
            ]

            commodity_long_filtered = commodity_long.copy()

            if not commodity_long_filtered.empty and "Date" in commodity_long_filtered.columns:
                commodity_long_filtered["Date"] = pd.to_datetime(
                    commodity_long_filtered["Date"],
                    errors="coerce"
                )

                commodity_long_filtered = commodity_long_filtered[
                    (commodity_long_filtered["Date"] >= commodity_start_timestamp)
                    &
                    (commodity_long_filtered["Date"] <= commodity_end_timestamp)
                ]

            st.subheader("Selected Date Range")

            st.write(
                f"Análise de commodities entre **{commodity_start_date}** e **{commodity_end_date}**."
            )

            if commodity_values_filtered.empty:
                st.warning(
                    "Não existem dados de commodities para o intervalo de datas selecionado."
                )

            else:
                commodity_returns = calculate_returns(commodity_values_filtered)
                commodity_performance = calculate_performance_base_100(commodity_values_filtered)
                commodity_drawdowns = calculate_drawdowns(commodity_values_filtered)

                commodity_summary = calculate_commodity_summary(
                    commodity_values_filtered,
                    annualization_factor=12
                )

                commodity_correlation = calculate_correlation_matrix(
                    commodity_returns
                )

                st.subheader("Commodity Summary")

                st.dataframe(
                    make_streamlit_safe_dataframe(
                        format_commodity_summary_for_display(commodity_summary)
                    ),
                    width="stretch",
                    hide_index=True
                )

                if not commodity_summary.empty:
                    st.subheader("Key Commodity Metrics")

                    best_total_return = commodity_summary.sort_values(
                        "Total Return",
                        ascending=False
                    ).iloc[0]

                    lowest_volatility = commodity_summary.sort_values(
                        "Annualized Volatility",
                        ascending=True
                    ).iloc[0]

                    best_sharpe = commodity_summary.sort_values(
                        "Sharpe Ratio Simplified",
                        ascending=False
                    ).iloc[0]

                    worst_drawdown = commodity_summary.sort_values(
                        "Max Drawdown",
                        ascending=True
                    ).iloc[0]

                    commodity_metric_1, commodity_metric_2, commodity_metric_3, commodity_metric_4 = st.columns(4)

                    with commodity_metric_1:
                        st.metric(
                            "Best Total Return",
                            best_total_return["Commodity"],
                            f"{best_total_return['Total Return']:.2%}"
                        )

                    with commodity_metric_2:
                        st.metric(
                            "Lowest Volatility",
                            lowest_volatility["Commodity"],
                            f"{lowest_volatility['Annualized Volatility']:.2%}"
                        )

                    with commodity_metric_3:
                        st.metric(
                            "Best Sharpe",
                            best_sharpe["Commodity"],
                            f"{best_sharpe['Sharpe Ratio Simplified']:.2f}"
                        )

                    with commodity_metric_4:
                        st.metric(
                            "Worst Drawdown",
                            worst_drawdown["Commodity"],
                            f"{worst_drawdown['Max Drawdown']:.2%}"
                        )

                st.subheader("Commodity Charts")

                fig_commodity_values = plot_commodity_values(
                    commodity_values_filtered
                )

                if fig_commodity_values is not None:
                    st.plotly_chart(
                        fig_commodity_values,
                        width="stretch"
                    )

                fig_commodity_performance = plot_commodity_performance(
                    commodity_performance
                )

                if fig_commodity_performance is not None:
                    st.plotly_chart(
                        fig_commodity_performance,
                        width="stretch"
                    )

                fig_commodity_drawdowns = plot_commodity_drawdowns(
                    commodity_drawdowns
                )

                if fig_commodity_drawdowns is not None:
                    st.plotly_chart(
                        fig_commodity_drawdowns,
                        width="stretch"
                    )

                fig_commodity_correlation = plot_commodity_correlation(
                    commodity_correlation
                )

                if fig_commodity_correlation is not None:
                    st.plotly_chart(
                        fig_commodity_correlation,
                        width="stretch"
                    )

                fig_commodity_total_return = plot_commodity_summary_bar(
                    summary=commodity_summary,
                    metric="Total Return",
                    title="Commodities Total Return Ranking",
                    y_axis_title="Total Return",
                    y_tickformat=".0%"
                )

                if fig_commodity_total_return is not None:
                    st.plotly_chart(
                        fig_commodity_total_return,
                        width="stretch"
                    )

                fig_commodity_volatility = plot_commodity_summary_bar(
                    summary=commodity_summary,
                    metric="Annualized Volatility",
                    title="Commodities Annualized Volatility Ranking",
                    y_axis_title="Annualized Volatility",
                    y_tickformat=".0%"
                )

                if fig_commodity_volatility is not None:
                    st.plotly_chart(
                        fig_commodity_volatility,
                        width="stretch"
                    )

                if show_raw_data:
                    st.subheader("Raw Commodities Data")

                    raw_commodity_tabs = st.tabs([
                        "Values",
                        "Returns",
                        "Performance Base 100",
                        "Drawdowns",
                        "Correlation",
                        "Long Data",
                        "Metadata"
                    ])

                    with raw_commodity_tabs[0]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(commodity_values_filtered.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_commodity_tabs[1]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(commodity_returns.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_commodity_tabs[2]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(commodity_performance.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_commodity_tabs[3]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(commodity_drawdowns.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_commodity_tabs[4]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(commodity_correlation.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_commodity_tabs[5]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(commodity_long_filtered),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_commodity_tabs[6]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(commodity_metadata),
                            width="stretch",
                            hide_index=True
                        )

                st.subheader("Financial Interpretation")

                st.markdown(
                    """
                    - **WTI** e **Brent** representam referências importantes para o petróleo.
                    - **Natural Gas** tende a ter dinâmica própria, ligada a procura energética, clima, inventários e sazonalidade.
                    - **Total Return** mostra a variação acumulada no período selecionado.
                    - **Annualized Volatility** mostra a instabilidade histórica anualizada.
                    - **Max Drawdown** mostra a maior queda face ao máximo anterior.
                    - **Correlation** mostra se as commodities tendem a mover-se em conjunto.
                    - O intervalo de datas escolhido altera diretamente os resultados.
                    """
                )

                st.warning(
                    "Commodities são ativos muito sensíveis a choques geopolíticos, oferta, procura, inventários, taxas de juro e câmbio. Esta análise é histórica e não representa previsão nem recomendação de investimento."
                )


# ============================================================
# TAB 6 - FX
# ============================================================

with tabs[5]:
    st.header("FX")

    st.markdown(
        """
        Este módulo analisa pares cambiais através da Alpha Vantage.

        Pares incluídos:

        - **EUR/USD**
        - **GBP/USD**
        - **USD/JPY**

        A análise calcula taxas de câmbio, retornos, performance base 100,
        drawdowns, correlação e métricas de risco/retorno.
        """
    )

    fx_pairs_config = [
        {
            "from_symbol": "EUR",
            "to_symbol": "USD",
            "pair_name": "EUR/USD"
        },
        {
            "from_symbol": "GBP",
            "to_symbol": "USD",
            "pair_name": "GBP/USD"
        },
        {
            "from_symbol": "USD",
            "to_symbol": "JPY",
            "pair_name": "USD/JPY"
        }
    ]

    selected_fx_display = pd.DataFrame(fx_pairs_config)

    st.subheader("Selected FX Pairs")

    st.dataframe(
        make_streamlit_safe_dataframe(selected_fx_display),
        width="stretch",
        hide_index=True
    )

    st.info(
        "Usa o botão **Load FX Data** na sidebar para carregar os dados cambiais."
    )

    if not api_status["Is Valid Locally"]:
        st.error("API key não encontrada. Verifica o ficheiro .env antes de usar este módulo.")

    elif fx_start_date > fx_end_date:
        st.error("Corrige o intervalo de datas FX na sidebar antes de analisar pares cambiais.")

    else:
        if load_fx_button:
            with st.spinner("A obter dados FX com Alpha Vantage ou cache local..."):
                fx_close_prices, fx_long, fx_metadata, fx_status = (
                    get_multiple_fx_pairs(
                        fx_pairs=fx_pairs_config,
                        base_url=BASE_URL,
                        api_key=API_KEY,
                        cache_dir=CACHE_DIR,
                        force_refresh=force_refresh,
                        outputsize=outputsize,
                        api_sleep_seconds=API_SLEEP_SECONDS
                    )
                )

            st.session_state["fx_close_prices"] = fx_close_prices
            st.session_state["fx_long"] = fx_long
            st.session_state["fx_metadata"] = fx_metadata
            st.session_state["fx_status"] = fx_status

        fx_close_prices = st.session_state.get(
            "fx_close_prices",
            pd.DataFrame()
        )

        fx_long = st.session_state.get(
            "fx_long",
            pd.DataFrame()
        )

        fx_metadata = st.session_state.get(
            "fx_metadata",
            pd.DataFrame()
        )

        fx_status = st.session_state.get(
            "fx_status",
            pd.DataFrame()
        )

        if not fx_status.empty:
            st.subheader("Download / Cache Status")

            st.dataframe(
                make_streamlit_safe_dataframe(fx_status),
                width="stretch",
                hide_index=True
            )

        if fx_close_prices.empty:
            st.info("Ainda não há dados FX carregados. Usa **Load FX Data** na sidebar.")

        else:
            fx_start_timestamp = pd.to_datetime(fx_start_date)
            fx_end_timestamp = pd.to_datetime(fx_end_date)

            fx_close_prices_filtered = fx_close_prices.loc[
                (fx_close_prices.index >= fx_start_timestamp)
                &
                (fx_close_prices.index <= fx_end_timestamp)
            ]

            fx_long_filtered = fx_long.copy()

            if not fx_long_filtered.empty and "Date" in fx_long_filtered.columns:
                fx_long_filtered["Date"] = pd.to_datetime(
                    fx_long_filtered["Date"],
                    errors="coerce"
                )

                fx_long_filtered = fx_long_filtered[
                    (fx_long_filtered["Date"] >= fx_start_timestamp)
                    &
                    (fx_long_filtered["Date"] <= fx_end_timestamp)
                ]

            st.subheader("Selected Date Range")

            st.write(
                f"Análise FX entre **{fx_start_date}** e **{fx_end_date}**."
            )

            if fx_close_prices_filtered.empty:
                st.warning(
                    "Não existem dados FX para o intervalo de datas selecionado."
                )

            else:
                fx_returns = calculate_returns(fx_close_prices_filtered)
                fx_performance = calculate_performance_base_100(fx_close_prices_filtered)
                fx_drawdowns = calculate_drawdowns(fx_close_prices_filtered)

                fx_summary = calculate_fx_summary(
                    fx_close_prices_filtered,
                    annualization_factor=252
                )

                fx_correlation = calculate_correlation_matrix(
                    fx_returns
                )

                st.subheader("FX Summary")

                st.dataframe(
                    make_streamlit_safe_dataframe(
                        format_fx_summary_for_display(fx_summary)
                    ),
                    width="stretch",
                    hide_index=True
                )

                if not fx_summary.empty:
                    st.subheader("Key FX Metrics")

                    best_total_return = fx_summary.sort_values(
                        "Total Return",
                        ascending=False
                    ).iloc[0]

                    lowest_volatility = fx_summary.sort_values(
                        "Annualized Volatility",
                        ascending=True
                    ).iloc[0]

                    best_sharpe = fx_summary.sort_values(
                        "Sharpe Ratio Simplified",
                        ascending=False
                    ).iloc[0]

                    worst_drawdown = fx_summary.sort_values(
                        "Max Drawdown",
                        ascending=True
                    ).iloc[0]

                    fx_metric_1, fx_metric_2, fx_metric_3, fx_metric_4 = st.columns(4)

                    with fx_metric_1:
                        st.metric(
                            "Best Total Return",
                            best_total_return["Pair"],
                            f"{best_total_return['Total Return']:.2%}"
                        )

                    with fx_metric_2:
                        st.metric(
                            "Lowest Volatility",
                            lowest_volatility["Pair"],
                            f"{lowest_volatility['Annualized Volatility']:.2%}"
                        )

                    with fx_metric_3:
                        st.metric(
                            "Best Sharpe",
                            best_sharpe["Pair"],
                            f"{best_sharpe['Sharpe Ratio Simplified']:.2f}"
                        )

                    with fx_metric_4:
                        st.metric(
                            "Worst Drawdown",
                            worst_drawdown["Pair"],
                            f"{worst_drawdown['Max Drawdown']:.2%}"
                        )

                st.subheader("FX Charts")

                fig_fx_rates = plot_fx_rates(
                    fx_close_prices_filtered
                )

                if fig_fx_rates is not None:
                    st.plotly_chart(
                        fig_fx_rates,
                        width="stretch"
                    )

                fig_fx_performance = plot_fx_performance(
                    fx_performance
                )

                if fig_fx_performance is not None:
                    st.plotly_chart(
                        fig_fx_performance,
                        width="stretch"
                    )

                fig_fx_drawdowns = plot_fx_drawdowns(
                    fx_drawdowns
                )

                if fig_fx_drawdowns is not None:
                    st.plotly_chart(
                        fig_fx_drawdowns,
                        width="stretch"
                    )

                fig_fx_correlation = plot_fx_correlation(
                    fx_correlation
                )

                if fig_fx_correlation is not None:
                    st.plotly_chart(
                        fig_fx_correlation,
                        width="stretch"
                    )

                fig_fx_total_return = plot_fx_summary_bar(
                    summary=fx_summary,
                    metric="Total Return",
                    title="FX Total Return Ranking",
                    y_axis_title="Total Return",
                    y_tickformat=".0%"
                )

                if fig_fx_total_return is not None:
                    st.plotly_chart(
                        fig_fx_total_return,
                        width="stretch"
                    )

                fig_fx_volatility = plot_fx_summary_bar(
                    summary=fx_summary,
                    metric="Annualized Volatility",
                    title="FX Annualized Volatility Ranking",
                    y_axis_title="Annualized Volatility",
                    y_tickformat=".0%"
                )

                if fig_fx_volatility is not None:
                    st.plotly_chart(
                        fig_fx_volatility,
                        width="stretch"
                    )

                if show_raw_data:
                    st.subheader("Raw FX Data")

                    raw_fx_tabs = st.tabs([
                        "Rates",
                        "Returns",
                        "Performance Base 100",
                        "Drawdowns",
                        "Correlation",
                        "Long OHLC",
                        "Metadata"
                    ])

                    with raw_fx_tabs[0]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(fx_close_prices_filtered.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_fx_tabs[1]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(fx_returns.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_fx_tabs[2]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(fx_performance.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_fx_tabs[3]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(fx_drawdowns.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_fx_tabs[4]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(fx_correlation.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_fx_tabs[5]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(fx_long_filtered),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_fx_tabs[6]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(fx_metadata),
                            width="stretch",
                            hide_index=True
                        )

                st.subheader("Financial Interpretation")

                st.markdown(
                    """
                    - **EUR/USD**: quando sobe, o euro valorizou face ao dólar.
                    - **GBP/USD**: quando sobe, a libra valorizou face ao dólar.
                    - **USD/JPY**: quando sobe, o dólar valorizou face ao iene.
                    - **Total Return** mede a variação acumulada da taxa de câmbio no período selecionado.
                    - **Annualized Volatility** mede a instabilidade histórica anualizada do par cambial.
                    - **Max Drawdown** mostra a maior queda face ao máximo anterior.
                    - **Correlation** mostra se os pares tendem a mover-se em conjunto.
                    """
                )

                st.warning(
                    "Câmbios são influenciados por taxas de juro, inflação, bancos centrais, crescimento económico, fluxos comerciais, risco geopolítico e sentimento de mercado. Esta análise é histórica e não representa previsão cambial nem recomendação de investimento."
                )


# ============================================================
# TAB 7 - CRYPTO
# ============================================================

with tabs[6]:
    st.header("Crypto")

    st.markdown(
        """
        Este módulo analisa criptoativos através da Alpha Vantage.

        Criptoativos incluídos:

        - **BTC/USD**
        - **ETH/USD**

        A análise calcula preços diários, retornos, performance base 100,
        drawdowns, correlação e métricas de risco/retorno.
        """
    )

    crypto_assets_config = [
        {
            "crypto_symbol": "BTC",
            "market_symbol": "USD",
            "crypto_name": "BTC/USD"
        },
        {
            "crypto_symbol": "ETH",
            "market_symbol": "USD",
            "crypto_name": "ETH/USD"
        }
    ]

    selected_crypto_display = pd.DataFrame(crypto_assets_config)

    st.subheader("Selected Crypto Assets")

    st.dataframe(
        make_streamlit_safe_dataframe(selected_crypto_display),
        width="stretch",
        hide_index=True
    )

    st.info(
        "Usa o botão **Load Crypto Data** na sidebar para carregar os dados crypto."
    )

    if not api_status["Is Valid Locally"]:
        st.error("API key não encontrada. Verifica o ficheiro .env antes de usar este módulo.")

    elif crypto_start_date > crypto_end_date:
        st.error("Corrige o intervalo de datas Crypto na sidebar antes de analisar criptoativos.")

    else:
        if load_crypto_button:
            with st.spinner("A obter dados Crypto com Alpha Vantage ou cache local..."):
                crypto_close_prices, crypto_long, crypto_metadata, crypto_status = (
                    get_multiple_crypto_assets(
                        crypto_assets=crypto_assets_config,
                        base_url=BASE_URL,
                        api_key=API_KEY,
                        cache_dir=CACHE_DIR,
                        force_refresh=force_refresh,
                        api_sleep_seconds=API_SLEEP_SECONDS
                    )
                )

            st.session_state["crypto_close_prices"] = crypto_close_prices
            st.session_state["crypto_long"] = crypto_long
            st.session_state["crypto_metadata"] = crypto_metadata
            st.session_state["crypto_status"] = crypto_status

        crypto_close_prices = st.session_state.get(
            "crypto_close_prices",
            pd.DataFrame()
        )

        crypto_long = st.session_state.get(
            "crypto_long",
            pd.DataFrame()
        )

        crypto_metadata = st.session_state.get(
            "crypto_metadata",
            pd.DataFrame()
        )

        crypto_status = st.session_state.get(
            "crypto_status",
            pd.DataFrame()
        )

        if not crypto_status.empty:
            st.subheader("Download / Cache Status")

            st.dataframe(
                make_streamlit_safe_dataframe(crypto_status),
                width="stretch",
                hide_index=True
            )

        if crypto_close_prices.empty:
            st.info("Ainda não há dados Crypto carregados. Usa **Load Crypto Data** na sidebar.")

        else:
            crypto_start_timestamp = pd.to_datetime(crypto_start_date)
            crypto_end_timestamp = pd.to_datetime(crypto_end_date)

            crypto_close_prices_filtered = crypto_close_prices.loc[
                (crypto_close_prices.index >= crypto_start_timestamp)
                &
                (crypto_close_prices.index <= crypto_end_timestamp)
            ]

            crypto_long_filtered = crypto_long.copy()

            if not crypto_long_filtered.empty and "Date" in crypto_long_filtered.columns:
                crypto_long_filtered["Date"] = pd.to_datetime(
                    crypto_long_filtered["Date"],
                    errors="coerce"
                )

                crypto_long_filtered = crypto_long_filtered[
                    (crypto_long_filtered["Date"] >= crypto_start_timestamp)
                    &
                    (crypto_long_filtered["Date"] <= crypto_end_timestamp)
                ]

            st.subheader("Selected Date Range")

            st.write(
                f"Análise Crypto entre **{crypto_start_date}** e **{crypto_end_date}**."
            )

            if crypto_close_prices_filtered.empty:
                st.warning(
                    "Não existem dados Crypto para o intervalo de datas selecionado."
                )

            else:
                crypto_returns = calculate_returns(crypto_close_prices_filtered)
                crypto_performance = calculate_performance_base_100(crypto_close_prices_filtered)
                crypto_drawdowns = calculate_drawdowns(crypto_close_prices_filtered)

                crypto_summary = calculate_crypto_summary(
                    crypto_close_prices_filtered,
                    annualization_factor=365
                )

                crypto_correlation = calculate_correlation_matrix(
                    crypto_returns
                )

                st.subheader("Crypto Summary")

                st.dataframe(
                    make_streamlit_safe_dataframe(
                        format_crypto_summary_for_display(crypto_summary)
                    ),
                    width="stretch",
                    hide_index=True
                )

                if not crypto_summary.empty:
                    st.subheader("Key Crypto Metrics")

                    best_total_return = crypto_summary.sort_values(
                        "Total Return",
                        ascending=False
                    ).iloc[0]

                    lowest_volatility = crypto_summary.sort_values(
                        "Annualized Volatility",
                        ascending=True
                    ).iloc[0]

                    best_sharpe = crypto_summary.sort_values(
                        "Sharpe Ratio Simplified",
                        ascending=False
                    ).iloc[0]

                    worst_drawdown = crypto_summary.sort_values(
                        "Max Drawdown",
                        ascending=True
                    ).iloc[0]

                    crypto_metric_1, crypto_metric_2, crypto_metric_3, crypto_metric_4 = st.columns(4)

                    with crypto_metric_1:
                        st.metric(
                            "Best Total Return",
                            best_total_return["Pair"],
                            f"{best_total_return['Total Return']:.2%}"
                        )

                    with crypto_metric_2:
                        st.metric(
                            "Lowest Volatility",
                            lowest_volatility["Pair"],
                            f"{lowest_volatility['Annualized Volatility']:.2%}"
                        )

                    with crypto_metric_3:
                        st.metric(
                            "Best Sharpe",
                            best_sharpe["Pair"],
                            f"{best_sharpe['Sharpe Ratio Simplified']:.2f}"
                        )

                    with crypto_metric_4:
                        st.metric(
                            "Worst Drawdown",
                            worst_drawdown["Pair"],
                            f"{worst_drawdown['Max Drawdown']:.2%}"
                        )

                st.subheader("Crypto Charts")

                fig_crypto_prices = plot_crypto_prices(
                    crypto_close_prices_filtered
                )

                if fig_crypto_prices is not None:
                    st.plotly_chart(
                        fig_crypto_prices,
                        width="stretch"
                    )

                fig_crypto_performance = plot_crypto_performance(
                    crypto_performance
                )

                if fig_crypto_performance is not None:
                    st.plotly_chart(
                        fig_crypto_performance,
                        width="stretch"
                    )

                fig_crypto_drawdowns = plot_crypto_drawdowns(
                    crypto_drawdowns
                )

                if fig_crypto_drawdowns is not None:
                    st.plotly_chart(
                        fig_crypto_drawdowns,
                        width="stretch"
                    )

                fig_crypto_correlation = plot_crypto_correlation(
                    crypto_correlation
                )

                if fig_crypto_correlation is not None:
                    st.plotly_chart(
                        fig_crypto_correlation,
                        width="stretch"
                    )

                fig_crypto_total_return = plot_crypto_summary_bar(
                    summary=crypto_summary,
                    metric="Total Return",
                    title="Crypto Total Return Ranking",
                    y_axis_title="Total Return",
                    y_tickformat=".0%"
                )

                if fig_crypto_total_return is not None:
                    st.plotly_chart(
                        fig_crypto_total_return,
                        width="stretch"
                    )

                fig_crypto_volatility = plot_crypto_summary_bar(
                    summary=crypto_summary,
                    metric="Annualized Volatility",
                    title="Crypto Annualized Volatility Ranking",
                    y_axis_title="Annualized Volatility",
                    y_tickformat=".0%"
                )

                if fig_crypto_volatility is not None:
                    st.plotly_chart(
                        fig_crypto_volatility,
                        width="stretch"
                    )

                if show_raw_data:
                    st.subheader("Raw Crypto Data")

                    raw_crypto_tabs = st.tabs([
                        "Prices",
                        "Returns",
                        "Performance Base 100",
                        "Drawdowns",
                        "Correlation",
                        "Long OHLCV",
                        "Metadata"
                    ])

                    with raw_crypto_tabs[0]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(crypto_close_prices_filtered.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_crypto_tabs[1]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(crypto_returns.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_crypto_tabs[2]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(crypto_performance.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_crypto_tabs[3]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(crypto_drawdowns.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_crypto_tabs[4]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(crypto_correlation.reset_index()),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_crypto_tabs[5]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(crypto_long_filtered),
                            width="stretch",
                            hide_index=True
                        )

                    with raw_crypto_tabs[6]:
                        st.dataframe(
                            make_streamlit_safe_dataframe(crypto_metadata),
                            width="stretch",
                            hide_index=True
                        )

                st.subheader("Financial Interpretation")

                st.markdown(
                    """
                    - **BTC/USD** mostra o preço do Bitcoin em dólares.
                    - **ETH/USD** mostra o preço do Ethereum em dólares.
                    - **Total Return** mede a valorização acumulada no período selecionado.
                    - **Annualized Volatility** mostra a instabilidade histórica anualizada.
                    - **Max Drawdown** mostra a maior queda face ao máximo anterior.
                    - **Correlation** mostra se BTC e ETH tendem a mover-se em conjunto.
                    - Criptoativos tendem a ter volatilidade e drawdowns superiores a muitos ativos tradicionais.
                    """
                )

                st.warning(
                    "Criptoativos são altamente voláteis e podem sofrer perdas acentuadas. Esta análise usa dados históricos e não representa previsão nem recomendação de investimento."
                )



# ============================================================
# TAB 8 - MACRO
# ============================================================

with tabs[7]:
    st.header("Macro")

    st.markdown(
        """
        Este módulo analisa indicadores macroeconómicos através da Alpha Vantage.

        Indicadores incluídos:

        - **Treasury Yield 10Y**
        - **Federal Funds Rate**
        - **CPI**
        - **Unemployment**

        A V6.1 separa a análise macro em **níveis** e **variações** para evitar
        comparar indicadores com unidades diferentes no mesmo gráfico.
        """
    )

    macro_indicators_config = [
        {
            "function": "TREASURY_YIELD",
            "name": "Treasury Yield 10Y",
            "interval": "monthly",
            "maturity": "10year"
        },
        {
            "function": "FEDERAL_FUNDS_RATE",
            "name": "Federal Funds Rate",
            "interval": "monthly"
        },
        {
            "function": "CPI",
            "name": "CPI",
            "interval": "monthly"
        },
        {
            "function": "UNEMPLOYMENT",
            "name": "Unemployment",
            "interval": None
        }
    ]

    selected_macro_display = pd.DataFrame(macro_indicators_config)

    st.subheader("Selected Macro Indicators")

    st.dataframe(
        make_streamlit_safe_dataframe(selected_macro_display),
        width="stretch",
        hide_index=True
    )

    st.info(
        "Usa o botão **Load Macro Data** na sidebar para carregar os dados macroeconómicos."
    )

    if not api_status["Is Valid Locally"]:
        st.error("API key não encontrada. Verifica o ficheiro .env antes de usar este módulo.")

    elif macro_start_date > macro_end_date:
        st.error("Corrige o intervalo de datas Macro na sidebar antes de analisar indicadores macroeconómicos.")

    else:
        if load_macro_button:
            with st.spinner("A obter dados Macro com Alpha Vantage ou cache local..."):
                macro_values, macro_long, macro_metadata, macro_status = (
                    get_multiple_macro_indicators(
                        macro_indicators=macro_indicators_config,
                        base_url=BASE_URL,
                        api_key=API_KEY,
                        cache_dir=CACHE_DIR,
                        force_refresh=force_refresh,
                        api_sleep_seconds=API_SLEEP_SECONDS
                    )
                )

            st.session_state["macro_values"] = macro_values
            st.session_state["macro_long"] = macro_long
            st.session_state["macro_metadata"] = macro_metadata
            st.session_state["macro_status"] = macro_status

        macro_values = st.session_state.get(
            "macro_values",
            pd.DataFrame()
        )

        macro_long = st.session_state.get(
            "macro_long",
            pd.DataFrame()
        )

        macro_metadata = st.session_state.get(
            "macro_metadata",
            pd.DataFrame()
        )

        macro_status = st.session_state.get(
            "macro_status",
            pd.DataFrame()
        )

        if not macro_status.empty:
            st.subheader("Download / Cache Status")

            st.dataframe(
                make_streamlit_safe_dataframe(macro_status),
                width="stretch",
                hide_index=True
            )

        if macro_values.empty:
            st.info("Ainda não há dados Macro carregados. Usa **Load Macro Data** na sidebar.")

        else:
            macro_start_timestamp = pd.to_datetime(macro_start_date)
            macro_end_timestamp = pd.to_datetime(macro_end_date)

            macro_values_filtered = macro_values.loc[
                (macro_values.index >= macro_start_timestamp)
                &
                (macro_values.index <= macro_end_timestamp)
            ]

            macro_long_filtered = macro_long.copy()

            if not macro_long_filtered.empty and "Date" in macro_long_filtered.columns:
                macro_long_filtered["Date"] = pd.to_datetime(
                    macro_long_filtered["Date"],
                    errors="coerce"
                )

                macro_long_filtered = macro_long_filtered[
                    (macro_long_filtered["Date"] >= macro_start_timestamp)
                    &
                    (macro_long_filtered["Date"] <= macro_end_timestamp)
                ]

            st.subheader("Selected Date Range")

            st.write(
                f"Análise Macro entre **{macro_start_date}** e **{macro_end_date}**."
            )

            if macro_values_filtered.empty:
                st.warning(
                    "Não existem dados Macro para o intervalo de datas selecionado."
                )

            else:
                macro_changes, macro_changes_long = calculate_macro_changes(
                    macro_values=macro_values_filtered,
                    periods_for_yoy=12
                )

                macro_summary = calculate_macro_summary(
                    macro_values=macro_values_filtered,
                    periods_for_yoy=12
                )

                st.subheader("Macro Summary")

                st.dataframe(
                    make_streamlit_safe_dataframe(
                        format_macro_summary_for_display(macro_summary)
                    ),
                    width="stretch",
                    hide_index=True
                )

                if not macro_summary.empty:
                    st.subheader("Key Macro Metrics")

                    latest_summary = macro_summary.copy()

                    treasury_row = latest_summary[
                        latest_summary["Indicator"] == "Treasury Yield 10Y"
                    ]

                    fed_funds_row = latest_summary[
                        latest_summary["Indicator"] == "Federal Funds Rate"
                    ]

                    cpi_row = latest_summary[
                        latest_summary["Indicator"] == "CPI"
                    ]

                    unemployment_row = latest_summary[
                        latest_summary["Indicator"] == "Unemployment"
                    ]

                    macro_metric_1, macro_metric_2, macro_metric_3, macro_metric_4 = st.columns(4)

                    with macro_metric_1:
                        if not treasury_row.empty:
                            st.metric(
                                "Latest 10Y Yield",
                                f"{treasury_row.iloc[0]['Latest Value']:.2f}",
                                f"YoY: {treasury_row.iloc[0]['Latest YoY Change']:.2f}"
                                if pd.notna(treasury_row.iloc[0]["Latest YoY Change"])
                                else None
                            )

                    with macro_metric_2:
                        if not fed_funds_row.empty:
                            st.metric(
                                "Latest Fed Funds",
                                f"{fed_funds_row.iloc[0]['Latest Value']:.2f}",
                                f"YoY: {fed_funds_row.iloc[0]['Latest YoY Change']:.2f}"
                                if pd.notna(fed_funds_row.iloc[0]["Latest YoY Change"])
                                else None
                            )

                    with macro_metric_3:
                        if not cpi_row.empty:
                            st.metric(
                                "Latest CPI",
                                f"{cpi_row.iloc[0]['Latest Value']:.2f}",
                                f"YoY %: {cpi_row.iloc[0]['Latest YoY % Change']:.2%}"
                                if pd.notna(cpi_row.iloc[0]["Latest YoY % Change"])
                                else None
                            )

                    with macro_metric_4:
                        if not unemployment_row.empty:
                            st.metric(
                                "Latest Unemployment",
                                f"{unemployment_row.iloc[0]['Latest Value']:.2f}",
                                f"YoY: {unemployment_row.iloc[0]['Latest YoY Change']:.2f}"
                                if pd.notna(unemployment_row.iloc[0]["Latest YoY Change"])
                                else None
                            )

                st.subheader("Macro Analysis")

                st.info(
                    "Nota de leitura: CPI é um índice, enquanto Federal Funds Rate, Treasury Yield e Unemployment são taxas. "
                    "Por isso, os valores absolutos não devem ser comparados diretamente no mesmo eixo. "
                    "Nesta versão, os níveis e as variações estão separados para facilitar a interpretação."
                )

                macro_analysis_tabs = st.tabs([
                    "Macro Levels",
                    "Macro Changes",
                    "Macro Comparison",
                    "Raw Macro Data"
                ])

                with macro_analysis_tabs[0]:
                    st.subheader("Macro Levels")

                    st.markdown(
                        """
                        Esta secção mostra cada indicador no seu próprio gráfico.
                        Isto evita que o **CPI**, por ser um índice acima de 300,
                        torne visualmente pequenas as taxas como Fed Funds, Treasury Yield e Unemployment.
                        """
                    )

                    level_col_1, level_col_2 = st.columns(2)

                    with level_col_1:
                        fig_cpi_level = plot_single_macro_indicator(
                            macro_values=macro_values_filtered,
                            indicator="CPI",
                            title="CPI Level",
                            y_axis_title="CPI Index"
                        )

                        if fig_cpi_level is not None:
                            st.plotly_chart(
                                fig_cpi_level,
                                width="stretch"
                            )

                        fig_treasury_level = plot_single_macro_indicator(
                            macro_values=macro_values_filtered,
                            indicator="Treasury Yield 10Y",
                            title="Treasury Yield 10Y",
                            y_axis_title="Yield (%)"
                        )

                        if fig_treasury_level is not None:
                            st.plotly_chart(
                                fig_treasury_level,
                                width="stretch"
                            )

                    with level_col_2:
                        fig_fed_level = plot_single_macro_indicator(
                            macro_values=macro_values_filtered,
                            indicator="Federal Funds Rate",
                            title="Federal Funds Rate",
                            y_axis_title="Rate (%)"
                        )

                        if fig_fed_level is not None:
                            st.plotly_chart(
                                fig_fed_level,
                                width="stretch"
                            )

                        fig_unemployment_level = plot_single_macro_indicator(
                            macro_values=macro_values_filtered,
                            indicator="Unemployment",
                            title="Unemployment Rate",
                            y_axis_title="Rate (%)"
                        )

                        if fig_unemployment_level is not None:
                            st.plotly_chart(
                                fig_unemployment_level,
                                width="stretch"
                            )

                with macro_analysis_tabs[1]:
                    st.subheader("Macro Changes")

                    st.markdown(
                        """
                        Esta secção é mais útil para comparar dinâmica macroeconómica.
                        Para o **CPI**, a variação YoY % funciona como leitura aproximada da inflação anual.
                        Para taxas, a variação YoY em pontos é normalmente mais interpretável.
                        """
                    )

                    fig_macro_yoy = plot_macro_yoy_change(
                        macro_changes_long
                    )

                    if fig_macro_yoy is not None:
                        st.plotly_chart(
                            fig_macro_yoy,
                            width="stretch"
                        )

                    fig_macro_yoy_percent = plot_macro_yoy_percent_change(
                        macro_changes_long
                    )

                    if fig_macro_yoy_percent is not None:
                        st.plotly_chart(
                            fig_macro_yoy_percent,
                            width="stretch"
                        )

                with macro_analysis_tabs[2]:
                    st.subheader("Macro Comparison")

                    st.markdown(
                        """
                        Estes gráficos resumem valores recentes e alterações absolutas.
                        Devem ser lidos com cuidado porque misturam indicadores com unidades diferentes.
                        """
                    )

                    fig_macro_latest = plot_macro_bar_clean(
                        summary=macro_summary,
                        metric="Latest Value",
                        title="Latest Macroeconomic Values",
                        y_axis_title="Latest Value"
                    )

                    if fig_macro_latest is not None:
                        st.plotly_chart(
                            fig_macro_latest,
                            width="stretch"
                        )

                    fig_macro_absolute_change = plot_macro_bar_clean(
                        summary=macro_summary,
                        metric="Absolute Change",
                        title="Macro Absolute Change Over Selected Period",
                        y_axis_title="Absolute Change"
                    )

                    if fig_macro_absolute_change is not None:
                        st.plotly_chart(
                            fig_macro_absolute_change,
                            width="stretch"
                        )

                with macro_analysis_tabs[3]:
                    st.subheader("Raw Macro Data")

                    if show_raw_data:
                        raw_macro_tabs = st.tabs([
                            "Values",
                            "Changes Long",
                            "Long Data",
                            "Metadata"
                        ])

                        with raw_macro_tabs[0]:
                            st.dataframe(
                                make_streamlit_safe_dataframe(macro_values_filtered.reset_index()),
                                width="stretch",
                                hide_index=True
                            )

                        with raw_macro_tabs[1]:
                            st.dataframe(
                                make_streamlit_safe_dataframe(macro_changes_long),
                                width="stretch",
                                hide_index=True
                            )

                        with raw_macro_tabs[2]:
                            st.dataframe(
                                make_streamlit_safe_dataframe(macro_long_filtered),
                                width="stretch",
                                hide_index=True
                            )

                        with raw_macro_tabs[3]:
                            st.dataframe(
                                make_streamlit_safe_dataframe(macro_metadata),
                                width="stretch",
                                hide_index=True
                            )
                    else:
                        st.info(
                            "Ativa **Show raw data tables** na sidebar para ver as tabelas brutas."
                        )

                st.subheader("Financial Interpretation")

                st.markdown(
                    """
                    - **Treasury Yield 10Y** é uma referência importante para taxas longas, desconto de cash flows e valuation.
                    - **Federal Funds Rate** representa a política monetária de curto prazo da Fed.
                    - **CPI** mede o nível de preços ao consumidor; a variação YoY % é uma proxy de inflação.
                    - **Unemployment** mede a taxa de desemprego e ajuda a avaliar o ciclo económico.
                    - **MoM Change** mostra a alteração face ao período anterior.
                    - **YoY Change** compara com o mesmo período do ano anterior.
                    - **YoY % Change** é mais útil para índices como CPI do que para taxas como Fed Funds ou desemprego.
                    - A separação entre níveis e variações reduz erros de leitura causados por escalas diferentes.
                    """
                )

                st.warning(
                    "Indicadores macroeconómicos têm revisões, atrasos de publicação e exigem contexto económico. Esta análise é histórica e não representa previsão económica nem recomendação de investimento."
                )


# ============================================================
# TAB 9 - EXPORT
# ============================================================

with tabs[8]:
    st.header("Export")

    st.markdown(
        """
        Este módulo exporta para Excel os dados atualmente carregados na app.

        A exportação usa os dados em `st.session_state`, por isso deves carregar primeiro
        os módulos que queres incluir no relatório: Stocks, Fundamentals, Commodities, FX,
        Crypto e Macro.
        """
    )

    st.subheader("Export Status")

    stock_close_prices_export = st.session_state.get("stock_close_prices", pd.DataFrame())
    stock_prices_long_export = st.session_state.get("stock_prices_long", pd.DataFrame())
    stock_metadata_export = st.session_state.get("stock_metadata", pd.DataFrame())
    stock_status_export = st.session_state.get("stock_status", pd.DataFrame())

    fundamentals_overview_export = st.session_state.get("fundamentals_overview", pd.DataFrame())
    fundamentals_metadata_export = st.session_state.get("fundamentals_metadata", pd.DataFrame())
    fundamentals_status_export = st.session_state.get("fundamentals_status", pd.DataFrame())

    commodity_values_export = st.session_state.get("commodity_values", pd.DataFrame())
    commodity_long_export = st.session_state.get("commodity_long", pd.DataFrame())
    commodity_metadata_export = st.session_state.get("commodity_metadata", pd.DataFrame())
    commodity_status_export = st.session_state.get("commodity_status", pd.DataFrame())

    fx_close_prices_export = st.session_state.get("fx_close_prices", pd.DataFrame())
    fx_long_export = st.session_state.get("fx_long", pd.DataFrame())
    fx_metadata_export = st.session_state.get("fx_metadata", pd.DataFrame())
    fx_status_export = st.session_state.get("fx_status", pd.DataFrame())

    crypto_close_prices_export = st.session_state.get("crypto_close_prices", pd.DataFrame())
    crypto_long_export = st.session_state.get("crypto_long", pd.DataFrame())
    crypto_metadata_export = st.session_state.get("crypto_metadata", pd.DataFrame())
    crypto_status_export = st.session_state.get("crypto_status", pd.DataFrame())

    macro_values_export = st.session_state.get("macro_values", pd.DataFrame())
    macro_long_export = st.session_state.get("macro_long", pd.DataFrame())
    macro_metadata_export = st.session_state.get("macro_metadata", pd.DataFrame())
    macro_status_export = st.session_state.get("macro_status", pd.DataFrame())

    export_status = pd.DataFrame([
        {
            "Module": "Stocks",
            "Loaded": "Yes" if not stock_close_prices_export.empty else "No",
            "Main Dataset Rows": len(stock_close_prices_export),
            "Comment": "Stock prices loaded." if not stock_close_prices_export.empty else "Load Stock Data first."
        },
        {
            "Module": "Fundamentals",
            "Loaded": "Yes" if not fundamentals_overview_export.empty else "No",
            "Main Dataset Rows": len(fundamentals_overview_export),
            "Comment": "Fundamental data loaded." if not fundamentals_overview_export.empty else "Load Fundamental Data first."
        },
        {
            "Module": "Commodities",
            "Loaded": "Yes" if not commodity_values_export.empty else "No",
            "Main Dataset Rows": len(commodity_values_export),
            "Comment": "Commodity data loaded." if not commodity_values_export.empty else "Load Commodities Data first."
        },
        {
            "Module": "FX",
            "Loaded": "Yes" if not fx_close_prices_export.empty else "No",
            "Main Dataset Rows": len(fx_close_prices_export),
            "Comment": "FX data loaded." if not fx_close_prices_export.empty else "Load FX Data first."
        },
        {
            "Module": "Crypto",
            "Loaded": "Yes" if not crypto_close_prices_export.empty else "No",
            "Main Dataset Rows": len(crypto_close_prices_export),
            "Comment": "Crypto data loaded." if not crypto_close_prices_export.empty else "Load Crypto Data first."
        },
        {
            "Module": "Macro",
            "Loaded": "Yes" if not macro_values_export.empty else "No",
            "Main Dataset Rows": len(macro_values_export),
            "Comment": "Macro data loaded." if not macro_values_export.empty else "Load Macro Data first."
        }
    ])

    st.dataframe(
        make_streamlit_safe_dataframe(export_status),
        width="stretch",
        hide_index=True
    )

    st.subheader("Export Settings")

    export_file_prefix = st.text_input(
        "Excel file prefix",
        value="alpha_vantage_report",
        help="Prefixo usado no nome do ficheiro Excel exportado."
    )

    include_raw_data_export = st.checkbox(
        "Include raw data in Excel export",
        value=True,
        help="Inclui tabelas raw/long e metadata no ficheiro Excel."
    )

    st.info(
        "O relatório Excel usa os filtros de datas atualmente selecionados na sidebar. "
        "Por exemplo, se escolheres Stock start date = 2022-01-01, o Excel exporta as ações a partir dessa data."
    )

    if st.button("Generate Excel Report", type="primary"):
        with st.spinner("A gerar relatório Excel..."):
            dataframes_to_export = {}
            notes = [
                "The Excel report uses the current date filters selected in the Streamlit sidebar.",
                "Historical data and calculated metrics are educational and are not investment advice.",
                "Currency display is visual only and does not perform FX conversion."
            ]

            # ------------------------------
            # Stocks
            # ------------------------------
            if not stock_close_prices_export.empty and stock_start_date <= stock_end_date:
                stock_start_timestamp = pd.to_datetime(stock_start_date)
                stock_end_timestamp = pd.to_datetime(stock_end_date)

                stock_prices_filtered_export = stock_close_prices_export.loc[
                    (stock_close_prices_export.index >= stock_start_timestamp)
                    &
                    (stock_close_prices_export.index <= stock_end_timestamp)
                ]

                stock_long_filtered_export = stock_prices_long_export.copy()

                if not stock_long_filtered_export.empty and "Date" in stock_long_filtered_export.columns:
                    stock_long_filtered_export["Date"] = pd.to_datetime(
                        stock_long_filtered_export["Date"],
                        errors="coerce"
                    )

                    stock_long_filtered_export = stock_long_filtered_export[
                        (stock_long_filtered_export["Date"] >= stock_start_timestamp)
                        &
                        (stock_long_filtered_export["Date"] <= stock_end_timestamp)
                    ]

                if not stock_prices_filtered_export.empty:
                    stock_returns_export = calculate_returns(stock_prices_filtered_export)
                    stock_performance_export = calculate_performance_base_100(stock_prices_filtered_export)
                    stock_drawdowns_export = calculate_drawdowns(stock_prices_filtered_export)
                    stock_summary_export = calculate_risk_return_summary(stock_prices_filtered_export)
                    stock_correlation_export = calculate_correlation_matrix(stock_returns_export)

                    dataframes_to_export["Stock Summary"] = stock_summary_export
                    dataframes_to_export["Stock Prices"] = stock_prices_filtered_export.reset_index()
                    dataframes_to_export["Stock Returns"] = stock_returns_export.reset_index()
                    dataframes_to_export["Stock Performance"] = stock_performance_export.reset_index()
                    dataframes_to_export["Stock Drawdowns"] = stock_drawdowns_export.reset_index()
                    dataframes_to_export["Stock Correlation"] = stock_correlation_export.reset_index()

                    if include_raw_data_export:
                        dataframes_to_export["Stock Long OHLCV"] = stock_long_filtered_export
                        dataframes_to_export["Stock Metadata"] = stock_metadata_export
                        dataframes_to_export["Stock Status"] = stock_status_export

                    # Technical indicators export for the first available ticker
                    first_technical_ticker = stock_prices_filtered_export.columns[0]
                    technical_export = calculate_technical_indicators(
                        close_prices=stock_prices_filtered_export[first_technical_ticker].dropna(),
                        sma_short_window=20,
                        sma_long_window=50,
                        rsi_period=14,
                        macd_fast=12,
                        macd_slow=26,
                        macd_signal=9
                    )

                    dataframes_to_export[f"Technical {first_technical_ticker}"] = technical_export.reset_index()

            # ------------------------------
            # Fundamentals
            # ------------------------------
            if not fundamentals_overview_export.empty:
                fundamental_ranking_export = create_fundamental_ranking(fundamentals_overview_export)

                dataframes_to_export["Fundamentals Overview"] = fundamentals_overview_export
                dataframes_to_export["Fundamental Ranking"] = fundamental_ranking_export

                if include_raw_data_export:
                    dataframes_to_export["Fundamentals Metadata"] = fundamentals_metadata_export
                    dataframes_to_export["Fundamentals Status"] = fundamentals_status_export

            # ------------------------------
            # Commodities
            # ------------------------------
            if not commodity_values_export.empty and commodity_start_date <= commodity_end_date:
                commodity_start_timestamp = pd.to_datetime(commodity_start_date)
                commodity_end_timestamp = pd.to_datetime(commodity_end_date)

                commodity_values_filtered_export = commodity_values_export.loc[
                    (commodity_values_export.index >= commodity_start_timestamp)
                    &
                    (commodity_values_export.index <= commodity_end_timestamp)
                ]

                commodity_long_filtered_export = commodity_long_export.copy()

                if not commodity_long_filtered_export.empty and "Date" in commodity_long_filtered_export.columns:
                    commodity_long_filtered_export["Date"] = pd.to_datetime(
                        commodity_long_filtered_export["Date"],
                        errors="coerce"
                    )

                    commodity_long_filtered_export = commodity_long_filtered_export[
                        (commodity_long_filtered_export["Date"] >= commodity_start_timestamp)
                        &
                        (commodity_long_filtered_export["Date"] <= commodity_end_timestamp)
                    ]

                if not commodity_values_filtered_export.empty:
                    commodity_returns_export = calculate_returns(commodity_values_filtered_export)
                    commodity_performance_export = calculate_performance_base_100(commodity_values_filtered_export)
                    commodity_drawdowns_export = calculate_drawdowns(commodity_values_filtered_export)
                    commodity_summary_export = calculate_commodity_summary(commodity_values_filtered_export, annualization_factor=12)
                    commodity_correlation_export = calculate_correlation_matrix(commodity_returns_export)

                    dataframes_to_export["Commodities Summary"] = commodity_summary_export
                    dataframes_to_export["Commodities Values"] = commodity_values_filtered_export.reset_index()
                    dataframes_to_export["Commodities Returns"] = commodity_returns_export.reset_index()
                    dataframes_to_export["Commodities Performance"] = commodity_performance_export.reset_index()
                    dataframes_to_export["Commodities Drawdowns"] = commodity_drawdowns_export.reset_index()
                    dataframes_to_export["Commodities Correlation"] = commodity_correlation_export.reset_index()

                    if include_raw_data_export:
                        dataframes_to_export["Commodities Long"] = commodity_long_filtered_export
                        dataframes_to_export["Commodities Metadata"] = commodity_metadata_export
                        dataframes_to_export["Commodities Status"] = commodity_status_export

            # ------------------------------
            # FX
            # ------------------------------
            if not fx_close_prices_export.empty and fx_start_date <= fx_end_date:
                fx_start_timestamp = pd.to_datetime(fx_start_date)
                fx_end_timestamp = pd.to_datetime(fx_end_date)

                fx_prices_filtered_export = fx_close_prices_export.loc[
                    (fx_close_prices_export.index >= fx_start_timestamp)
                    &
                    (fx_close_prices_export.index <= fx_end_timestamp)
                ]

                fx_long_filtered_export = fx_long_export.copy()

                if not fx_long_filtered_export.empty and "Date" in fx_long_filtered_export.columns:
                    fx_long_filtered_export["Date"] = pd.to_datetime(
                        fx_long_filtered_export["Date"],
                        errors="coerce"
                    )

                    fx_long_filtered_export = fx_long_filtered_export[
                        (fx_long_filtered_export["Date"] >= fx_start_timestamp)
                        &
                        (fx_long_filtered_export["Date"] <= fx_end_timestamp)
                    ]

                if not fx_prices_filtered_export.empty:
                    fx_returns_export = calculate_returns(fx_prices_filtered_export)
                    fx_performance_export = calculate_performance_base_100(fx_prices_filtered_export)
                    fx_drawdowns_export = calculate_drawdowns(fx_prices_filtered_export)
                    fx_summary_export = calculate_fx_summary(fx_prices_filtered_export, annualization_factor=252)
                    fx_correlation_export = calculate_correlation_matrix(fx_returns_export)

                    dataframes_to_export["FX Summary"] = fx_summary_export
                    dataframes_to_export["FX Rates"] = fx_prices_filtered_export.reset_index()
                    dataframes_to_export["FX Returns"] = fx_returns_export.reset_index()
                    dataframes_to_export["FX Performance"] = fx_performance_export.reset_index()
                    dataframes_to_export["FX Drawdowns"] = fx_drawdowns_export.reset_index()
                    dataframes_to_export["FX Correlation"] = fx_correlation_export.reset_index()

                    if include_raw_data_export:
                        dataframes_to_export["FX Long OHLC"] = fx_long_filtered_export
                        dataframes_to_export["FX Metadata"] = fx_metadata_export
                        dataframes_to_export["FX Status"] = fx_status_export

            # ------------------------------
            # Crypto
            # ------------------------------
            if not crypto_close_prices_export.empty and crypto_start_date <= crypto_end_date:
                crypto_start_timestamp = pd.to_datetime(crypto_start_date)
                crypto_end_timestamp = pd.to_datetime(crypto_end_date)

                crypto_prices_filtered_export = crypto_close_prices_export.loc[
                    (crypto_close_prices_export.index >= crypto_start_timestamp)
                    &
                    (crypto_close_prices_export.index <= crypto_end_timestamp)
                ]

                crypto_long_filtered_export = crypto_long_export.copy()

                if not crypto_long_filtered_export.empty and "Date" in crypto_long_filtered_export.columns:
                    crypto_long_filtered_export["Date"] = pd.to_datetime(
                        crypto_long_filtered_export["Date"],
                        errors="coerce"
                    )

                    crypto_long_filtered_export = crypto_long_filtered_export[
                        (crypto_long_filtered_export["Date"] >= crypto_start_timestamp)
                        &
                        (crypto_long_filtered_export["Date"] <= crypto_end_timestamp)
                    ]

                if not crypto_prices_filtered_export.empty:
                    crypto_returns_export = calculate_returns(crypto_prices_filtered_export)
                    crypto_performance_export = calculate_performance_base_100(crypto_prices_filtered_export)
                    crypto_drawdowns_export = calculate_drawdowns(crypto_prices_filtered_export)
                    crypto_summary_export = calculate_crypto_summary(crypto_prices_filtered_export, annualization_factor=365)
                    crypto_correlation_export = calculate_correlation_matrix(crypto_returns_export)

                    dataframes_to_export["Crypto Summary"] = crypto_summary_export
                    dataframes_to_export["Crypto Prices"] = crypto_prices_filtered_export.reset_index()
                    dataframes_to_export["Crypto Returns"] = crypto_returns_export.reset_index()
                    dataframes_to_export["Crypto Performance"] = crypto_performance_export.reset_index()
                    dataframes_to_export["Crypto Drawdowns"] = crypto_drawdowns_export.reset_index()
                    dataframes_to_export["Crypto Correlation"] = crypto_correlation_export.reset_index()

                    if include_raw_data_export:
                        dataframes_to_export["Crypto Long OHLCV"] = crypto_long_filtered_export
                        dataframes_to_export["Crypto Metadata"] = crypto_metadata_export
                        dataframes_to_export["Crypto Status"] = crypto_status_export

            # ------------------------------
            # Macro
            # ------------------------------
            if not macro_values_export.empty and macro_start_date <= macro_end_date:
                macro_start_timestamp = pd.to_datetime(macro_start_date)
                macro_end_timestamp = pd.to_datetime(macro_end_date)

                macro_values_filtered_export = macro_values_export.loc[
                    (macro_values_export.index >= macro_start_timestamp)
                    &
                    (macro_values_export.index <= macro_end_timestamp)
                ]

                macro_long_filtered_export = macro_long_export.copy()

                if not macro_long_filtered_export.empty and "Date" in macro_long_filtered_export.columns:
                    macro_long_filtered_export["Date"] = pd.to_datetime(
                        macro_long_filtered_export["Date"],
                        errors="coerce"
                    )

                    macro_long_filtered_export = macro_long_filtered_export[
                        (macro_long_filtered_export["Date"] >= macro_start_timestamp)
                        &
                        (macro_long_filtered_export["Date"] <= macro_end_timestamp)
                    ]

                if not macro_values_filtered_export.empty:
                    macro_changes_export, macro_changes_long_export = calculate_macro_changes(
                        macro_values=macro_values_filtered_export,
                        periods_for_yoy=12
                    )
                    macro_summary_export = calculate_macro_summary(
                        macro_values=macro_values_filtered_export,
                        periods_for_yoy=12
                    )

                    dataframes_to_export["Macro Summary"] = macro_summary_export
                    dataframes_to_export["Macro Values"] = macro_values_filtered_export.reset_index()
                    dataframes_to_export["Macro Changes Long"] = macro_changes_long_export

                    if include_raw_data_export:
                        dataframes_to_export["Macro Long"] = macro_long_filtered_export
                        dataframes_to_export["Macro Metadata"] = macro_metadata_export
                        dataframes_to_export["Macro Status"] = macro_status_export

            # ------------------------------
            # Global status sheets
            # ------------------------------
            dataframes_to_export["Export Status"] = export_status
            dataframes_to_export["Cache Summary"] = get_folder_summary(EXPORTS_DIR)

            if not dataframes_to_export:
                st.error("Não há dados disponíveis para exportar. Carrega pelo menos um módulo primeiro.")
            else:
                output_filename = generate_export_filename(
                    prefix=export_file_prefix
                )

                output_path = EXPORTS_DIR / output_filename

                exported_path = export_alpha_vantage_report(
                    output_path=output_path,
                    app_version=APP_VERSION,
                    selected_stocks=stock_tickers,
                    dataframes=dataframes_to_export,
                    notes=notes
                )

                st.session_state["latest_export_path"] = str(exported_path)
                st.session_state["latest_export_filename"] = output_filename

        latest_export_path = st.session_state.get("latest_export_path")
        latest_export_filename = st.session_state.get("latest_export_filename")

        if latest_export_path:
            st.success(f"Relatório Excel criado com sucesso: {latest_export_filename}")

    latest_export_path = st.session_state.get("latest_export_path")
    latest_export_filename = st.session_state.get("latest_export_filename")

    if latest_export_path:
        latest_export_path = Path(latest_export_path)

        if latest_export_path.exists():
            with open(latest_export_path, "rb") as excel_file:
                st.download_button(
                    label="Download Excel Report",
                    data=excel_file,
                    file_name=latest_export_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    st.subheader("Exports Folder")

    st.dataframe(
        make_streamlit_safe_dataframe(get_folder_summary(EXPORTS_DIR)),
        width="stretch",
        hide_index=True
    )


# ============================================================
# TAB 10 - GLOSSARY
# ============================================================

with tabs[9]:
    st.header("Glossary")

    glossary = render_metric_explanation_table()

    st.dataframe(
        make_streamlit_safe_dataframe(glossary),
        width="stretch",
        hide_index=True
    )

    st.markdown(
        """
        ### Nota

        Esta app é educacional. Os resultados históricos não são previsões e
        não representam recomendação de investimento.
        """
    )
