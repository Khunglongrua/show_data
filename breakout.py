import ccxt
import pandas as pd
import pandas_ta as ta
import requests

# Khởi tạo đối tượng Binance Futures
binance = ccxt.binance({
    'options': {
        'defaultType': 'future'  # Sử dụng thị trường Futures
    }
})

interval = "5m"
threshold = 0.5  # Ngưỡng phần trăm bứt phá

def fetch_top_trading_pairs(limit=200):
    """Lấy danh sách 200 cặp giao dịch có khối lượng lớn nhất trên Binance Futures."""
    tickers = binance.fetch_tickers()
    sorted_tickers = sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)
    
    # Lọc các cặp là cặp USDT và không chứa ký tự lỗi
    filtered_pairs = [pair for pair, data in sorted_tickers if '/USDT' in pair and not pair.endswith(':USDT')]
    
    return filtered_pairs[:limit]

def fetch_ohlcv(symbol, timeframe=interval, limit=100):
    """Lấy dữ liệu lịch sử giá OHLCV từ Binance Futures."""
    ohlcv = binance.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Tính EMA21 của volume
    df['ema21_volume'] = df['volume'].ewm(span=21, adjust=False).mean()
    
    return df

def calculate_indicators(df):
    """Tính toán RSI, EMA50, CCI và kiểm tra điều kiện bứt phá."""
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['cci'] = ta.cci(df['high'], df['low'], df['close'], length=20)
    df['price_change'] = (df['close'] - df['open']) / df['open'] * 100
    return df

def detect_breakouts(df, threshold=0.5):
    """Phát hiện các điểm bứt phá tăng hoặc giảm theo tiêu chí."""
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    latest = df.iloc[-1].copy()

    if latest[['rsi', 'ema50', 'cci', 'price_change', 'open', 'close', 'ema21_volume']].isnull().any():
        return False, False, 0

    # Tính tỷ lệ tăng trưởng của volume so với ema21_volume
    if latest['ema21_volume'] != 0:
        volume_ratio = ((latest['volume'] - latest['ema21_volume']) / latest['ema21_volume']) * 100
    else:
        volume_ratio = 0

    # Điều kiện mới: chỉ chấp nhận khi tỷ lệ này > 200%
    if volume_ratio <= 100:
        return False, False, 0

    breakout_up = (30 < latest['rsi'] < 70) and (latest['price_change'] > threshold) and (latest['open'] < latest['ema50'] < latest['close'])
    breakout_down = (30 < latest['rsi'] < 70) and (latest['price_change'] < -threshold) and (latest['close'] < latest['ema50'] < latest['open'])

    return breakout_up, breakout_down, volume_ratio

def send_to_discord(breakout_df, webhook_url):
    """Gửi kết quả đến Discord webhook."""
    if breakout_df.empty:
        print("❌ Không có đồng nào đạt tiêu chí bứt phá. Không gửi thông báo qua Discord.")
        return

    message = "📢 **Danh sách các cặp đạt tiêu chí bứt phá** 📊\n"
    for _, row in breakout_df.iterrows():
        message += f"\n**{row['symbol']}**: {row['breakout_type']} tại {row['latest_timestamp']} (CCI: {row['cci']:.2f}, Tăng trưởng khối lượng: {row['volume_ratio']:.2f}%)"
    
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload)
    if response.status_code == 204:
        print("Đã gửi báo cáo thành công đến Discord.")
    else:
        print(f"Đã có lỗi khi gửi báo cáo đến Discord: {response.status_code}")

def main():
    webhook_url = "https://discord.com/api/webhooks/1344273160278638694/TXFWMlubnyJ4WQwyXo-mbdFvIti-xx2lgySxw9ghx4OHTO18zb4PEpTi6td0NzWwg2sd"
    top_pairs = fetch_top_trading_pairs()
    breakout_results = []
    
    for pair in top_pairs:
        df = fetch_ohlcv(pair)
        df = calculate_indicators(df)
        breakout_up, breakout_down, volume_ratio = detect_breakouts(df, threshold=threshold)
        if breakout_up or breakout_down:
            breakout_results.append({
                'symbol': pair,
                'latest_timestamp': df.iloc[-1]['timestamp'],
                'cci': df.iloc[-1]['cci'],
                'volume_ratio': volume_ratio,
                'breakout_type': 'UP' if breakout_up else 'DOWN'
            })
    
    breakout_df = pd.DataFrame(breakout_results)
    if not breakout_df.empty:
        print("Các cặp đạt tiêu chí bứt phá:")
        print(breakout_df)
        breakout_df.to_csv("breakout_results.csv", index=False)
    else:
        print("Không có đồng nào đạt tiêu chí bứt phá.")
    
    send_to_discord(breakout_df, webhook_url)

if __name__ == "__main__":
    main()







