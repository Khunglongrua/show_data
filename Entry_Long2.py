import os
import pandas as pd
import ccxt
import requests
import time
from ta.momentum import RSIIndicator
from ta.trend import CCIIndicator, EMAIndicator

# Cài đặt Telegram Bot
TELEGRAM_BOT_TOKEN = "6462681730:AAE4_9qV7m04EOB3NfGGFXyksuuWKnftUk0"
TELEGRAM_CHAT_ID = "-4770512637"

# Thiết lập tham số
PRICE_DIFFERENCE_THRESHOLD = 2  # Ngưỡng chênh lệch giá (phần trăm)
INTERVAL = '1m'  # Lấy dữ liệu nến 1 phút và chuyển đổi thành nến 15 phút
exchange = ccxt.binance({'options': {'defaultType': 'spot'}})

# Gửi tin nhắn tới Telegram
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"[LỖI] Gửi tin nhắn thất bại: {response.status_code}")
    except Exception as e:
        print(f"[LỖI] Lỗi khi gửi báo cáo: {e}")

# Lấy top 100 cặp USDT Spot dựa trên khối lượng giao dịch
def get_top_100_usdt_spot_coins():
    try:
        tickers = exchange.fetch_tickers()
        df = pd.DataFrame([tickers[symbol] for symbol in tickers if symbol.endswith('/USDT')])
        stablecoins = ["USDC/USDT", "BUSD/USDT", "TUSD/USDT", "DAI/USDT", "FDUSD/USDT", "USDP/USDT", "GUSD/USDT"]
        df = df[~df['symbol'].isin(stablecoins)].nlargest(100, 'quoteVolume')
        return df['symbol'].tolist()
    except Exception as e:
        print(f"[LỖI] Lỗi khi lấy danh sách cặp: {e}")
        return []

# Lấy dữ liệu OHLCV từ Binance
def get_binance_klines(symbol, timeframe='1m', limit=500):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        print(f"[LỖI] Lỗi khi lấy dữ liệu {symbol}: {e}")
        return pd.DataFrame()

# Chuyển đổi nến 1 phút thành nến 15 phút
def convert_to_15m_candles(df):
    df.set_index('timestamp', inplace=True)
    df_15m = df.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    df_15m['ema21_volume'] = df_15m['volume'].ewm(span=21, adjust=False).mean()
    return df_15m

# Tính các chỉ báo kỹ thuật
def calculate_indicators(df):
    df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
    df['CCI'] = CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=20).cci()
    df['EMA50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
    return df

# Kiểm tra và gửi tín hiệu tới Telegram
def check_and_send_signals(symbol, df):
    latest_volume = df['volume'].iloc[-1]
    latest_ema21_volume = df['ema21_volume'].iloc[-1]
    volume_ratio = round(latest_volume / latest_ema21_volume, 2)

    if 1 < volume_ratio < 2.5:
        latest_close = df['close'].iloc[-1]
        previous_close = df['close'].iloc[-2]
        price_difference = round(((latest_close - previous_close) / previous_close) * 100, 2)
        latest_rsi = round(df['RSI'].iloc[-1], 2)
        latest_cci = round(df['CCI'].iloc[-1], 2)

        if abs(price_difference) > PRICE_DIFFERENCE_THRESHOLD:
            direction = "UP" if price_difference > 0 else "DOWN"
            # Thông báo ngắn gọn với chênh lệch giá đúng dấu và làm tròn 2 số
            message = (
                f"{symbol} = {direction} {price_difference:.2f}% | RSI: {latest_rsi:.2f}, CCI: {latest_cci:.2f} | Vol: {volume_ratio:.2f}x"
            )
            send_to_telegram(message)

# Xử lý dữ liệu cho top 100 cặp USDT Spot
def process_top_100_usdt_spot_coins():
    top_100_coins = get_top_100_usdt_spot_coins()
    if not top_100_coins:
        return

    for symbol in top_100_coins:
        df = get_binance_klines(symbol)
        if df.empty:
            continue

        df_15m = convert_to_15m_candles(df)
        df_15m = calculate_indicators(df_15m)
        check_and_send_signals(symbol, df_15m)
        time.sleep(0.5)

if __name__ == "__main__":
    process_top_100_usdt_spot_coins()

