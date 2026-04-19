import requests
import pandas as pd
import time
import csv
import os
from flask import Flask
from threading import Thread

# ==============================
# KEEP ALIVE
# ==============================
app = Flask('')

@app.route('/')
def home():
    return "Bot Running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# ==============================
# 🔐 TELEGRAM SETTINGS
# ==============================
TELEGRAM_TOKEN = "8755159897:AAGgtPESQOJG5I48ECf72-cbIPoC60dCQZs"
CHAT_ID = "1037106335"

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg}
            )
        except:
            print("Telegram error")

# ==============================
# COINS (CoinGecko IDs)
# ==============================
coins = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "binancecoin": "BNB",
    "solana": "SOL",
    "ripple": "XRP"
}

# ==============================
# INDICATORS
# ==============================
def indicators(prices):
    df = pd.DataFrame(prices, columns=["price"])

    df["EMA20"] = df["price"].ewm(span=20).mean()

    delta = df["price"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ==============================
# FETCH DATA (CoinGecko)
# ==============================
def get_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=1&interval=minute"
        data = requests.get(url, timeout=10).json()

        prices = [p[1] for p in data["prices"]]

        if len(prices) < 30:
            return None

        return prices[-50:]  # last 50 points

    except:
        return None

# ==============================
# VARIABLES
# ==============================
balance = 5000
trade_open = False
entry_price = 0
current_coin = ""
trade_type = ""
stop_loss = 0

# SETTINGS
SL_PERCENT = 0.015
TRAIL_START = 0.02
TRAIL_GAP = 0.02

# ==============================
# START
# ==============================
keep_alive()

# ==============================
# MAIN LOOP
# ==============================
while True:
    print("\n===== MARKET CHECK =====")

    for coin_id, symbol in coins.items():
        try:
            prices = get_data(coin_id)

            if prices is None:
                print(f"{symbol} ❌ data failed")
                continue

            df = indicators(prices)

            price = df["price"].iloc[-1]
            ema = df["EMA20"].iloc[-1]
            rsi = df["RSI"].iloc[-1]

            support = min(df["price"].iloc[-20:])
            resistance = max(df["price"].iloc[-20:])

            print(f"{symbol} | Price: {round(price,2)} | RSI: {round(rsi,2)}")

            # BUY
            if not trade_open and price <= support * 1.02 and price > ema and rsi < 30:
                print("📈 BUY")
                send_telegram(f"📈 BUY {symbol} @ {price}")

                trade_open = True
                entry_price = price
                current_coin = symbol
                trade_type = "long"
                stop_loss = price * (1 - SL_PERCENT)

            # SHORT
            elif not trade_open and price >= resistance * 0.98 and price < ema and rsi > 70:
                print("📉 SHORT")
                send_telegram(f"📉 SHORT {symbol} @ {price}")

                trade_open = True
                entry_price = price
                current_coin = symbol
                trade_type = "short"
                stop_loss = price * (1 + SL_PERCENT)

            # EXIT
            elif trade_open and symbol == current_coin:

                if trade_type == "long":
                    profit_pct = (price - entry_price) / entry_price

                    if profit_pct >= TRAIL_START:
                        stop_loss = max(stop_loss, price * (1 - TRAIL_GAP))

                    if price <= stop_loss:
                        profit = price - entry_price
                        balance += profit
                        send_telegram(f"🔴 EXIT LONG {symbol} Profit: {round(profit,2)}")
                        trade_open = False

                elif trade_type == "short":
                    profit_pct = (entry_price - price) / entry_price

                    if profit_pct >= TRAIL_START:
                        stop_loss = min(stop_loss, price * (1 + TRAIL_GAP))

                    if price >= stop_loss:
                        profit = entry_price - price
                        balance += profit
                        send_telegram(f"🔴 EXIT SHORT {symbol} Profit: {round(profit,2)}")
                        trade_open = False

            time.sleep(2)

        except Exception as e:
            print(symbol, "ERROR:", e)

    print("Balance:", balance)
    time.sleep(60)
