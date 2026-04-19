import requests
import pandas as pd
import time
import csv
import os

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
                data={"chat_id": CHAT_ID, "text": msg},
                timeout=5
            )
        except:
            print("Telegram Error")

# ==============================
# VARIABLES
# ==============================
balance = 5000
trade_open = False
entry_price = 0
current_symbol = ""
trade_type = ""
stop_loss = 0

# ==============================
# COINS
# ==============================
symbols = [
"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
"ADAUSDT","DOGEUSDT","MATICUSDT","DOTUSDT","LTCUSDT"
]

# ==============================
# SETTINGS
# ==============================
VOLUME_MULTIPLIER = 1.5
PRICE_THRESHOLD = 0.002
SL_PERCENT = 0.015
TRAIL_START = 0.02
TRAIL_GAP = 0.02

# ==============================
# SAFE API
# ==============================
def get_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=50"
        res = requests.get(url, timeout=10)
        data = res.json()

        if not isinstance(data, list) or len(data) < 20:
            return None, None

        closes = [float(c[4]) for c in data]
        volumes = [float(c[5]) for c in data]

        return closes, volumes
    except:
        return None, None

# ==============================
# INDICATORS
# ==============================
def indicators(closes, volumes):
    df = pd.DataFrame({"close": closes, "volume": volumes})

    df["EMA20"] = df["close"].ewm(span=20).mean()

    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ==============================
# MAIN LOOP
# ==============================
while True:
    print("\n========= MARKET CHECK =========")

    for symbol in symbols:
        try:
            closes, volumes = get_data(symbol)

            if closes is None:
                print(f"{symbol} ❌ data failed")
                continue

            df = indicators(closes, volumes)

            price = df["close"].iloc[-1]
            prev_price = df["close"].iloc[-2]
            ema = df["EMA20"].iloc[-1]
            rsi = df["RSI"].iloc[-1]

            # 🔥 SUPPORT / RESISTANCE
            support = min(df["close"].iloc[-20:])
            resistance = max(df["close"].iloc[-20:])

            # 🔥 TREND
            trend_up = price > ema
            trend_down = price < ema

            avg_vol = df["volume"].rolling(20).mean().iloc[-1]
            cur_vol = df["volume"].iloc[-1]

            price_change = (price - prev_price) / prev_price

            print(f"{symbol} | Price: {round(price,2)} | RSI: {round(rsi,2)}")

            # ================= BUY =================
            if (
                not trade_open and
                price <= support * 1.02 and
                trend_up and
                rsi < 30 and
                cur_vol >= avg_vol * VOLUME_MULTIPLIER and
                price_change > PRICE_THRESHOLD
            ):
                print("📈 BUY")
                send_telegram(f"📈 BUY {symbol} @ {price}")

                trade_open = True
                entry_price = price
                current_symbol = symbol
                trade_type = "long"
                stop_loss = price * (1 - SL_PERCENT)

            # ================= SHORT =================
            elif (
                not trade_open and
                price >= resistance * 0.98 and
                trend_down and
                rsi > 70 and
                cur_vol >= avg_vol * VOLUME_MULTIPLIER and
                price_change < -PRICE_THRESHOLD
            ):
                print("📉 SHORT")
                send_telegram(f"📉 SHORT {symbol} @ {price}")

                trade_open = True
                entry_price = price
                current_symbol = symbol
                trade_type = "short"
                stop_loss = price * (1 + SL_PERCENT)

            # ================= EXIT =================
            elif trade_open and symbol == current_symbol:

                if trade_type == "long":
                    profit_pct = (price - entry_price) / entry_price

                    if profit_pct >= TRAIL_START:
                        new_sl = price * (1 - TRAIL_GAP)
                        if new_sl > stop_loss:
                            stop_loss = new_sl

                    if price <= stop_loss:
                        profit = price - entry_price
                        balance += profit

                        send_telegram(f"🔴 EXIT LONG {symbol} Profit: {round(profit,2)}")
                        trade_open = False

                elif trade_type == "short":
                    profit_pct = (entry_price - price) / entry_price

                    if profit_pct >= TRAIL_START:
                        new_sl = price * (1 + TRAIL_GAP)
                        if new_sl < stop_loss:
                            stop_loss = new_sl

                    if price >= stop_loss:
                        profit = entry_price - price
                        balance += profit

                        send_telegram(f"🔴 EXIT SHORT {symbol} Profit: {round(profit,2)}")
                        trade_open = False

            time.sleep(1)  # 🔥 avoid rate limit

        except Exception as e:
            print(f"{symbol} ERROR:", e)

    print("Balance:", balance)
    time.sleep(60)
