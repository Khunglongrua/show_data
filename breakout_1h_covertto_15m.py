import ccxt
import pandas as pd
import pandas_ta as ta
import requests

# Khởi tạo đối tượng Binance
binance = ccxt.binance()
interval = "1m"  # Lấy nến 1 phút từ API
VOLUME_THRESHOLD = 100_000_000  # Ngưỡng khối lượng giao dịch 24h > 100 triệu đô

def fetch_top_trading_pairs(limit=100):
    """Lấy danh sách 100 cặp giao dịch có khối lượng lớn nhất trên Binance và thỏa điều kiện khối lượng > 100 triệu đô."""
    tickers = binance.fetch_tickers()
    sorted_tickers = sorted(tickers.items(), key=lambda x: x[1].get('quoteVolume', 0), reverse=True)
    
    filtered_pairs = [
        pair for pair, data in sorted_tickers
        if '/USDT' in pair and data.get('quoteVolume', 0) > VOLUME_THRESHOLD
    ]
    
    return filtered_pairs[:limit]

def fetch_ohlcv(symbol, timeframe=interval, limit=1500):
    """Lấy dữ liệu nến 1 phút từ Binance."""
    ohlcv = binance.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
    df.set_index('timestamp', inplace=True)
    return df

def convert_to_15m(df):
    """Chuyển từ nến 1 phút sang nến 15 phút."""
    df_15m = df.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()
    return df_15m

def calculate_indicators(df):
    """Tính toán RSI, EMA50, CCI và kiểm tra điều kiện bứt phá trên nến 15 phút."""
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema50'] = ta.ema(df['close'], length=50)  # EMA50 trên nến 15 phút
    df['cci'] = ta.cci(df['high'], df['low'], df['close'], length=20)
    df['price_change'] = (df['close'] - df['open']) / df['open'] * 100
    return df

def detect_breakouts(df):
    """Phát hiện các điểm bứt phá tăng hoặc giảm theo tiêu chí."""
    df.fillna(method='ffill', inplace=True)
    df.fillna(method='bfill', inplace=True)
    latest = df.iloc[-1].copy()

    if latest[['rsi', 'ema50', 'cci', 'price_change', 'open', 'close']].isnull().any():
        return False, False

    breakout_up = (30 < latest['rsi'] < 70) and (latest['price_change'] > 0.5) and (latest['open'] < latest['ema50'] < latest['close'])
    breakout_down = (30 < latest['rsi'] < 70) and (latest['price_change'] < -0.5) and (latest['close'] < latest['ema50'] < latest['open'])

    return breakout_up, breakout_down

def send_to_discord(breakout_df, webhook_url):
    """Gửi kết quả đến Discord webhook nếu có đồng nào thỏa điều kiện."""
    if breakout_df.empty:
        print("Không có đồng nào đạt tiêu chí bứt phá.")  # In ra console nếu không có đồng nào thỏa
    else:
        message = "📢 **Danh sách 1M to 15M bứt phá** 📊\n"
        for _, row in breakout_df.iterrows():
            message += f"\n**{row['symbol']}**: {row['breakout_type']} tại {row['latest_timestamp']} (CCI: {row['cci']:.2f})"
        
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
        df_1m = fetch_ohlcv(pair)
        df_15m = convert_to_15m(df_1m)  # Chuyển sang nến 15 phút
        df_15m = calculate_indicators(df_15m)
        breakout_up, breakout_down = detect_breakouts(df_15m)
        if breakout_up or breakout_down:
            breakout_results.append({'symbol': pair, 'latest_timestamp': df_15m.iloc[-1]['timestamp'], 'cci': df_15m.iloc[-1]['cci'], 
                                     'breakout_type': 'UP' if breakout_up else 'DOWN'})
    
    breakout_df = pd.DataFrame(breakout_results)
    if not breakout_df.empty:
        print("Các cặp đạt tiêu chí bứt phá:")
        print(breakout_df)
        breakout_df.to_csv("breakout_results.csv", index=False)
        send_to_discord(breakout_df, webhook_url)  # Gửi nếu có kết quả
    else:
        print("Không có đồng nào đạt tiêu chí bứt phá.")  # Chỉ in ra nếu không có đồng nào thỏa

if __name__ == "__main__":
    main()
