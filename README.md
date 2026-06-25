# README — Alpha Vantage Financial Dashboard

## 1. App Objective

This Streamlit app turns the project into an interactive financial analysis tool based on the Alpha Vantage API.

The objective is to make it possible to analyze, visualize, and export financial data in a practical, organized, and reusable way, including:

- stocks;
- technical indicators;
- company fundamental data;
- commodities;
- foreign exchange pairs;
- crypto assets;
- macroeconomic indicators;
- formatted Excel export.

The app was built with a focus on learning Python for Finance, financial data analysis, interactive visualization, local cache, and professional report creation.

---

## 2. Real-World Application

This app is not only a technical exercise. It simulates a real workflow used by financial analysts, research teams, finance students, consultants, and investment teams that need to collect data, organize information, calculate metrics, and produce reusable reports.

### Real Use Cases

The app can be used, with the appropriate adaptations, in contexts such as:

- **quick stock analysis**, to review prices, returns, volatility, drawdowns, and correlation;
- **company comparison**, using fundamental metrics such as Market Cap, P/E, margins, ROE, and an educational ranking;
- **global asset monitoring**, including stocks, commodities, FX, crypto, and macroeconomic indicators;
- **financial report preparation**, by exporting data and metrics to Excel;
- **research decision support**, allowing analysis of different asset classes in a single interface;
- **Python for Finance training**, because it demonstrates a full pipeline from API, cache, data cleaning, calculations, visualization, and export.

### Example of a Real Workflow

An analyst can use the app as follows:

```text
1. Define the company tickers to analyze.
2. Load historical prices and fundamental data.
3. Select the relevant date range.
4. Evaluate return, risk, drawdown, and correlation.
5. Review technical indicators to analyze trend and momentum.
6. Compare companies using fundamental metrics.
7. Analyze the macroeconomic context with CPI, Fed Funds, Treasury Yield, and Unemployment.
8. Review commodities, FX, and crypto to understand global market conditions.
9. Export the report to Excel.
10. Use the Excel file as a basis for discussion, presentation, study, or internal reporting.
```

### Practical Value for Finance

The app helps transform scattered data into structured information. Instead of manually consulting multiple pages, copying data, and building separate charts, the user can centralize everything in a single dashboard.

In practice, this is close to a small internal financial analysis system, with:

- **data ingestion**, through the Alpha Vantage API;
- **local cache**, to reduce API calls and avoid wasting requests;
- **data cleaning**, with date handling, missing value treatment, and formatting;
- **financial analytics**, with returns, volatility, simplified Sharpe ratio, drawdowns, and correlation;
- **visual analytics**, with interactive Plotly charts;
- **reporting**, through formatted Excel export.

### How This Approaches Professional Tools

This app is an educational and simplified version of workflows that exist in professional environments, such as:

- internal research dashboards;
- market monitoring tools;
- periodic portfolio reports;
- risk and performance analysis;
- investment memo preparation;
- internal financial business intelligence systems.

The logic is similar: collect data, validate it, calculate metrics, visualize, interpret, and export. The difference is that institutional tools use paid data sources, robust databases, user permissions, advanced logs, audit trails, version control, and professional data validation.

### Limitations for Professional Use

To use this app in a real professional context, several points would need to be strengthened:

- use paid and more robust data sources, such as Bloomberg, Refinitiv, FactSet, S&P Capital IQ, or premium APIs;
- validate data quality and frequency;
- improve API error handling and quota limit management;
- add user authentication;
- store data in a database, such as PostgreSQL or SQLite, instead of relying only on CSV/local cache;
- create execution logs;
- implement automated tests;
- better separate backend, frontend, and data layers;
- add permission control and security;
- review financial methodologies before any use in real decisions.

### Correct Interpretation

The app should be seen as an analysis and learning tool, not as an automatic decision-making machine.

The results help answer questions such as:

```text
Which asset had the best return during the period?
Which asset had the highest volatility?
What was the largest drawdown?
How are the assets correlated?
What is the macroeconomic context?
How have commodities, currencies, and crypto evolved?
```

But they do not automatically answer questions such as:

```text
Should I buy this asset?
Will this asset go up?
What will the future price be?
Is this company necessarily a good investment?
```

For real decisions, the app must be complemented with qualitative analysis, detailed valuation, sector context, macroeconomic analysis, risk management, and validation using professional sources.

### Next Realistic Evolution

A natural evolution of this app into a product closer to the real world would be:

```text
1. Local or cloud database.
2. Automatic data updates.
3. Personalized watchlist.
4. Portfolio analysis with user-defined weights.
5. Benchmark comparison.
6. VaR and CVaR.
7. Simple backtesting.
8. Automatic PDF report.
9. Cloud deployment.
10. Login and permission system.
```

This evolution would transform the app from an educational project into a financial analysis tool closer to a professional dashboard.

## 3. Current Project Status

Current version:

```text
V7.0 — Excel Export Module
```

Completed modules:

```text
V1 — Layout: OK
V2 — Stocks: OK
V3 — Technical Indicators: OK
V4 — Fundamentals: OK
V5.1 — Commodities: OK
V5.2 — FX: OK
V5.3 — Crypto: OK
V6.0 — Macro: OK
V6.1 — Macro Formatting: OK
V7.0 — Excel Export: OK
```

---

## 4. Folder Structure

Recommended project structure:

```text
alpha_vantage_streamlit_app/
│
├── app.py
├── .env
├── .gitignore
├── requirements.txt
├── README.md
│
├── .vscode/
│   └── launch.json
│
├── utils/
│   ├── __init__.py
│   ├── config.py
│   ├── alpha_vantage_client.py
│   ├── calculations.py
│   ├── charts.py
│   └── excel_export.py
│
└── Data/
    ├── cache/
    └── exports/
```

### Purpose of Each Folder/File

| File/Folder | Purpose |
|---|---|
| `app.py` | Main Streamlit app file. |
| `.env` | Stores the Alpha Vantage API key. |
| `.gitignore` | Prevents sensitive/cache files from being pushed to Git. |
| `requirements.txt` | Lists the required Python libraries. |
| `README.md` | Project documentation. |
| `.vscode/launch.json` | Run and Debug configuration in VS Code. |
| `utils/config.py` | Configures paths, app version, and API key. |
| `utils/alpha_vantage_client.py` | API connection and local cache functions. |
| `utils/calculations.py` | Financial and statistical calculations. |
| `utils/charts.py` | Plotly charts. |
| `utils/excel_export.py` | Formatted Excel export. |
| `Data/cache/` | Locally stored data to reduce API calls. |
| `Data/exports/` | Exported Excel reports. |

---

## 5. Libraries Used

Main libraries:

```python
streamlit
pandas
numpy
plotly
requests
python-dotenv
openpyxl
xlsxwriter
```

Installation:

```powershell
py -3.14 -m pip install -r requirements.txt
```

Recommended `requirements.txt` content:

```text
streamlit
pandas
numpy
plotly
requests
python-dotenv
openpyxl
xlsxwriter
```

---

## 6. API Key Configuration

The app uses the Alpha Vantage API.

Create a `.env` file in the main project folder:

```env
ALPHAVANTAGE_API_KEY=YOUR_API_KEY_HERE
```

The `.env` file should not be pushed to GitHub.

In `.gitignore`, keep:

```gitignore
.env
__pycache__/
*.pyc
Data/cache/
Data/exports/
```

---

## 7. How to Run the App

In PowerShell, inside the main project folder:

```powershell
cd "C:\Users\Lenovo\OneDrive - MMU\Desktop\alpha_vantage_streamlit_app"
py -3.14 -m streamlit run .\app.py
```

The app opens in the browser at:

```text
http://localhost:8501
```

---

## 8. Running via VS Code Run and Debug

Recommended `.vscode/launch.json` configuration:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run Alpha Vantage Streamlit App - Python 3.14",
            "type": "debugpy",
            "request": "launch",
            "module": "streamlit",
            "args": [
                "run",
                "${workspaceFolder}/app.py"
            ],
            "console": "integratedTerminal",
            "justMyCode": true,
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

---

## 9. App Sidebar

The sidebar is organized into blocks:

```text
1. API & Cache
2. Stocks Setup
3. Market Date Ranges
4. Data Actions
5. Display Settings
6. Project Folders
```

### 1. API & Cache

Allows the user to choose:

```text
Use local cache if available
Force API refresh
```

Recommendation:

```text
Use local cache whenever possible.
```

This avoids using too many API calls, especially because the free Alpha Vantage plan has daily limits.

### 2. Stocks Setup

Allows the user to enter comma-separated tickers:

```text
MSFT,AAPL,NVDA
```

It also allows the user to choose the stock date range:

```text
Stock start date
Stock end date
```

This filter affects:

```text
Stocks
Technical Indicators
```

### 3. Market Date Ranges

Separate filters for:

```text
Commodities
FX
Crypto
Macro
```

Each module has its own date range to avoid analyses with periods that are too long or not very relevant.

### 4. Data Actions

Main buttons:

```text
Load Stock Data
Load Fundamental Data
Load Commodities Data
Load FX Data
Load Crypto Data
Load Macro Data
```

### 5. Display Settings

Includes:

```text
Currency display
Show raw data tables
```

Note: the currency symbol is only visual and does not perform currency conversion.

### 6. Project Folders

Shows the main paths:

```text
Base
Cache
Exports
```

---

## 10. App Tabs

The app has the following tabs:

```text
Overview
Stocks
Technical Indicators
Fundamentals
Commodities
FX
Crypto
Macro
Export
Glossary
```

---

## 11. Overview Tab

The `Overview` tab shows:

- general app status;
- current version;
- API key status;
- availability of the cache and export folders;
- project roadmap;
- summary of files in cache.

It is the first tab to check to confirm whether the project is configured correctly.

---

## 12. Stocks Tab

The `Stocks` tab loads daily stock prices through Alpha Vantage.

### Main Outputs

```text
Download / Cache Status
Risk & Return Summary
Key Metrics
Price Chart
Performance Base 100
Drawdowns
Returns Histogram
Risk Return Scatter
Correlation Heatmap
Raw Data
```

### Calculated Metrics

| Metric | Interpretation |
|---|---|
| Total Return | Cumulative return during the selected period. |
| Annualized Return | Annualized return. |
| Annualized Volatility | Annualized risk/instability. |
| Sharpe Ratio Simplified | Annualized return divided by annualized volatility. |
| Max Drawdown | Largest fall from the previous peak. |
| Best Daily Return | Best daily return. |
| Worst Daily Return | Worst daily return. |

### Financial Interpretation

The analysis shows which stocks had the best historical performance during the selected interval, while also allowing comparison of risk, volatility, and drawdowns.

A stock may have a higher cumulative return, but also higher volatility and a larger drawdown.

---

## 13. Technical Indicators Tab

The `Technical Indicators` tab uses the prices loaded in the Stocks tab and applies the same stock date filter.

Included indicators:

```text
SMA
RSI
MACD
```

### SMA

Simple moving average.

```python
rolling(window).mean()
```

Used to analyze trend.

### RSI

Momentum indicator.

Common interpretation:

```text
RSI > 70 → possible overbought condition
RSI < 30 → possible oversold condition
```

### MACD

Trend and momentum indicator.

Common interpretation:

```text
MACD above the Signal Line → positive momentum
MACD below the Signal Line → negative momentum
```

### Limitation

Technical indicators are historical signals and do not guarantee future movements.

---

## 14. Fundamentals Tab

The `Fundamentals` tab uses the Alpha Vantage `OVERVIEW` endpoint.

### Main Outputs

```text
Company Overview
Key Fundamental Metrics
Fundamental Ranking
Valuation Metrics
Profitability Metrics
Risk and Income Metrics
Fundamental Charts
Raw Fundamental Data
```

### Metrics Analyzed

| Metric | Interpretation |
|---|---|
| Market Capitalization | Company market value. |
| P/E Ratio | Price divided by earnings per share. |
| Price/Sales | Relationship between price and revenue. |
| Price/Book | Relationship between price and book value. |
| Profit Margin | Percentage of revenue that remains as profit. |
| ROA | Return on assets. |
| ROE | Return on equity. |
| Beta | Historical sensitivity to the market. |
| Dividend Yield | Dividend income yield. |

### Fundamental Score

The app calculates a simple fundamental ranking for educational purposes.

This score should not be interpreted as a buy or sell recommendation.

---

## 15. Commodities Tab

The `Commodities` tab analyzes:

```text
WTI Crude Oil
Brent Crude Oil
Natural Gas
```

### Main Outputs

```text
Commodity Summary
Key Commodity Metrics
Commodity Values
Performance Base 100
Drawdowns
Correlation
Total Return Ranking
Volatility Ranking
Raw Commodities Data
```

### Financial Interpretation

Commodities are sensitive to:

- supply and demand;
- geopolitical shocks;
- inventories;
- interest rates;
- exchange rates;
- seasonality;
- economic cycles.

WTI and Brent are important oil benchmarks. Natural Gas has its own dynamics, often related to weather, reserves, and energy demand.

---

## 16. FX Tab

The `FX` tab analyzes currency pairs:

```text
EUR/USD
GBP/USD
USD/JPY
```

### Main Outputs

```text
FX Summary
Key FX Metrics
Exchange Rates
Performance Base 100
Drawdowns
Correlation
FX Total Return Ranking
FX Volatility Ranking
Raw FX Data
```

### Financial Interpretation

| Pair | Interpretation |
|---|---|
| EUR/USD rises | The euro appreciates against the dollar. |
| GBP/USD rises | The pound appreciates against the dollar. |
| USD/JPY rises | The dollar appreciates against the yen. |

Currencies are influenced by:

- interest rates;
- inflation;
- central banks;
- economic growth;
- trade flows;
- geopolitical risk;
- market sentiment.

---

## 17. Crypto Tab

The `Crypto` tab analyzes:

```text
BTC/USD
ETH/USD
```

### Main Outputs

```text
Crypto Summary
Key Crypto Metrics
Crypto Prices
Performance Base 100
Drawdowns
Correlation
Crypto Total Return Ranking
Crypto Volatility Ranking
Raw Crypto Data
```

### Financial Interpretation

Crypto assets tend to have:

- high volatility;
- severe drawdowns;
- speculative cycles;
- sensitivity to global liquidity;
- impact from regulation and institutional adoption.

This analysis uses historical data and does not represent a forecast or investment recommendation.

---

## 18. Macro Tab

The `Macro` tab analyzes U.S. macroeconomic indicators:

```text
Treasury Yield 10Y
Federal Funds Rate
CPI
Unemployment
```

### Main Outputs

```text
Macro Summary
Macro Levels
Macro Changes
Macro Comparison
Raw Macro Data
```

### Macro Levels

V6.1 improved macro formatting by separating level charts:

```text
CPI Level
Treasury Yield 10Y
Federal Funds Rate
Unemployment Rate
```

This avoids directly comparing CPI with rates on the same axis.

### Macro Changes

Includes:

```text
MoM Change
YoY Change
YoY % Change
```

### Financial Interpretation

| Indicator | Interpretation |
|---|---|
| Treasury Yield 10Y | Long-term reference yield. |
| Federal Funds Rate | Federal Reserve monetary policy rate. |
| CPI | Price index used to measure inflation. |
| Unemployment | Unemployment rate. |

Important note:

```text
CPI is an index.
Fed Funds, Treasury Yield, and Unemployment are rates.
```

Therefore, they should not be compared directly in absolute value on the same axis.

---

## 19. Export Tab

The `Export` tab creates a formatted Excel report with the data loaded in the app.

### Features

```text
Export Status
Export Settings
Generate Excel Report
Download Excel Report
Exports Folder
```

### Possible Excel Sheets

```text
README
App Summary
Stock Summary
Stock Prices
Stock Returns
Stock Performance
Stock Drawdowns
Stock Correlation
Technical Indicators
Fundamentals Overview
Fundamental Ranking
Commodities Summary
Commodities Values
FX Summary
FX Rates
Crypto Summary
Crypto Prices
Macro Summary
Macro Values
Macro Changes
Status Sheets
Metadata Sheets
```

### Important Note

Excel only exports data that has already been loaded in the app.

Example:

```text
If you have not clicked Load Macro Data yet, the Macro section will not have real data in the Excel file.
```

The exported file is saved in:

```text
Data/exports
```

---

## 20. Glossary Tab

The `Glossary` tab explains the main concepts used in the app.

It includes concepts such as:

```text
Close Price
Daily Return
Performance Base 100
Annualized Volatility
Drawdown
Max Drawdown
Correlation
SMA
RSI
MACD
Market Cap
P/E Ratio
ROE
Date Filter
```

---

## 21. Local Cache

The app uses local cache to avoid wasting API calls.

Files are saved in:

```text
Data/cache
```

When the mode is:

```text
Use local cache if available
```

The app first tries to use already saved files.

When the mode is:

```text
Force API refresh
```

The app forces a new call to Alpha Vantage.

Use `Force API refresh` carefully because it can quickly reach the API limit.

---

## 22. Excel Export

The export engine is located in:

```text
utils/excel_export.py
```

It uses:

```python
pandas.ExcelWriter(engine="openpyxl")
```

and then applies formatting with `openpyxl`.

Formatting includes:

```text
highlighted headers
freeze panes
filters
automatic column width
light borders
simple number and date formatting
```

Important rule applied:

```text
Do not use worksheet.add_table()
```

This decision avoids corrupted Excel file issues that appeared in previous projects.

---

## 23. Common Errors and Fixes

### Error: `NameError: name 'Path' is not defined`

Cause:

```text
app.py uses Path(...) but did not import pathlib.Path.
```

Fix:

```python
from pathlib import Path
```

At the top of `app.py`:

```python
from datetime import datetime, date
from pathlib import Path
```

---

### Error: Alpha Vantage limit

Cause:

```text
Too many API calls on the free plan.
```

Fix:

```text
Use Use local cache if available.
Avoid Force API refresh unless necessary.
Wait for the quota reset.
```

---

### Error: old or overly long data

Cause:

```text
The API returns the full available history for some endpoints.
```

Fix:

```text
Use the date filters in the sidebar.
```

---

### Error: poorly formatted Macro chart

Cause:

```text
CPI is an index and the other indicators are rates.
```

Fix applied:

```text
Separate macro charts by indicator/scale.
```

---

### Error: data does not appear in Excel

Cause:

```text
The module has not yet been loaded in the app.
```

Fix:

```text
Click the corresponding Load button before exporting.
```

---

## 24. Limitations

This app has several important limitations:

1. The data depends on Alpha Vantage.
2. The free API plan has call limits.
3. Some endpoints may be subject to restrictions or delays.
4. Historical data is not a forecast.
5. Technical indicators do not guarantee future movements.
6. The Fundamental Score is educational and simplified.
7. The currency symbol is only visual and does not convert values.
8. The app does not replace professional analysis, Bloomberg, Refinitiv, FactSet, or institutional data.
9. The Excel export only includes data loaded in the current session.

---

## 25. Best Practices for Use

Recommended workflow:

```text
1. Open the app
2. Confirm the API key
3. Use local cache
4. Choose tickers
5. Choose date filters
6. Load data by module
7. Validate tables and charts
8. Interpret metrics
9. Export Excel
10. Save a backup of the stable version
```

Recommended backups:

```powershell
Copy-Item .\app.py .\app_v7_0_stable_backup.py
Copy-Item .\utils\excel_export.py .\utils\excel_export_v7_0_backup.py
```

---

## 26. Possible Next Steps

Recommended future improvements:

```text
V8 — Portfolio Analysis
V9 — Benchmark Comparison
V10 — VaR / CVaR
V11 — Rolling Metrics
V12 — Portfolio Optimization
V13 — Backtesting
V14 — PDF Report
V15 — Multi-source data provider
V16 — Deployment
```

### V8 — Portfolio Analysis

Possible features:

- table of tickers and weights;
- custom portfolio;
- equal-weighted portfolio;
- portfolio return;
- volatility;
- Sharpe Ratio;
- drawdown;
- comparison against benchmark;
- Excel portfolio export.

### V9 — Benchmark Comparison

Possible features:

- choose a benchmark;
- compare asset/portfolio against SPY, QQQ, or another index;
- calculate tracking difference;
- rolling correlation;
- rolling beta.

### V10 — VaR / CVaR

Possible features:

- Historical VaR;
- Historical CVaR;
- simple simulation;
- return distribution;
- extreme loss analysis.

---

## 27. Conclusion

The `Alpha Vantage Financial Dashboard` is an educational and practical app for learning Python applied to finance.

It combines:

- data collection via API;
- local cache;
- financial analysis;
- interactive visualization;
- economic interpretation;
- formatted Excel export;
- modular Python organization.

Version V7.0 already represents a solid foundation for turning the project into a more advanced financial analysis tool, including portfolio analysis, benchmark comparison, risk, and optimization.

---

## 28. Disclaimer

This app is for educational purposes only.

Historical results, financial metrics, technical indicators, fundamental data, macroeconomic analysis, and Excel exports do not represent forecasts, financial advice, or investment recommendations.

Any financial decision should be made with additional analysis, data validation, and, where applicable, professional advice.
