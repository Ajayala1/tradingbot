import requests
import pandas as pd
import time
import csv

# ==============================
# 🔐 TELEGRAM SETTINGS
# ==============================
TELEGRAM_TOKEN = "8755159897:AAGgtPESQOJG5I48ECf72-cbIPoC60dCQZs"
CHAT_ID = "1037106335"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }
    try:
        requests.post(url, data=data)
    except:
        print("Telegram Error")

# ==============================
# ⚙️ BOT VARIABLES
# ==============================
balance = 5000
trade_open = False
entry_price = 0
current_symbol = ""
trade_type = ""
stop_loss = 0

# ==============================
# 🔥 COINS (50)
# ==============================
all_symbols = [
"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","MATICUSDT","DOTUSDT","LTCUSDT",
"TRXUSDT","AVAXUSDT","SHIBUSDT","ATOMUSDT","LINKUSDT","NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT",
"INJUSDT","SUIUSDT","FILUSDT","AAVEUSDT","EOSUSDT","XTZUSDT","THETAUSDT","ALGOUSDT","VETUSDT","ICPUSDT",
"FLOWUSDT","CHZUSDT","EGLDUSDT","KAVAUSDT","FTMUSDT","HBARUSDT","GRTUSDT","MANAUSDT","SANDUSDT","AXSUSDT",
"IMXUSDT","RNDRUSDT","PEPEUSDT","BONKUSDT","WLDUSDT","TIAUSDT","SEIUSDT","DYDXUSDT","JASMYUSDT","ENSUSDT"
]

priority_symbols = ["BTCUSDT","ETHUSDT","BNBUSDT"]

batch_size = 10
current_index = 0

# ==============================
# 🔥 SETTINGS
# ==============================
VOLUME_MULTIPLIER = 1.5
PRICE_THRESHOLD = 0.002

SL_PERCENT = 0.015
TRAIL_START = 0.02
TRAIL_GAP = 0.02

# ==============================
# 🔁 ROTATION FUNCTION
# ==============================
def get_active_symbols():
    global current_index

    start = current_index
    end = start + batch_size

    rotating = all_symbols[start:end]

    if end >= len(all_symbols):
        current_index = 0
    else:
        current_index += batch_size

    return priority_symbols + rotating

# ==============================
# 📊 DATA FUNCTIONS
# ==============================
def get_data(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=50"
    data = requests.get(url).json()

    closes = [float(c[4]) for c in data]
    volumes = [float(c[5]) for c in data]

    return closes, volumes

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
# 🔄 MAIN LOOP
# ==============================
while True:
    print("\n================ MARKET CHECK ================")

    active_symbols = get_active_symbols()
    print("Active Coins:", active_symbols)

    for symbol in active_symbols:
        try:
            # 4H support/resistance
            closes_4h, _ = get_data(symbol, "4h")
            support = min(closes_4h[-20:])
            resistance = max(closes_4h[-20:])

            # 1H trend
            closes_1h, vol_1h = get_data(symbol, "1h")
            df_1h = indicators(closes_1h, vol_1h)

            trend_up = df_1h["close"].iloc[-1] > df_1h["EMA20"].iloc[-1]
            trend_down = df_1h["close"].iloc[-1] < df_1h["EMA20"].iloc[-1]

            # 15m entry
            closes_15m, vol_15m = get_data(symbol, "15m")
            df_15m = indicators(closes_15m, vol_15m)

            price = df_15m["close"].iloc[-1]
            prev_price = df_15m["close"].iloc[-2]
            ema = df_15m["EMA20"].iloc[-1]
            rsi = df_15m["RSI"].iloc[-1]

            avg_vol = df_15m["volume"].rolling(20).mean().iloc[-1]
            cur_vol = df_15m["volume"].iloc[-1]

            price_change = (price - prev_price) / prev_price

            trend = "UP 📈" if trend_up else "DOWN 📉"
            volume_status = "HIGH 🔥" if cur_vol >= avg_vol * VOLUME_MULTIPLIER else "LOW"

            # ================= DISPLAY =================
            print("\n--------------------------------")
            print(f"COIN: {symbol}")
            print(f"Price: {round(price,2)}")
            print(f"Support: {round(support,2)}")
            print(f"Resistance: {round(resistance,2)}")
            print(f"Trend: {trend}")
            print(f"EMA: {round(ema,2)}")
            print(f"RSI: {round(rsi,2)}")
            print(f"Volume: {volume_status}")
            print(f"Price Change: {round(price_change*100,2)}%")
            print(f"Current Trade: {trade_type if trade_open else 'No Trade'}")
            print(f"Stop Loss: {round(stop_loss,2)}")

            # ================= LONG ENTRY =================
            if (
                not trade_open and
                price <= support * 1.02 and
                trend_up and
                price > ema and
                rsi < 30 and
                cur_vol >= avg_vol * VOLUME_MULTIPLIER and
                price_change > PRICE_THRESHOLD
            ):
                print("Decision: 📈 BUY")

                send_telegram(f"📈 BUY {symbol}\nPrice: {price}\nSupport: {support}\nTrend: {trend}\nRSI: {round(rsi,2)}")

                trade_open = True
                entry_price = price
                current_symbol = symbol
                trade_type = "long"
                stop_loss = price * (1 - SL_PERCENT)
                break

            # ================= SHORT ENTRY =================
            elif (
                not trade_open and
                price >= resistance * 0.98 and
                trend_down and
                price < ema and
                rsi > 70 and
                cur_vol >= avg_vol * VOLUME_MULTIPLIER and
                price_change < -PRICE_THRESHOLD
            ):
                print("Decision: 📉 SHORT SELL")

                send_telegram(f"📉 SHORT {symbol}\nPrice: {price}\nResistance: {resistance}\nTrend: {trend}\nRSI: {round(rsi,2)}")

                trade_open = True
                entry_price = price
                current_symbol = symbol
                trade_type = "short"
                stop_loss = price * (1 + SL_PERCENT)
                break

            # ================= TRAILING + EXIT =================
            elif trade_open and symbol == current_symbol:

                if trade_type == "long":
                    profit_pct = (price - entry_price) / entry_price

                    if profit_pct >= TRAIL_START:
                        new_sl = price * (1 - TRAIL_GAP)
                        if new_sl > stop_loss:
                            stop_loss = new_sl

                    if price <= stop_loss:
                        print("Decision: EXIT 🔴")
                        profit = price - entry_price
                        balance += profit

                        send_telegram(f"🔴 EXIT {symbol}\nType: LONG\nEntry: {entry_price}\nExit: {price}\nProfit: {round(profit,2)}\nBalance: {round(balance,2)}")

                        with open("trades.csv", "a", newline="") as f:
                            csv.writer(f).writerow([symbol, "LONG", entry_price, price, profit])

                        trade_open = False

                elif trade_type == "short":
                    profit_pct = (entry_price - price) / entry_price

                    if profit_pct >= TRAIL_START:
                        new_sl = price * (1 + TRAIL_GAP)
                        if new_sl < stop_loss:
                            stop_loss = new_sl

                    if price >= stop_loss:
                        print("Decision: EXIT 🔴")
                        profit = entry_price - price
                        balance += profit

                        send_telegram(f"🔴 EXIT {symbol}\nType: SHORT\nEntry: {entry_price}\nExit: {price}\nProfit: {round(profit,2)}\nBalance: {round(balance,2)}")

                        with open("trades.csv", "a", newline="") as f:
                            csv.writer(f).writerow([symbol, "SHORT", entry_price, price, profit])

                        trade_open = False

            else:
                print("Decision: SKIP ⏸️")

        except Exception as e:
            print("Error:", e)

    print("\nBalance:", balance)
    time.sleep(60)