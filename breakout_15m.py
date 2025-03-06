import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import os

# Sử dụng biến môi trường để bảo mật thông tin nhạy cảm
TELEGRAM_BOT_TOKEN = os.getenv("6383838849:AAFkLDa6LJy_MoTl7gE15OPApeVllcWqekY")
TELEGRAM_CHAT_ID = os.getenv("-4770512637")

# Khởi tạo đối tượng Binance
binance = ccxt.binance()
interval = "15m"

# Tham số cấu hình
PRICE_THRESHOLD = 0.5  # Ngưỡng chênh lệch giá (phần trăm)

def fetch_top_trading_pairs(limit=200):
    """Lấy danh sách 200 cặp USDT có khối lượng giao dịch cao nhất."""
    tickers = binance.fetch_tickers()
    sorted_tickers = sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)
    return [pair for pair, data in sorted_tickers[:limit] if pair.endswith('USDT')]

def fetch_ohlcv(symbol, timeframe=interval, limit=100):
    """Lấy dữ liệu lịch sử giá OHLCV từ Binance."""
    ohlcv = binance.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.strftime('%Y-%m-%d %H:%M:%S')
    df['ema21_volume'] = df['volume'].ewm(span=21, adjust=False).mean()
    return df

def calculate_indicators(df):
    """Tính toán EMA50, tỷ lệ thay đổi giá và các chỉ báo khác."""
    df['ema50'] = ta.ema(df['close'], length=50)
    df['price_change'] = (df['close'] - df['open']) / df['open'] * 100
    return df

def detect_breakouts(df):
    """Phát hiện các điểm bứt phá tăng hoặc giảm theo tiêu chí."""
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    latest = df.iloc[-1].copy()
    volume_ratio = ((latest['volume'] - latest['ema21_volume']) / latest['ema21_volume']) * 100
    if volume_ratio <= 100:
        return False, False, volume_ratio
    breakout_up = (latest['price_change'] > PRICE_THRESHOLD) and (latest['open'] < latest['ema50'] < latest['close'])
    breakout_down = (latest['price_change'] < -PRICE_THRESHOLD) and (latest['close'] < latest['ema50'] < latest['open'])
    return breakout_up, breakout_down, volume_ratio

def send_to_telegram(breakout_df):
    """Gửi kết quả đến Telegram."""
    if breakout_df.empty:
        print("❌ Không có đồng nào đạt tiêu chí bứt phá.")
        return
    message = "📢 **Danh sách các cặp đạt tiêu chí bứt phá** 📊\n"
    for _, row in breakout_df.iterrows():
        message += f"\n**{row['symbol']}**: {row['breakout_type']} tại {row['latest_timestamp']} (Tăng trưởng khối lượng: {row['volume_ratio']:.2f}%)"
    if len(message) > 4000:
        message = message[:3997] + "..."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
    if response.status_code != 200:
        print(f"Đã có lỗi khi gửi báo cáo: {response.status_code}")
    else:
        print("Đã gửi báo cáo thành công.")

def main():
    top_pairs = fetch_top_trading_pairs()
    breakout_results = []
    for pair in top_pairs:
        try:
            df = fetch_ohlcv(pair)
            df = calculate_indicators(df)
            breakout_up, breakout_down, volume_ratio = detect_breakouts(df)
            if breakout_up or breakout_down:
                breakout_results.append({
                    'symbol': pair,
                    'latest_timestamp': df.iloc[-1]['timestamp'],
                    'volume_ratio': volume_ratio,
                    'breakout_type': 'UP' if breakout_up else 'DOWN'
                })
        except Exception as e:
            print(f"Lỗi khi xử lý {pair}: {str(e)}")
    
    breakout_df = pd.DataFrame(breakout_results)
    send_to_telegram(breakout_df)

if __name__ == "__main__":
    main()
