import yfinance as yf
import pandas as pd
import numpy as np
import os
import argparse
from datetime import datetime, timedelta

def get_data(ticker, years=5):
    """Fetch 'years' of daily historical data for a given ticker, rounded to start of year."""
    end_date = datetime.now()
    start_year = end_date.year - years
    start_date = datetime(start_year, 1, 1)
    
    print(f"Fetching data for {ticker} from {start_date.date()} to {end_date.date()}...")
    
    # Get Ticker object for metadata
    ticker_obj = yf.Ticker(ticker)
    data = ticker_obj.history(start=start_date, end=end_date)
    
    if data.empty:
        # Fallback to download if history is empty
        data = yf.download(ticker, start=start_date, end=end_date)
        if data.empty:
            raise ValueError(f"No data found for ticker {ticker}")
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # Dynamic Currency Normalization
    try:
        currency = ticker_obj.info.get('currency', 'USD')
        print(f"Detected currency: {currency}")
        
        # If listed in Pence (GBX), normalize to Pounds (GBP)
        if currency == 'GBX':
            print(f"Normalizing {ticker} price from GBX to GBP...")
            for col in ['Open', 'High', 'Low', 'Close']:
                data[col] = data[col] / 100.0
    except Exception as e:
        print(f"Warning: Could not detect currency, using raw values. Error: {e}")
        
    return data

def calculate_indicators(data, donchian_period, atr_period, donchian_exit_period=None):
    """Calculate Donchian Channels and ATR."""
    if donchian_exit_period is None:
        donchian_exit_period = donchian_period
        
    data = data.copy()
    data['Donchian_Upper'] = data['High'].rolling(window=donchian_period).max().shift(1)
    data['Donchian_Lower'] = data['Low'].rolling(window=donchian_period).min().shift(1)
    
    data['Exit_Upper'] = data['High'].rolling(window=donchian_exit_period).max().shift(1)
    data['Exit_Lower'] = data['Low'].rolling(window=donchian_exit_period).min().shift(1)
    
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift(1))
    low_close = np.abs(data['Low'] - data['Close'].shift(1))
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    data['ATR'] = true_range.rolling(window=atr_period).mean()
    
    return data

def backtest(data, initial_capital, risk_per_trade, atr_multiplier, mode='long_only', max_leverage=1.0, exit_strategy='trailing'):
    """Run the backtesting engine with proper cash tracking and no look-ahead bias."""
    cash = initial_capital
    position = 0 # absolute number of shares
    position_type = None # 'long' or 'short'
    avg_entry_price = 0
    last_entry_price = 0
    stop_loss = 0
    units = 0
    n_atr = 0 # ATR at initial entry
    unit_size = 0
    trades = []
    equity_curve = [initial_capital]
    
    current_trade_history = []
    
    data['Buy_Signal'] = np.nan
    data['Sell_Signal'] = np.nan
    data['Short_Signal'] = np.nan
    data['Cover_Signal'] = np.nan
    data['Add_Signal'] = np.nan
    
    start_idx = data[['Donchian_Upper', 'Exit_Lower', 'ATR']].first_valid_index()
    if start_idx is None:
        return None, [], []
    
    data_to_test = data.loc[start_idx:]
    
    for date, row in data_to_test.iterrows():
        open_p = row['Open']
        close = row['Close']
        high = row['High']
        low = row['Low']
        
        # 1. Check for Exits or Pyramiding (using existing positions)
        exit_price = 0
        exit_reason = ""
        
        if position > 0:
            if position_type == 'long':
                # Check for Exit Today (using YESTERDAY'S stop_loss to avoid look-ahead)
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "Stop / Trailing"
                elif low < row['Exit_Lower']:
                    exit_price = min(open_p, row['Exit_Lower'])
                    exit_reason = "Donchian Exit"
                
                if exit_price > 0:
                    cash += (position * exit_price)
                    profit = (exit_price - avg_entry_price) * position
                    trade_record = {
                        'type': 'long', 'units': units, 'entry_date': entry_date, 'exit_date': date,
                        'avg_entry': avg_entry_price, 'exit_price': exit_price, 'shares': position,
                        'profit': profit, 'return_pct': (profit / (avg_entry_price * position)) * 100 if (avg_entry_price * position) > 0 else 0,
                        'reason': exit_reason
                    }
                    for i, unit in enumerate(current_trade_history):
                        trade_record[f'unit{i+1}_date'] = unit['date']; trade_record[f'unit{i+1}_price'] = unit['price']; trade_record[f'unit{i+1}_size'] = unit['size']
                    trades.append(trade_record)
                    data.at[date, 'Sell_Signal'] = exit_price
                    position = 0; units = 0; current_trade_history = []
                else:
                    # Check for Pyramiding
                    if units < 4 and high > last_entry_price + (0.5 * n_atr):
                        add_price = last_entry_price + (0.5 * n_atr)
                        current_equity = cash + (close * position)
                        total_power = current_equity * max_leverage
                        if total_power > (position + unit_size) * add_price:
                            new_total_cost = (avg_entry_price * position) + (unit_size * add_price)
                            cash -= (unit_size * add_price)
                            position += unit_size
                            avg_entry_price = new_total_cost / position
                            last_entry_price = add_price
                            units += 1
                            data.at[date, 'Add_Signal'] = add_price
                            current_trade_history.append({'date': date, 'price': add_price, 'size': unit_size})
                            stop_loss = last_entry_price - (atr_multiplier * n_atr)
                    
                    # Update Trailing Stop for TOMORROW (only if strategy is 'trailing')
                    if exit_strategy == 'trailing':
                        new_stop = high - (row['ATR'] * atr_multiplier)
                        if new_stop > stop_loss:
                            stop_loss = new_stop
                
            elif position_type == 'short':
                if high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "Stop / Trailing"
                elif high > row['Exit_Upper']:
                    exit_price = max(open_p, row['Exit_Upper'])
                    exit_reason = "Donchian Exit"
                
                if exit_price > 0:
                    cash -= (position * exit_price)
                    profit = (avg_entry_price - exit_price) * position
                    trade_record = {
                        'type': 'short', 'units': units, 'entry_date': entry_date, 'exit_date': date,
                        'avg_entry': avg_entry_price, 'exit_price': exit_price, 'shares': position,
                        'profit': profit, 'return_pct': (profit / (avg_entry_price * position)) * 100 if (avg_entry_price * position) > 0 else 0,
                        'reason': exit_reason
                    }
                    for i, unit in enumerate(current_trade_history):
                        trade_record[f'unit{i+1}_date'] = unit['date']; trade_record[f'unit{i+1}_price'] = unit['price']; trade_record[f'unit{i+1}_size'] = unit['size']
                    trades.append(trade_record)
                    data.at[date, 'Cover_Signal'] = exit_price
                    position = 0; units = 0; current_trade_history = []
                else:
                    if units < 4 and low < last_entry_price - (0.5 * n_atr):
                        add_price = last_entry_price - (0.5 * n_atr)
                        current_equity = cash - (close * position)
                        total_power = current_equity * max_leverage
                        if total_power > (position + unit_size) * add_price:
                            new_total_cost = (avg_entry_price * position) + (unit_size * add_price)
                            cash += (unit_size * add_price)
                            position += unit_size
                            avg_entry_price = new_total_cost / position
                            last_entry_price = add_price
                            units += 1
                            data.at[date, 'Add_Signal'] = add_price
                            current_trade_history.append({'date': date, 'price': add_price, 'size': unit_size})
                            stop_loss = last_entry_price + (atr_multiplier * n_atr)

                    if exit_strategy == 'trailing':
                        new_stop = low + (row['ATR'] * atr_multiplier)
                        if new_stop < stop_loss:
                            stop_loss = new_stop

        # 2. Check for New Entries (if no position)
        if position == 0:
            current_equity = cash
            if high > row['Donchian_Upper']:
                entry_price = max(open_p, row['Donchian_Upper'])
                n_atr = row['ATR']
                stop_distance = n_atr * atr_multiplier
                risk_amount = current_equity * risk_per_trade
                unit_size = int(risk_amount / stop_distance) if stop_distance > 0 else 0
                available_buying_power = current_equity * max_leverage
                if unit_size * entry_price > available_buying_power:
                    unit_size = int(available_buying_power / entry_price)
                
                if unit_size > 0:
                    position = unit_size
                    position_type = 'long'
                    avg_entry_price = entry_price
                    last_entry_price = entry_price
                    units = 1
                    entry_date = date
                    cash -= (unit_size * entry_price)
                    stop_loss = entry_price - stop_distance
                    data.at[date, 'Buy_Signal'] = entry_price
                    current_trade_history = [{'date': date, 'price': entry_price, 'size': unit_size}]
                    
            elif mode == 'long_short' and low < row['Donchian_Lower']:
                entry_price = min(open_p, row['Donchian_Lower'])
                n_atr = row['ATR']
                stop_distance = n_atr * atr_multiplier
                risk_amount = current_equity * risk_per_trade
                unit_size = int(risk_amount / stop_distance) if stop_distance > 0 else 0
                available_buying_power = current_equity * max_leverage
                if unit_size * entry_price > available_buying_power:
                    unit_size = int(available_buying_power / entry_price)
                
                if unit_size > 0:
                    position = unit_size
                    position_type = 'short'
                    avg_entry_price = entry_price
                    last_entry_price = entry_price
                    units = 1
                    entry_date = date
                    cash += (unit_size * entry_price)
                    stop_loss = entry_price + stop_distance
                    data.at[date, 'Short_Signal'] = entry_price
                    current_trade_history = [{'date': date, 'price': entry_price, 'size': unit_size}]

        # 3. Final Equity Calculation for the bar
        if position > 0:
            if position_type == 'long':
                current_equity = cash + (close * position)
            else:
                current_equity = cash - (close * position)
        else:
            current_equity = cash
            
        equity_curve.append(current_equity)

    if position > 0:
        final_price = data_to_test.iloc[-1]['Close']
        if position_type == 'long':
            cash += (position * final_price)
            profit = (final_price - avg_entry_price) * position
        else:
            cash -= (position * final_price)
            profit = (avg_entry_price - final_price) * position
        trade_record = {
            'type': position_type, 'units': units, 'entry_date': entry_date, 'exit_date': data_to_test.index[-1],
            'avg_entry': avg_entry_price, 'exit_price': final_price, 'shares': position,
            'profit': profit, 'return_pct': (profit / (avg_entry_price * position)) * 100 if (avg_entry_price * position) > 0 else 0,
            'reason': "End of Period"
        }
        for i, unit in enumerate(current_trade_history):
            trade_record[f'unit{i+1}_date'] = unit['date']; trade_record[f'unit{i+1}_price'] = unit['price']; trade_record[f'unit{i+1}_size'] = unit['size']
        trades.append(trade_record)
        equity_curve.append(cash)
        
    return cash, trades, equity_curve

def calculate_max_drawdown(equity_curve):
    """Calculate the maximum drawdown from an equity curve."""
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max
    min_dd = drawdown.min()
    return min_dd * 100 if not np.isnan(min_dd) else 0

def export_trades(trades, ticker):
    """Export trade list to a CSV file."""
    if not os.path.exists('test_output'):
        os.makedirs('test_output')
    
    df = pd.DataFrame(trades)
    filename = f"test_output/{ticker}_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    print(f"Trades exported to {filename}")

def plot_results(data, ticker):
    """Plot stock price, Donchian Channels, and buy/sell signals."""
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=(14, 8))
    plt.plot(data.index, data['Close'], label='Close Price', alpha=0.5, color='gray')
    plt.plot(data.index, data['Donchian_Upper'], label='Donchian Upper', color='green', linestyle='--', alpha=0.7)
    plt.plot(data.index, data['Donchian_Lower'], label='Donchian Lower', color='red', linestyle='--', alpha=0.7)
    
    # Long Signals
    plt.scatter(data.index, data['Buy_Signal'], label='Long Entry', marker='^', color='green', s=100)
    plt.scatter(data.index, data['Sell_Signal'], label='Long Exit', marker='v', color='darkgreen', s=100)
    
    # Short Signals
    plt.scatter(data.index, data['Short_Signal'], label='Short Entry', marker='v', color='red', s=100)
    plt.scatter(data.index, data['Cover_Signal'], label='Short Exit', marker='^', color='darkred', s=100)
    
    # Add-on Signals (Pyramiding)
    plt.scatter(data.index, data['Add_Signal'], label='Pyramid Add', marker='+', color='blue', s=50)
    
    plt.title(f"Donchian Channel Backtest for {ticker}")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    if not os.path.exists('test_output'):
        os.makedirs('test_output')
    plot_filename = f"test_output/{ticker}_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(plot_filename)
    print(f"Plot saved to {plot_filename}")
    plt.show()

def print_stats(initial_capital, final_capital, trades, equity_curve):
    """Print backtest statistics."""
    total_return = (final_capital - initial_capital) / initial_capital * 100
    num_trades = len(trades)
    max_dd = calculate_max_drawdown(equity_curve)
    
    if num_trades > 0:
        winning_trades = [t for t in trades if t['profit'] > 0]
        win_rate = len(winning_trades) / num_trades * 100
        avg_profit = sum(t['profit'] for t in trades) / num_trades
    else:
        win_rate = 0
        avg_profit = 0
        
    print("\n--- Backtest Results ---")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Final Capital:   ${final_capital:,.2f}")
    print(f"Total Return:    {total_return:.2f}%")
    print(f"Max Drawdown:    {max_dd:.2f}%")
    print(f"Number of Trades: {num_trades}")
    print(f"Win Rate:        {win_rate:.2f}%")
    print(f"Avg Profit/Trade: ${avg_profit:,.2f}")

    if num_trades > 0:
        df_trades = pd.DataFrame(trades)
        
        # Format dates for display
        display_df = df_trades.copy()
        display_df['entry_date'] = pd.to_datetime(display_df['entry_date']).dt.date
        display_df['exit_date'] = pd.to_datetime(display_df['exit_date']).dt.date
        
        print("\n--- Recent Trades ---")
        cols = ['type', 'entry_date', 'exit_date', 'avg_entry', 'exit_price', 'profit', 'reason']
        print(display_df[cols].tail(10).to_string(index=False))

        print("\n--- Annual Summary ---")
        df_trades['year'] = pd.to_datetime(df_trades['exit_date']).dt.year
        annual_stats = df_trades.groupby('year').agg(
            trades=('profit', 'count'),
            profit=('profit', 'sum')
        )
        print(annual_stats.to_string())
        
    print("------------------------\n")

def run_optimization(data, initial_capital, risk_per_trade, atr_period, d_range, m_range, mode, exit_strategy='trailing'):
    """Perform grid search optimization over Donchian and ATR parameters."""
    results = []
    
    donchian_periods = range(d_range[0], d_range[1] + 1, d_range[2])
    atr_multipliers = np.arange(m_range[0], m_range[1] + 0.01, m_range[2])
    
    total_combinations = len(donchian_periods) * len(atr_multipliers)
    print(f"Running optimization with {total_combinations} combinations...")
    
    for d_period in donchian_periods:
        data_with_ind = calculate_indicators(data, d_period, atr_period)
        
        for m_mult in atr_multipliers:
            final_cap, trades, equity_curve = backtest(data_with_ind.copy(), initial_capital, risk_per_trade, m_mult, mode, exit_strategy=exit_strategy)
            
            if final_cap is not None:
                total_return = (final_cap - initial_capital) / initial_capital * 100
                max_dd = calculate_max_drawdown(equity_curve)
                ratio = total_return / abs(max_dd) if abs(max_dd) > 0.01 else total_return
                
                results.append({
                    'donchian_period': d_period,
                    'atr_multiplier': round(m_mult, 2),
                    'total_return': total_return,
                    'max_drawdown': max_dd,
                    'num_trades': len(trades),
                    'ratio': ratio
                })
                
    return pd.DataFrame(results)

def execute_mode(ticker, initial_capital, risk_per_trade, donchian_period, donchian_exit_period, atr_multiplier, atr_period):
    """Calculate and display trading levels for the next session."""
    data = get_data(ticker, years=1) # 1 year is enough for calculations
    data = calculate_indicators(data, donchian_period, atr_period, donchian_exit_period)
    
    last_row = data.iloc[-1]
    prev_close = last_row['Close']
    atr = last_row['ATR']
    
    long_entry = last_row['Donchian_Upper']
    short_entry = last_row['Donchian_Lower']
    long_exit = last_row['Exit_Lower']
    short_exit = last_row['Exit_Upper']
    
    # Risk calculation
    stop_distance = atr * atr_multiplier
    risk_amount = initial_capital * risk_per_trade
    unit_size = int(risk_amount / stop_distance) if stop_distance > 0 else 0
    
    print(f"\n=== EXECUTION LEVELS FOR {ticker} ===")
    print(f"Current Date:  {data.index[-1].date()}")
    print(f"Latest Close:  ${prev_close:.2f}")
    print(f"ATR ({atr_period}):   ${atr:.2f}")
    print(f"Unit Size:     {unit_size} shares (based on ${initial_capital:,.2f} capital & {risk_per_trade*100}% risk)")
    print("-" * 35)
    print(f"LONG ENTRY:    Above ${long_entry:.2f}")
    print(f"LONG EXIT:     Below ${long_exit:.2f} (Donchian) or Trailing Stop")
    print("-" * 35)
    print(f"SHORT ENTRY:   Below ${short_entry:.2f}")
    print(f"SHORT EXIT:    Above ${short_exit:.2f} (Donchian) or Trailing Stop")
    print("-" * 35)
    print(f"STOP DISTANCE: ${stop_distance:.2f} ({atr_multiplier} * ATR)")
    print(f"PYRAMID STEP:  ${0.5 * atr:.2f} (0.5 * ATR)")
    print("=" * 35)
    print("Note: Entries/Exits should be executed on breakout of these levels.")

def main():
    parser = argparse.ArgumentParser(description="Donchian Channel & ATR Backtester")
    parser.add_argument("--execute", action="store_true", help="Calculate execution levels for the next session")
    parser.add_argument("--plot", action="store_true", help="Enable visualization of results")
    parser.add_argument("--optimize", action="store_true", help="Run parameter optimization")
    parser.add_argument("--ticker", type=str, help="Stock ticker symbol")
    parser.add_argument("--capital", type=float, help="Initial capital")
    parser.add_argument("--risk", type=float, help="Risk per trade % (e.g. 2 for 2%)")
    parser.add_argument("--years", type=int, help="Number of years to backtest")
    parser.add_argument("--d-entry", type=int, help="Donchian entry period")
    parser.add_argument("--d-exit", type=int, help="Donchian exit period")
    parser.add_argument("--atr-mult", type=float, help="ATR multiplier for stop loss")
    parser.add_argument("--mode", choices=['long_only', 'long_short'], default='long_only', 
                        help="Select trade direction mode (default: long_only)")
    parser.add_argument("--exit-strategy", choices=['trailing', 'donchian'], default='trailing',
                        help="Select exit strategy: 'trailing' (ATR trail + Donchian) or 'donchian' (Donchian only)")
    args = parser.parse_args()
    
    print("Welcome to the Donchian Channel & ATR Trading System")
    
    # Ticker
    if args.ticker:
        ticker = args.ticker.upper()
    else:
        ticker = input("Enter Stock Ticker (e.g., AAPL): ").upper()
    
    # Capital
    if args.capital:
        initial_capital = args.capital
    else:
        capital_input = input("Enter Starting Capital (default 10000): ")
        initial_capital = float(capital_input) if capital_input.strip() else 10000.0
        
    # Risk
    if args.risk:
        risk_per_trade = args.risk / 100.0
    else:
        risk_input = input("Enter Risk per Trade % (default 2 for 2%): ")
        risk_per_trade = (float(risk_input) if risk_input.strip() else 2.0) / 100.0
        
    atr_period = 14
    
    # Exit Strategy
    if args.exit_strategy:
        exit_strategy = args.exit_strategy
    else:
        exit_strat_input = input("Enter Exit Strategy (trailing/donchian, default 'trailing'): ").strip().lower()
        exit_strategy = exit_strat_input if exit_strat_input in ['trailing', 'donchian'] else 'trailing'

    if args.execute:
        # Donchian Periods
        if args.d_entry:
            d_entry = args.d_entry
        else:
            d_entry_input = input("Enter Donchian Entry Period (default 20): ")
            d_entry = int(d_entry_input) if d_entry_input.strip() else 20
            
        if args.d_exit:
            d_exit = args.d_exit
        else:
            d_exit_input = input(f"Enter Donchian Exit Period (default {d_entry}): ")
            d_exit = int(d_exit_input) if d_exit_input.strip() else d_entry
            
        # ATR Multiplier
        if args.atr_mult:
            atr_mult = args.atr_mult
        else:
            atr_mult_input = input("Enter ATR Multiplier (default 2.0): ")
            atr_mult = float(atr_mult_input) if atr_mult_input.strip() else 2.0
            
        execute_mode(ticker, initial_capital, risk_per_trade, d_entry, d_exit, atr_mult, atr_period)
        return

    # Backtest Years
    if args.years:
        backtest_years = args.years
    else:
        try:
            years_input = input("Enter Years to Backtest (default 5): ")
            backtest_years = int(years_input) if years_input.strip() else 5
        except ValueError:
            backtest_years = 5
    
    try:
        data = get_data(ticker, years=backtest_years)
        
        if args.optimize:
            print("\n--- Optimization Configuration ---")
            d_start_input = input("Donchian Period Start (default 10): ")
            d_start = int(d_start_input) if d_start_input.strip() else 10
            
            d_end_input = input("Donchian Period End (default 60): ")
            d_end = int(d_end_input) if d_end_input.strip() else 60
            
            d_step_input = input("Donchian Period Step (default 5): ")
            d_step = int(d_step_input) if d_step_input.strip() else 5
            
            m_start_input = input("ATR Multiplier Start (default 1.0): ")
            m_start = float(m_start_input) if m_start_input.strip() else 1.0
            
            m_end_input = input("ATR Multiplier End (default 5.0): ")
            m_end = float(m_end_input) if m_end_input.strip() else 5.0
            
            m_step_input = input("ATR Multiplier Step (default 0.5): ")
            m_step = float(m_step_input) if m_step_input.strip() else 0.5
            
            results_df = run_optimization(data, initial_capital, risk_per_trade, atr_period, 
                                          (d_start, d_end, d_step), (m_start, m_end, m_step), args.mode, exit_strategy)
            
            if not results_df.empty:
                results_df = results_df.sort_values(by='ratio', ascending=False)
                print("\n--- Top 5 Parameter Combinations ---")
                print(results_df.head(5).to_string(index=False))
                
                best = results_df.iloc[0]
                print(f"\nBEST PARAMETERS:")
                print(f"Donchian Period: {best['donchian_period']}")
                print(f"ATR Multiplier:  {best['atr_multiplier']}")
                
                if not os.path.exists('test_output'):
                    os.makedirs('test_output')
                filename = f"test_output/{ticker}_optimization_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                results_df.to_csv(filename, index=False)
                print(f"\nOptimization results saved to {filename}")
        else:
            # Donchian Entry
            if args.d_entry:
                donchian_period = args.d_entry
            else:
                d_entry_input = input("Enter Donchian Entry Period (default 20): ")
                donchian_period = int(d_entry_input) if d_entry_input.strip() else 20
            
            # Donchian Exit
            if args.d_exit:
                donchian_exit_period = args.d_exit
            else:
                d_exit_input = input(f"Enter Donchian Exit Period (default {donchian_period}): ")
                donchian_exit_period = int(d_exit_input) if d_exit_input.strip() else donchian_period
                
            # ATR Multiplier
            if args.atr_mult:
                atr_multiplier = args.atr_mult
            else:
                atr_mult_input = input("Enter ATR Multiplier for Stop Loss (default 2.0): ")
                atr_multiplier = float(atr_mult_input) if atr_mult_input.strip() else 2.0
            
            data_with_ind = calculate_indicators(data, donchian_period, atr_period, donchian_exit_period)
            final_capital, trades, equity_curve = backtest(data_with_ind, initial_capital, risk_per_trade, atr_multiplier, args.mode, exit_strategy=exit_strategy)
            
            if final_capital is not None:
                print_stats(initial_capital, final_capital, trades, equity_curve)
                export_trades(trades, ticker)
                
                if args.plot:
                    plot_results(data_with_ind, ticker)
                
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
