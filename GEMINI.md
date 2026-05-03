# Turtle Trading Backtester

A Python-based backtesting engine implementing a "Turtle Trading" style strategy using Donchian Channels and Average True Range (ATR).

## Project Overview

This project provides a command-line interface (CLI) to backtest and optimize trading strategies based on breakout signals. It supports pyramiding (adding units to winning positions), trailing stops, and both long-only or long-short trading modes.

### Key Technologies
- **Data Source:** [yfinance](https://github.com/ranaroussi/yfinance) for fetching historical stock data.
- **Analysis:** [pandas](https://pandas.pydata.org/) and [NumPy](https://numpy.org/) for indicator calculations and backtesting logic.
- **Visualization:** [matplotlib](https://matplotlib.org/) for plotting stock prices, channels, and trade signals.

### Core Features
- **Donchian Channels:** Used for entry and exit signals (breakouts).
- **ATR (Average True Range):** Used for position sizing, pyramiding increments, and stop-loss distances.
- **5-Year Historical Analysis:** Automatically fetches 5 years of data, rounded to the start of the calendar year.
- **Annual Performance Summary:** Provides a year-by-year breakdown of trade counts and total profit.
- **Pyramiding:** Automatically adds up to 4 units to a position as the price moves in a favorable direction.
- **Optimization:** Grid search functionality to find the best combination of Donchian periods and ATR multipliers.
- **Output:** Generates trade logs (CSV), equity curves, and visual plots (PNG) stored in the `test_output/` directory.

---

## Getting Started

### Prerequisites
Ensure you have Python installed and the following libraries:
```bash
pip install yfinance pandas numpy matplotlib
```

### Running a Backtest
To run a standard backtest, execute the script and follow the interactive prompts for ticker symbol, capital, and risk parameters:
```bash
python backtester.py
```

### Advanced Usage
- **Visualize Results:** Use the `--plot` flag to generate a PNG plot of the backtest.
  ```bash
  python backtester.py --plot
  ```
- **Parameter Optimization:** Use the `--optimize` flag to search for optimal Donchian and ATR settings.
  ```bash
  python backtester.py --optimize
  ```
- **Execution Mode:** Generate trading levels (entry, exit, stop loss, unit size) for the next trading session.
  ```bash
  python backtester.py --execute --ticker AAPL --capital 10000 --risk 2 --d-entry 20 --d-exit 10
  ```
- **Custom Parameters via CLI:** Most parameters can now be passed as arguments to avoid interactive prompts.
  ```bash
  python backtester.py --ticker SPY --capital 50000 --risk 1 --years 10 --d-entry 55 --d-exit 20 --atr-mult 3.0
  ```
- **Trade Mode:** Specify whether to trade only long or both long and short.
  ```bash
  python backtester.py --mode long_only
  python backtester.py --mode long_short  # Default
  ```

---

## Development Conventions

- **Module Structure:** All core logic resides in `backtester.py`.
- **Output Management:** All results (CSV and PNG) should be directed to the `test_output/` folder.
- **Interactive Inputs:** The CLI currently relies on `input()` for configuration; future updates may migrate these to command-line arguments via `argparse`.
- **Error Handling:** Basic error handling for ticker data fetching is implemented in `get_data`.

## Future Enhancements
Planned improvements are documented in `future-enhancement.md`, including:
- 200-Day SMA trend filter.
- Batch processing for multiple tickers.
- Advanced risk metrics (Sharpe, Sortino, Profit Factor).
- Commission and slippage modeling.
