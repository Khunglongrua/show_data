import ccxt
import pandas as pd
import requests
import time

# Initialize Binance Futures object using ccxt
binance = ccxt.binance({
    'options': {
        'defaultType': 'future'  # Sử dụng thị trường Futures
    }
})

# Discord Webhook URL
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1325976304029532252/qY1bNguDfHqy4qBjCzclrfdhFZpCLOJvOzvvDw4U1bPkOPCse9kiRud8rZsD1y88ANwE'

# Fetch top 200 symbols by trading volume directly from Binance Futures
volume_data = []
try:
    tickers = binance.fetch_tickers()
    for symbol, ticker in tickers.items():
        # Điều kiện kiểm tra symbol hợp lệ: Kết thúc bằng USDT và không chứa :USDT
        if symbol.endswith('USDT') and ':USDT' not in symbol and ticker['quoteVolume'] is not None:
            volume_data.append((symbol, ticker['quoteVolume']))
except Exception as e:
    print(f"Lỗi khi lấy dữ liệu ticker: {e}")

# Sort symbols by trading volume (descending) and get top 200
top_symbols = sorted(volume_data, key=lambda x: x[1], reverse=True)[:200]
symbols = [symbol[0] for symbol in top_symbols]

# Parameters
timeframe = '15m'
limit_candles = 120
donchian_period = 20

# Function to fetch candles data
def get_candles(symbol, timeframe, limit=120):
    try:
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu nến cho {symbol}: {e}")
        return pd.DataFrame()  # Trả về DataFrame rỗng nếu lỗi

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

# Biến để kiểm tra có tín hiệu nào không
has_signal = False

# Iterate through each symbol
for symbol in symbols:
    try:
        # Fetch candles data
        df = get_candles(symbol, timeframe, limit=limit_candles)

        # Kiểm tra nếu DataFrame rỗng thì bỏ qua
        if df.empty:
            print(f"⚠️ Không có dữ liệu cho {symbol}")
            continue

        # Calculate Donchian Channel
        df['donchian_high'] = df['high'].rolling(window=donchian_period).max()
        df['donchian_low'] = df['low'].rolling(window=donchian_period).min()
        df['donchian_mid'] = (df['donchian_high'] + df['donchian_low']) / 2

        # Calculate Ichimoku Cloud
        high9 = df['high'].rolling(window=9).max()
        low9 = df['low'].rolling(window=9).min()
        tenkan_sen = (high9 + low9) / 2

        high26 = df['high'].rolling(window=26).max()
        low26 = df['low'].rolling(window=26).min()
        kijun_sen = (high26 + low26) / 2

        # Drop NaN values
        df = df.dropna()

        # Kiểm tra lại nếu DataFrame rỗng sau khi drop NaN
        if df.empty:
            print(f"⚠️ Không có đủ dữ liệu sau khi xử lý cho {symbol}")
            continue

        # Get last values
        last_close = df['close'].iat[-1]
        upper_band = df['donchian_high'].iat[-1]
        lower_band = df['donchian_low'].iat[-1]

        # Create TradingView link
        symbol_tradingview = symbol.replace("/", "")
        tradingview_link = f"https://www.tradingview.com/symbols/{symbol_tradingview}/"

        # Tín hiệu từ Donchian Channel và Ichimoku
        if last_close > upper_band and tenkan_sen.iloc[-1] > kijun_sen.iloc[-1]:
            message = f"📈🟢 **Tín hiệu tăng sớm:** {symbol}\n🔗 Link: {tradingview_link}"
            print(message)
            send_discord_message(message)
            has_signal = True
        elif last_close < lower_band and tenkan_sen.iloc[-1] < kijun_sen.iloc[-1]:
            message = f"📉🔴 **Tín hiệu giảm sớm:** {symbol}\n🔗 Link: {tradingview_link}"
            print(message)
            send_discord_message(message)
            has_signal = True

        # Nghỉ 0.2 giây giữa các yêu cầu để tránh bị chặn IP
        time.sleep(0.2)

    except Exception as e:
        print(f"Cannot process {symbol}: {str(e)}")

# Nếu không có tín hiệu nào thỏa mãn
if not has_signal:
    no_signal_message = "❌ Không có symbol nào thỏa mãn điều kiện."
    print(no_signal_message)
    send_discord_message(no_signal_message)

print("\n--- All symbols processed ---")
