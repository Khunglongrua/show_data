import ccxt
import pandas as pd
import requests  # Dùng để gửi tín hiệu qua Telegram
from ta.trend import IchimokuIndicator

# 🌟 Thông tin Telegram Bot
API_TOKEN = '6303089629:AAGUqu7ve_aN98Z7J_rTcxBQv1b3nvLIJ-U'
CHAT_ID = '-4748582015'

# 🌟 Cài đặt chung
required_1m_candles = 45  # Giảm xuống 200 nến 1 phút (không tính chikou_span)

# Kết nối Binance API (Spot)
binance = ccxt.binance({
    'options': {'defaultType': 'spot'}
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

# Lấy dữ liệu nến 1 phút và chuyển thành 15 phút
def get_15m_candles_from_1m(symbol):
    ohlcv = binance.fetch_ohlcv(symbol, timeframe='1m', limit=required_1m_candles)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    df_15m = df.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()



# Tính toán Ichimoku (bỏ chikou_span)
def calculate_ichimoku(df):
    ichimoku = IchimokuIndicator(high=df['high'], low=df['low'], window1=9, window2=26, window3=52)
    df['tenkan_sen'] = ichimoku.ichimoku_conversion_line()
    df['kijun_sen'] = ichimoku.ichimoku_base_line()
    df['senkou_span_a'] = ichimoku.ichimoku_a()
    df['senkou_span_b'] = ichimoku.ichimoku_b()

    df.dropna(inplace=True)
    return df

# Tính delta
def calculate_deltas(df):
    delta_last = df['tenkan_sen'].iloc[-1] - df['kijun_sen'].iloc[-1]
    delta_third_last = df['tenkan_sen'].iloc[-3] - df['kijun_sen'].iloc[-3]
    delta_close_tenkan = df['close'].iloc[-1] - df['tenkan_sen'].iloc[-1]
    return delta_last, delta_third_last, delta_close_tenkan

# Kiểm tra điều kiện đảo chiều
def check_trend_reversal(delta_last, delta_third_last, delta_close_tenkan):
    if delta_last > 0 and delta_third_last < 0 and delta_close_tenkan > 0:
        return "UP"
    elif delta_last < 0 and delta_third_last > 0 and delta_close_tenkan < 0:
        return "DOWN"
    else:
        return "NO_REVERSAL"

# 🌟 Bắt đầu kiểm tra tín hiệu
top_100_tokens = get_top_100_usdt_pairs()

for symbol in top_100_tokens:
    try:
        df = get_15m_candles_from_1m(symbol)
        if df is None:
            continue

        df = calculate_ichimoku(df)
        delta_last, delta_third_last, delta_close_tenkan = calculate_deltas(df)

        trend_signal = check_trend_reversal(delta_last, delta_third_last, delta_close_tenkan)

        # 🟢 Gửi tín hiệu ngay lập tức nếu là UP hoặc DOWN
        if trend_signal in ["UP", "DOWN"]:
            kijun_sen_last = df['kijun_sen'].iloc[-1]
            delta_percentage = (delta_last / kijun_sen_last) * 100 if kijun_sen_last != 0 else 0
            message = f"{symbol} | {trend_signal} | Δ: {delta_percentage:+.2f}%"
            print(message)
            send_telegram_message(message)  # 🟢 Gửi ngay lập tức

    except Exception as e:
        print(f"Không thể xử lý {symbol}: {str(e)}")

print("Hoàn thành tính toán Ichimoku.")


