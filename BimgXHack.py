import tkinter as tk
from tkinter import ttk, messagebox
from ttkthemes import ThemedTk
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor

class CryptoAnalyzer:
    def __init__(self):
        self.tickers = []
        self.index = 0

    def update_data(self):
        if not self.tickers:
            output_text.insert(tk.END, "No tickers provided.\n")
            return
        
        ticker = self.tickers[self.index]
        output_text.insert(tk.END, f"Analyzing {ticker}...\n")

        data = yf.download(ticker, period='5d', interval='15m')
        
        if data.empty:
            output_text.insert(tk.END, "No data available for this ticker.\n")
            self.next_ticker()
            return

        data.fillna(data.mean(), inplace=True)
        
        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['Buy_Signal'] = np.where((data['MA5'] > data['MA20']), 1, 0)
        data['Sell_Signal'] = np.where((data['MA5'] < data['MA20']), 1, 0)
        data['std_dev'] = data['Close'].rolling(window=30).std()
        data['Stop_Loss'] = data['Close'] - 2 * data['std_dev']
        data['Take_Profit'] = data['Close'] + 2 * data['std_dev']
        data['RSI'] = ta.momentum.rsi(data['Close'], window=24)

        self.detect_price_jump(data)
        self.detect_whale_activity(data)
        self.determine_entry_points(data)

        X = data[['Open', 'High', 'Low', 'Volume', 'RSI']]
        y = data['Close']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        model = DecisionTreeRegressor()
        model.fit(X_train, y_train)

        last_row = data.iloc[-1]
        output = ""

        if last_row['Buy_Signal'] == 1:
            output += "LONG"
            buy_price = last_row['Close']  # Price to enter a long position
            output += f"BUY at: {buy_price:.2f}\n"
            if (last_row['Take_Profit'] >= last_row['Close'] * 2):
                self.show_notification(ticker, "Take Profit can be reached at 100%.")
        elif last_row['Sell_Signal'] == 1:
            output += "SHORT"
            sell_price = last_row['Close']  # Price to enter a short position
            output += f"SELL at: {sell_price:.2f}\n"
        else:
            output += "NO SIGNAL"

        output += f"STOP LOSS: {last_row['Stop_Loss']:.2f}\n"
        output += f"TAKE PROFIT: {last_row['Take_Profit']:.2f}\n"
        output += f"RSI: {last_row['RSI']:.2f}\n"

        output_text.insert(tk.END, output + '\n')
        
        self.next_ticker()

    def determine_entry_points(self, data):
        last_row = data.iloc[-1]
        entry_point = None
        
        # Suggesting entry point based on Buy/Sell signal and RSI
        if last_row['Buy_Signal'] == 1 and last_row['RSI'] < 30:
            entry_point = "Consider entering a LONG position."
        elif last_row['Sell_Signal'] == 1 and last_row['RSI'] > 70:
            entry_point = "Consider entering a SHORT position."

        if entry_point:
            output_text.insert(tk.END, f"ENTRY POINT: {entry_point}\n")

    def detect_price_jump(self, data):
        data['Price_Change'] = data['Close'].pct_change(periods=4)  # Change over the last hour (4 * 15 mins)
        recent_jump = data['Price_Change'].iloc[-1]
        
        if recent_jump > 0.02:  # Example threshold for a 2% rise
            self.show_notification("Price Jump Detected", f"Significant price increase for {self.tickers[self.index]}: {recent_jump:.2%}")
        elif recent_jump < -0.02:  # A significant drop
            self.show_notification("Price Drop Detected", f"Significant price decrease for {self.tickers[self.index]}: {recent_jump:.2%}")

    def detect_whale_activity(self, data):
        recent_volume = data['Volume'].iloc[-1]
        average_volume = data['Volume'].rolling(window=5).mean().iloc[-1]  # Average volume of the last 5 periods
        
        if recent_volume > 2 * average_volume:  # If the recent volume is more than double the average
            self.show_notification("Whale Activity Detected", f"Significant volume spike for {self.tickers[self.index]}: {recent_volume}")

    def show_notification(self, title, message):
        messagebox.showinfo(title, message)

    def next_ticker(self):
        self.index = (self.index + 1) % len(self.tickers)
        self.schedule_update()

    def schedule_update(self):
        root.after(20000, self.update_data)

def start_analysis():
    tickers_input = ticker_entry.get().strip().split(",")
    analyzer.tickers = [ticker.strip() for ticker in tickers_input if ticker.strip()]
    analyzer.index = 0
    output_text.delete(1.0, tk.END)
    analyzer.update_data()
    
    def wrong_signal():
     if analyzer.index > 0:
        analyzer.tickers.pop(analyzer.index-1)
        analyzer.index -= 1
        output_text.insert(tk.END, f"Incorrect signal detected for {analyzer.tickers[analyzer.index]}. Excluding from further analysis.\n")
     else:
        output_text.insert(tk.END, f"No tickers to remove.\n")
        
def next_ticker():
    if analyzer.index < len(analyzer.tickers):
        analyzer.schedule_update()
    else:
        output_text.insert(tk.END, "All tickers analyzed.\n")

def schedule_update():
    if analyzer.index < len(analyzer.tickers):
        root.after(20000, analyzer.update_data)

root = ThemedTk(theme="equilux")
root.title("Crypto Analysis App")
root.geometry("800x600")

style = {'font': ('Arial', 14)}

ticker_label = ttk.Label(root, text="Enter tickers (comma separated):", font=style['font'])
ticker_label.pack(padx=10, pady=10)

ticker_entry = ttk.Entry(root, font=style['font'])
ticker_entry.pack(padx=10, pady=10)

button = ttk.Button(root, text="Start Analysis", command=start_analysis)
button.pack(padx=10, pady=10)

output_text = tk.Text(root, font=style['font'], bg='light grey', fg='black')
output_text.pack(padx=10, pady=10)

analyzer = CryptoAnalyzer()
root.mainloop()
