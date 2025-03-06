import os
import pandas as pd
import ccxt
import requests
import time
from discord_webhook import DiscordWebhook
from datetime import datetime

# Thiết lập tham số
PRICE_DIFFERENCE_THRESHOLD = 1.5  # Ngưỡng chênh lệch giá (phần trăm)
INTERVAL = '5m'  # Tham số khung thời gian (có thể là '15m', '1h', '4h', v.v.)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1345622429501886475/TcA67eYtH9Z-U65XGi33QXO_ztuavjpHLwI3-0lUbS9ubK1Ljkm-gHphq6J_EDSpwTSj"

# Thiết lập sàn giao dịch Binance
exchange = ccxt.binance()

def get_top_200_usdt_coins():
    """Lấy danh sách 200 cặp USDT có khối lượng giao dịch cao nhất."""
    tickers = exchange.fetch_tickers()
    df = pd.DataFrame([tickers[symbol] for symbol in tickers])
    df = df[df['symbol'].str.endswith('/USDT')]
    stablecoins = ["USDC/USDT", "BUSD/USDT", "TUSD/USDT", "DAI/USDT", "FDUSD/USDT", "USDP/USDT", "GUSD/USDT"]
    df = df[~df['symbol'].isin(stablecoins)]
    df = df.nlargest(200, 'quoteVolume')
    return df['symbol'].tolist()

def send_to_discord(message):
    """Gửi tin nhắn tới Discord."""
    try:
        webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, content=message)
        response = webhook.execute()
        if response.status_code == 200:
            print("Đã gửi báo cáo thành công đến Discord.")
        else:
            print(f"Đã có lỗi khi gửi báo cáo đến Discord: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gửi báo cáo tới Discord: {e}")

def get_binance_klines(symbol, timeframe=INTERVAL, limit=100):
    """Lấy dữ liệu OHLCV từ Binance."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        print(f"Lỗi lấy dữ liệu {symbol}: {e}")
        return None

# Hàm tính EMA
def calculate_ema(df, column='close', period=50):
    """Tính toán EMA cho một cột cụ thể."""
    return df[column].ewm(span=period, adjust=False).mean()

def process_top_200_usdt_coins():
    """Phân tích 200 cặp USDT có khối lượng giao dịch tốt nhất."""
    symbols = get_top_200_usdt_coins()
    print(f"\n--- Đang phân tích top 200 cặp USDT với khung thời gian {INTERVAL} ---")

    suitable_symbols = []  # Danh sách các cặp thỏa mãn điều kiện

    if not symbols:
        print("[LỖI] Không lấy được bất kỳ cặp giao dịch nào!")
        return

    for symbol in symbols:
        df = get_binance_klines(symbol, INTERVAL)
        if df is None or df.empty:
            continue

        # Tính toán EMA50 và EMA21 của volume
        df['ema50'] = calculate_ema(df, column='close', period=50)
        df['ema21_volume'] = calculate_ema(df, column='volume', period=21)

        latest_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]

        price_difference = ((latest_candle['close'] - latest_candle['open']) / latest_candle['open']) * 100

        # Điều kiện mới: volume > 100% so với ema21_volume
        if latest_candle['volume'] > 2 * latest_candle['ema21_volume'] and abs(price_difference) > PRICE_DIFFERENCE_THRESHOLD:
            # Tính tỷ lệ tăng trưởng của volume so với ema21_volume
            volume_ratio = ((latest_candle['volume'] - latest_candle['ema21_volume']) / latest_candle['ema21_volume']) * 100

            # Điều kiện mới: Xu hướng UP/DOWN dựa trên giá đóng và EMA50
            ema50 = latest_candle['ema50']
            if latest_candle['close'] > ema50:
                trend = "UP"
            elif latest_candle['close'] < ema50:
                trend = "DOWN"
            else:
                continue  # Bỏ qua nếu giá đóng = EMA50 (ít khi xảy ra)

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = f"📅 Thời gian: {current_time}\n" \
                     f"📊 Cặp giao dịch: {symbol}\n" \
                     f"🔹 Chênh lệch giá: {price_difference:.2f}%\n" \
                     f"🔹 Tăng trưởng khối lượng: {volume_ratio:.2f}% so với EMA21\n" \
                     f"📈 EMA50: {ema50:.4f}\n" \
                     f"🔹 Xu hướng: {trend}"
            print(result)
            send_to_discord(result)
            suitable_symbols.append(symbol)  # Thêm symbol thỏa mãn điều kiện vào danh sách

        time.sleep(0.5)  # Nghỉ 0.5 giây giữa các lần phân tích cặp

    print("\n--- Kết quả: Các cặp giao dịch thỏa mãn điều kiện ---")
    if suitable_symbols:
        for sym in suitable_symbols:
            print(f"- {sym}")
    else:
        print("Không có cặp nào thỏa mãn điều kiện.")

if __name__ == "__main__":
    process_top_200_usdt_coins()




