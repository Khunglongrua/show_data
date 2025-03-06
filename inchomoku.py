import os
import ccxt
import pandas as pd
import requests
import time

# Khởi tạo đối tượng Binance Futures
binance = ccxt.binance({
    'options': {
        'defaultType': 'future'  # Sử dụng thị trường Futures
    }
})

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "6383838849:AAFkLDa6LJy_MoTl7gE15OPApeVllcWqekY"
TELEGRAM_CHAT_ID = "5912075421"  # Thay bằng chat ID của bạn

# Lấy 200 cặp có khối lượng giao dịch cao nhất trên Futures
def fetch_top_symbols(limit=200):
    markets = binance.load_markets()
    volume_data = []

    for symbol in markets:
        # Thêm điều kiện kiểm tra symbol hợp lệ
        if '/USDT' in symbol and 'PERP' in symbol and not symbol.endswith(':USDT'):
            try:
                ticker = binance.fetch_ticker(symbol)
                if ticker['quoteVolume'] is not None:
                    volume_data.append((symbol, ticker['quoteVolume']))
            except Exception as e:
                print(f"Lỗi khi lấy dữ liệu {symbol}: {e}")

    # Sắp xếp các cặp theo khối lượng giao dịch giảm dần và lấy top 200
    top_symbols = sorted(volume_data, key=lambda x: x[1], reverse=True)[:limit]
    return list(set([symbol[0] for symbol in top_symbols]))  # Loại bỏ trùng lặp


# Parameters for Ichimoku
timeframe = '15m'  # Khung thời gian 15 phút
limit_candles = 120  # Số lượng nến để tính Ichimoku (tối thiểu 120 nến)
threshold = 2  # Ngưỡng chênh lệch ±3%

# Function to fetch candles data using ccxt
def get_candles(symbol, timeframe, limit=120):
    try:
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu nến cho {symbol}: {e}")
        return None

# Function to send message to Telegram
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Đã gửi báo cáo thành công đến Telegram.")
        else:
            print(f"Đã có lỗi khi gửi báo cáo đến Telegram: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gửi báo cáo tới Telegram: {e}")

# Lấy danh sách 200 cặp có khối lượng giao dịch tốt nhất
symbols = fetch_top_symbols()

# Danh sách để lưu các cặp thoả điều kiện
qualified_symbols = []

# Iterate through each symbol and calculate Ichimoku Cloud
for symbol in symbols:
    print(f"\n--- Đang xử lý {symbol} ---")
    df = get_candles(symbol, timeframe, limit=limit_candles)
    if df is None or df.empty:
        continue  # Bỏ qua nếu không có dữ liệu

    # Tính Ichimoku Cloud
    high9 = df['high'].rolling(window=9).max()
    low9 = df['low'].rolling(window=9).min()
    tenkan_sen = (high9 + low9) / 2

    high26 = df['high'].rolling(window=26).max()
    low26 = df['low'].rolling(window=26).min()
    kijun_sen = (high26 + low26) / 2

    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    high52 = df['high'].rolling(window=52).max()
    low52 = df['low'].rolling(window=52).min()
    senkou_span_b = ((high52 + low52) / 2).shift(26)

    # Drop NaN values after calculation
    df = df.dropna()

    # Get last values
    senkou_a = senkou_span_a.iloc[-1]
    senkou_b = senkou_span_b.iloc[-1]
    current_price = df['close'].iloc[-1]

    # Calculate delta
    delta = round((senkou_a - senkou_b) / current_price * 100, 2)
    delta_abs = abs(delta)
    print(f"Delta cho {symbol}: {delta:.2f}%")

    sent_symbols = []  # Lưu các symbol đã gửi

    # Check if delta exceeds threshold
    if delta_abs >= threshold and symbol not in sent_symbols:
        message = f"📊 *Token vượt quá ±{threshold}%:*\n- {symbol}: Δ = {delta:.2f}%"
        print(message)  # Print ngay khi tìm thấy
        send_to_telegram(message)  # Gửi ngay qua Telegram
        sent_symbols.append(symbol)  # Lưu symbol đã gửi
        qualified_symbols.append(symbol)  # Lưu vào danh sách thoả điều kiện


    # Nghỉ 0.2 giây giữa các yêu cầu để tránh bị chặn IP
    time.sleep(0.2)

print("\n--- Tất cả các cặp đã được xử lý ---")
print(f"--- Tổng cộng có {len(qualified_symbols)} cặp thoả điều kiện ---")

if qualified_symbols:
    print("Các cặp thoả điều kiện:")
    for sym in qualified_symbols:
        print(f"- {sym}")
else:
    print("Không có cặp nào thoả điều kiện.")

