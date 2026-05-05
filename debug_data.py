import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def calculate_indicators(data, donchian_period, atr_period, donchian_exit_period=None):
    if donchian_exit_period is None:
        donchian_exit_period = donchian_period
    data = data.copy()
    data['Donchian_Upper'] = data['High'].rolling(window=donchian_period).max().shift(1)
    data['Donchian_Lower'] = data['Low'].rolling(window=donchian_period).min().shift(1)
    data['Exit_Lower'] = data['Low'].rolling(window=donchian_exit_period).min().shift(1)
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift(1))
    low_close = np.abs(data['Low'] - data['Close'].shift(1))
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    data['ATR'] = true_range.rolling(window=atr_period).mean()
    return data

ticker = yf.Ticker("DBA")
adj_data = ticker.history(start="2025-11-01", end="2026-01-15")
unadj_data = ticker.history(start="2025-11-01", end="2026-01-15", auto_adjust=False)

print("Comparison (Adjusted vs Unadjusted High):")
for date in adj_data.loc["2025-12-05":"2026-01-05"].index:
    print(f"Date: {date.date()}, Adj: {adj_data.loc[date, 'High']:.4f}, Unadj: {unadj_data.loc[date, 'High']:.4f}")

print("\nDividends in Dec 2025:")
print(ticker.dividends.loc["2025-12-01":"2025-12-31"])

