# Future Enhancements for Trading Backtester

This document outlines potential features and improvements to be implemented in future versions of the Donchian Channel & ATR Backtester.

## 1. Market Trend Filter (200-Day SMA)
- **Concept:** Only take Long entries when the price is above its 200-day Simple Moving Average (SMA) and Short entries when below it.
- **Benefit:** Reduces "false breakouts" during sideways or choppy market conditions.

## 2. Batch Processing / Scanner Mode
- **Concept:** Allow the program to read a `watchlist.txt` file containing multiple stock tickers.
- **Benefit:** Runs the backtest/optimization on a portfolio of stocks and generates a leaderboard of the most trend-friendly assets.

## 3. Institutional Performance Metrics
- **Concept:** Calculate and report advanced risk-adjusted metrics:
  - **Sharpe Ratio:** Measures return per unit of total risk.
  - **Sortino Ratio:** Measures return per unit of downside risk.
  - **Profit Factor:** Ratio of gross profits to gross losses.
- **Benefit:** Provides a professional-grade evaluation of the strategy's quality.

## 4. Commission & Slippage Modeling
- **Concept:** Add parameters for a fixed commission per trade and a "slippage" percentage (price impact).
- **Benefit:** Provides a more realistic "Net Profit" figure by accounting for real-world trading costs.

## 5. Portfolio Simulation
- **Concept:** Simulate a shared capital pool across multiple concurrent trades in different tickers.
- **Benefit:** Models how the strategy would perform as a managed fund with position limits and margin constraints.
