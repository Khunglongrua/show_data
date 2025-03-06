import ccxt
import pandas as pd
import requests  # Dùng để gửi tín hiệu qua Telegram
from ta.trend import IchimokuIndicator

# 🌟 Thông tin Telegram Bot
API_TOKEN = '6796631082:AAHc9aKXaL-u3IMh-X8xFD8oASR7KHYk03Q'  # Thay YOUR_TELEGRAM_API_TOKEN bằng token của bạn
CHAT_ID = '-4748582015'  # Thay YOUR_CHAT_ID bằng chat ID của bạn

# 🌟 Cài đặt chung
interval = '15m'         # ⏰ Dễ dàng điều chỉnh khung thời gian
limit_candles = 120      # Số lượng nến cần lấy

# Kết nối Binance API (Spot)
binance = ccxt.binance({
    'options': {'defaultType': 'spot'}  # Sử dụng thị trường Spot
})

# 🌟 Hàm gửi tin nhắn Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, json=payload)

# Lấy 100 cặp USDT có khối lượng giao dịch lớn nhất trên Spot
def get_top_100_usdt_pairs():
    markets = binance.fetch_tickers()
    usdt_pairs = [symbol for symbol in markets if "/USDT" in symbol]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: markets[x]['quoteVolume'], reverse=True)
    return sorted_pairs[:100]

# Lấy dữ liệu nến
def get_candles(symbol):
    ohlcv = binance.fetch_ohlcv(symbol, timeframe=interval, limit=limit_candles)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# Tính toán Ichimoku
def calculate_ichimoku(df):
    ichimoku = IchimokuIndicator(high=df['high'], low=df['low'], window1=9, window2=26, window3=52)
    df['tenkan_sen'] = ichimoku.ichimoku_conversion_line()
    df['kijun_sen'] = ichimoku.ichimoku_base_line()
    df['senkou_span_a'] = ichimoku.ichimoku_a()
    df['senkou_span_b'] = ichimoku.ichimoku_b()
    df['chikou_span'] = df['close'].shift(-26)
    df.dropna(inplace=True)
    return df

# Kiểm tra tín hiệu vào lệnh
def check_signals(df):
    long_signal = (
        df['tenkan_sen'].iloc[-1] > df['kijun_sen'].iloc[-1] and
        df['close'].iloc[-1] > df['senkou_span_a'].iloc[-1] and
        df['close'].iloc[-1] > df['senkou_span_b'].iloc[-1] and
        df['senkou_span_a'].iloc[-1] > df['senkou_span_b'].iloc[-1] and
        df['chikou_span'].iloc[-1] > df['close'].iloc[-26]
    )
    
    short_signal = (
        df['tenkan_sen'].iloc[-1] < df['kijun_sen'].iloc[-1] and
        df['close'].iloc[-1] < df['senkou_span_a'].iloc[-1] and
        df['close'].iloc[-1] < df['senkou_span_b'].iloc[-1] and
        df['senkou_span_a'].iloc[-1] < df['senkou_span_b'].iloc[-1] and
        df['chikou_span'].iloc[-1] < df['close'].iloc[-26]
    )
    
    if long_signal:
        return "LONG"
    elif short_signal:
        return "SHORT"
    else:
        return "NO_SIGNAL"

# 🌟 Bắt đầu kiểm tra tín hiệu
long_tokens, short_tokens = [], []
top_100_tokens = get_top_100_usdt_pairs()

for symbol in top_100_tokens:
    try:
        df = get_candles(symbol)
        df = calculate_ichimoku(df)
        signal = check_signals(df)
        if signal == "LONG":
            long_tokens.append(symbol)
            print(f"💹 Tín hiệu LONG cho {symbol}")
            send_telegram_message(f"💹 Tín hiệu LONG cho {symbol} tại khung {interval}")
        elif signal == "SHORT":
            short_tokens.append(symbol)
            print(f"🔻 Tín hiệu SHORT cho {symbol}")
            send_telegram_message(f"🔻 Tín hiệu SHORT cho {symbol} tại khung {interval}")
    except Exception as e:
        print(f"Không thể xử lý {symbol}: {str(e)}")

# In ra danh sách token có tín hiệu
print("\n--- TỔNG KẾT ---")
print(f"Tín hiệu LONG ({len(long_tokens)}):", long_tokens)
print(f"Tín hiệu SHORT ({len(short_tokens)}):", short_tokens)

# Gửi tổng kết qua Telegram
send_telegram_message(f"--- TỔNG KẾT ---\nTín hiệu LONG ({len(long_tokens)}): {long_tokens}\nTín hiệu SHORT ({len(short_tokens)}): {short_tokens}")
