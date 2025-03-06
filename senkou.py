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

# Discord Webhook URL (thay URL này bằng webhook của bạn)
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1325976304029532252/qY1bNguDfHqy4qBjCzclrfdhFZpCLOJvOzvvDw4U1bPkOPCse9kiRud8rZsD1y88ANwE'

# Lấy 200 cặp có khối lượng giao dịch cao nhất trên Futures
# Lấy 200 cặp có khối lượng giao dịch cao nhất trên Futures
def fetch_top_symbols(limit=200):
    try:
        markets = binance.load_markets()
    except Exception as e:
        print(f"Lỗi khi tải dữ liệu thị trường: {e}")
        return []

    # Lấy tất cả ticker một lần để tránh gọi API nhiều lần
    try:
        tickers = binance.fetch_tickers()
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu ticker: {e}")
        return []

    volume_data = []

    for symbol in markets:
        # Điều kiện kiểm tra symbol hợp lệ: Kết thúc bằng USDT và không chứa :USDT
        if symbol.endswith('USDT') and ':USDT' not in symbol:
            try:
                ticker = tickers.get(symbol)
                if ticker and ticker['quoteVolume'] is not None:
                    volume_data.append((symbol, ticker['quoteVolume']))
            except Exception as e:
                print(f"Lỗi khi lấy dữ liệu {symbol}: {e}")
        else:
            print(f"⚠️ Symbol không hợp lệ đã bị loại: {symbol}")

    # Sắp xếp các cặp theo khối lượng giao dịch giảm dần và lấy top 200
    top_symbols = sorted(volume_data, key=lambda x: x[1], reverse=True)[:limit]
    return [symbol[0] for symbol in top_symbols]  # Trả về danh sách symbol


# Parameters for Ichimoku
timeframe = '5m'  # Khung thời gian 15 phút
limit_candles = 120  # Số lượng nến để tính Ichimoku (tối thiểu 120 nến)
threshold = 1  # Ngưỡng chênh lệch ±5%

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

# Function to send message to Discord
def send_discord_message(message):
    data = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            print("Message sent to Discord successfully!")
        else:
            print(f"Failed to send message to Discord: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn đến Discord: {e}")

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

    sent_symbols = []

    # Trong vòng lặp:
    if delta_abs >= threshold and symbol not in sent_symbols:
        message = f"**Token vượt quá ±{threshold}%:**\n- {symbol}: Δ = {delta:.2f}%"
        send_discord_message(message)
        sent_symbols.append(symbol)  # Lưu symbol đã gửi
        qualified_symbols.append(symbol)  # Thêm symbol vào danh sách thoả điều kiện

        # Nghỉ 0.2 giây giữa các yêu cầu để tránh bị chặn IP
        time.sleep(0.2)

print("\n--- Tất cả các cặp đã được xử lý ---")
print(f"--- Tổng cộng có {len(qualified_symbols)} cặp thoả điều kiện ---")

# Gửi thông báo nếu có cặp thoả điều kiện
if qualified_symbols:
    print("Các cặp thoả điều kiện:")
    for sym in qualified_symbols:
        print(f"- {sym}")
else:
    print("Không có cặp nào thoả điều kiện.")
