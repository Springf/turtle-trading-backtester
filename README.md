# Turtle Trading Backtester

A robust Python-based backtesting engine implementing the classic "Turtle Trading" strategy. It utilizes Donchian Channels for breakout signals and Average True Range (ATR) for position sizing, pyramiding, and risk management.

## Features

- **Breakout Strategy:** Uses Donchian Channels for entry (e.g., 20-day high) and exit (e.g., 10-day low) signals.
- **Risk Management:** ATR-based position sizing and stop-loss calculations to normalize risk across different volatilities.
- **Pyramiding:** Automatically adds up to 4 units to a position as the price moves favorably.
- **Trailing Stops:** Implements dynamic trailing stops based on ATR.
- **Flexible Modes:** Supports both `long_only` and `long_short` trading.
- **Optimization:** Grid search functionality to find the best Donchian period and ATR multiplier for any ticker.
- **Execution Mode:** Generate specific entry, exit, and stop-loss levels for the next trading day.
- **Visualization:** Generates detailed plots of price action, channels, and trade signals.
- **Detailed Reporting:** Provides annual performance summaries and exports full trade logs to CSV.

## Getting Started

### Prerequisites

You will need Python 3.x installed. The following libraries are required:

```bash
pip install yfinance pandas numpy matplotlib
```

### Quick Start

Run the backtester interactively by simply executing:

```bash
python backtester.py
```

Follow the prompts to enter the ticker symbol, starting capital, and risk parameters.

## Usage Guide

### Command-Line Arguments

The program supports various flags to bypass interactive prompts and enable specific features:

| Argument | Description | Example |
| :--- | :--- | :--- |
| `--ticker` | Stock ticker symbol | `--ticker AAPL` |
| `--capital` | Starting capital amount | `--capital 10000` |
| `--risk` | Risk per trade as a percentage | `--risk 2` |
| `--years` | Number of years of historical data | `--years 10` |
| `--d-entry` | Donchian Entry Period (days) | `--d-entry 20` |
| `--d-exit` | Donchian Exit Period (days) | `--d-exit 10` |
| `--atr-mult` | ATR Multiplier for stop loss | `--atr-mult 2.5` |
| `--mode` | Trade direction (`long_only`, `long_short`) | `--mode long_only` (Default) |
| `--plot` | Generate and save a visualization plot | `--plot` |
| `--optimize` | Run parameter optimization grid search | `--optimize` |
| `--execute` | Calculate levels for the next session | `--execute` |

### Examples

**Standard Backtest with Plotting:**
```bash
python backtester.py --ticker SPY --capital 50000 --risk 1 --years 5 --plot
```

**Find Optimal Parameters:**
```bash
python backtester.py --ticker TSLA --optimize
```

**Get Tomorrow's Trading Levels:**
```bash
python backtester.py --execute --ticker BTC-USD --d-entry 20 --d-exit 10 --atr-mult 2.0
```

## Output

All generated files are stored in the `test_output/` directory:
- **CSV Logs:** Detailed records of every trade, including entry/exit dates, prices, and pyramiding units.
- **PNG Plots:** Visual representations of the backtest (if `--plot` is used).
- **Optimization Results:** CSV file containing all tested parameter combinations and their performance metrics.

## Strategy Details

- **Entry:** Long when price exceeds the `n-day` high; Short when price falls below the `n-day` low.
- **Position Sizing:** 1 unit = (Capital * Risk%) / (ATR * ATR_Multiplier).
- **Pyramiding:** Add a unit every 0.5 * ATR move in the favorable direction, up to 4 units total.
- **Stop Loss:** Initial stop at `ATR_Multiplier * ATR` from entry; trails as price moves.
- **Exit:** Exit long when price touches the `exit-period` low; Exit short when price touches the `exit-period` high.

## License

This project is open-source and available for educational purposes.
