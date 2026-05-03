import yfinance as yf
import pandas as pd
from datetime import datetime

ticker = "USO"
end_date = "2021-03-01"
start_date = "2021-01-01"

data = yf.download(ticker, start=start_date, end=end_date)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

# Calculate indicators manually for the day
donchian_period = 20
data['Donchian_Upper'] = data['High'].rolling(window=donchian_period).max().shift(1)
data['Donchian_Lower'] = data['Low'].rolling(window=donchian_period).min().shift(1)

print(data.loc['2026-01-28':'2026-01-30'])
