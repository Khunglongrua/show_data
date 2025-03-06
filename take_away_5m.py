import ccxt
import pandas as pd
import pandas_ta as ta
import requests

# Khởi tạo đối tượng Binance
binance = ccxt.binance()
interval = "5m"
VOLUME_THRESHOLD = 100_000_000  # Ngưỡng khối lượng giao dịch 24h > 100 triệu đô
VOLUME_GROWTH_THRESHOLD = 1  # Ngưỡng tốc độ phát triển của khối lượng so với EMA21
PRICE_THRESHOLD = 0.5 # Phần trăm

# Telegram Bot Configuration
TELEGRAM_TOKEN = "6935422937:AAGYolPsrtw4UCW4QMXUQyBJqtTK5qWatBc"  # Thay YOUR_TELEGRAM_BOT_TOKEN bằng TOKEN của bot Telegram
CHAT_ID = "-4624245458"  # Thay YOUR_CHAT_ID bằng CHAT ID của bạn

def send_to_telegram(message):
    """Gửi tin nhắn đến Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Đã gửi báo cáo thành công đến Telegram.")
    else:
        print(f"Đã có lỗi khi gửi báo cáo đến Telegram: {response.status_code}")

def fetch_top_trading_pairs(limit=100):
    """Lấy danh sách 100 cặp giao dịch có khối lượng lớn nhất trên Binance và thỏa điều kiện khối lượng > 100 triệu đô."""
    tickers = binance.fetch_tickers()
    sorted_tickers = sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)
    filtered_pairs = [
        pair for pair, data in sorted_tickers
        if '/USDT' in pair and data.get('quoteVolume', 0) > VOLUME_THRESHOLD
    ]
    return filtered_pairs[:limit]

def fetch_ohlcv(symbol, timeframe=interval, limit=100):
    """Lấy dữ liệu lịch sử giá OHLCV từ Binance."""
    ohlcv = binance.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh').dt.strftime('%Y-%m-%d %H:%M:%S')
    return df

def calculate_indicators(df):
    """Tính toán RSI, EMA50, CCI, EMA21 của khối lượng và kiểm tra điều kiện bứt phá."""
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['ema21_volume'] = ta.ema(df['volume'], length=21)  # Tính EMA21 của khối lượng
    df['cci'] = ta.cci(df['high'], df['low'], df['close'], length=20)
    df['price_change'] = (df['close'] - df['open']) / df['open'] * 100
    return df

def detect_breakouts(df):
    """Phát hiện các điểm bứt phá tăng hoặc giảm theo tiêu chí."""
    df.fillna(method='ffill', inplace=True)
    df.fillna(method='bfill', inplace=True)
    latest = df.iloc[-1].copy()

    if latest[['rsi', 'ema50', 'cci', 'price_change', 'open', 'close', 'ema21_volume']].isnull().any():
        return False, False

    volume_growth = latest['volume'] / latest['ema21_volume']
    if volume_growth <= VOLUME_GROWTH_THRESHOLD:
        return False, False

    breakout_up = (30 < latest['rsi'] < 70) and (latest['price_change'] > 0.5) and (latest['open'] < latest['ema50'] < latest['close'])
    breakout_down = (30 < latest['rsi'] < 70) and (latest['price_change'] < -0.5) and (latest['close'] < latest['ema50'] < latest['open'])

    return breakout_up, breakout_down

def main():
    top_pairs = fetch_top_trading_pairs()
    breakout_results = []

    for pair in top_pairs:
        df = fetch_ohlcv(pair)
        df = calculate_indicators(df)
        breakout_up, breakout_down = detect_breakouts(df)
        if breakout_up or breakout_down:
            breakout_results.append({
                'symbol': pair,
                'latest_timestamp': df.iloc[-1]['timestamp'],
                'cci': df.iloc[-1]['cci'],
                'breakout_type': 'UP' if breakout_up else 'DOWN'
            })
    
    if breakout_results:
        # Tạo message gửi Telegram
        message = "📢 *Các cặp Breakout Basic 5M bứt phá* 📊\n"
        print("Các cặp đạt tiêu chí bứt phá:")
        for result in breakout_results:
            message += f"\n*{result['symbol']}* ➡ {result['breakout_type']} tại {result['latest_timestamp']} (CCI: {result['cci']:.2f})"
            print(f"{result['symbol']} ➡ {result['breakout_type']} tại {result['latest_timestamp']} (CCI: {result['cci']:.2f})")
        
        # Gửi qua Telegram
        send_to_telegram(message)
    else:
        print("Không có đồng nào đạt tiêu chí bứt phá.")  # Chỉ in ra, không gửi Telegram

if __name__ == "__main__":
    main()
