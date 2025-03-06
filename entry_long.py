import os
import pandas as pd
import ccxt
import requests
import time


from ta.momentum import RSIIndicator
from ta.trend import CCIIndicator, EMAIndicator


# Cài đặt Telegram Bot
TELEGRAM_BOT_TOKEN = "6462681730:AAE4_9qV7m04EOB3NfGGFXyksuuWKnftUk0"
TELEGRAM_CHAT_ID = "-4770512637"

# Thiết lập tham số
PRICE_DIFFERENCE_THRESHOLD = 2  # Ngưỡng chênh lệch giá (phần trăm)
INTERVAL = '15m'  # Tham số khung thời gian (có thể là '15m', '1h', '4h', v.v.)

# Thiết lập sàn giao dịch Binance Futures
exchange = ccxt.binance({
    'options': {
        'defaultType': 'future'  # Sử dụng thị trường Futures
    }
})

def send_to_telegram(message):
    """Gửi tin nhắn tới Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Đã gửi báo cáo thành công đến Telegram.")
        else:
            print(f"Đã có lỗi khi gửi báo cáo đến Telegram: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gửi báo cáo tới Telegram: {e}")

def get_top_200_usdt_coins():
    """Lấy danh sách 200 cặp USDT có khối lượng giao dịch cao nhất."""
    try:
        tickers = exchange.fetch_tickers()
        if not tickers:
            print("[LỖI] Không lấy được dữ liệu từ API Binance!")
            return []

        # In ra một phần dữ liệu để kiểm tra
        print("Dữ liệu trả về từ Binance:", list(tickers.keys())[:5])  # In thử 5 cặp đầu tiên

        # Xử lý dữ liệu để bỏ hậu tố ':USDT'
        cleaned_tickers = {}
        for symbol in tickers:
            clean_symbol = symbol.split(':')[0]  # Loại bỏ phần ':USDT'
            tickers[symbol]['symbol'] = clean_symbol  # Cập nhật symbol trong dữ liệu
            cleaned_tickers[clean_symbol] = tickers[symbol]

        df = pd.DataFrame([cleaned_tickers[symbol] for symbol in cleaned_tickers])

        if 'symbol' not in df.columns or 'quoteVolume' not in df.columns:
            print("[LỖI] Không tìm thấy cột 'symbol' hoặc 'quoteVolume' trong dữ liệu!")
            print("Các cột hiện có:", df.columns)
            return []

        # Chỉ lấy các cặp kết thúc bằng '/USDT'
        df = df[df['symbol'].str.endswith('/USDT')]
        
        # Loại bỏ các stablecoins
        stablecoins = ["USDC/USDT", "BUSD/USDT", "TUSD/USDT", "DAI/USDT", "FDUSD/USDT", "USDP/USDT", "GUSD/USDT"]
        df = df[~df['symbol'].isin(stablecoins)]
        
        # Lọc top 200 theo khối lượng giao dịch
        df = df.nlargest(200, 'quoteVolume')
        

        return df['symbol'].tolist()
    except ccxt.NetworkError as e:
        print(f"[LỖI] Lỗi mạng khi lấy dữ liệu: {e}")
    except ccxt.ExchangeError as e:
        print(f"[LỖI] Lỗi từ sàn Binance: {e}")
    except Exception as e:
        print(f"[LỖI] Lỗi không xác định: {e}")
    return []

def get_binance_klines(symbol, timeframe=INTERVAL, limit=100):
    """Lấy dữ liệu OHLCV từ Binance."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            print(f"[LỖI] Không có dữ liệu OHLCV cho {symbol}!")
            return None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        if df.empty:
            print(f"[LỖI] Không có dữ liệu hợp lệ cho {symbol}!")
            return None

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)

        # Tính EMA21 của volume
        df['ema21_volume'] = df['volume'].ewm(span=21, adjust=False).mean()
        
        return df
    except ccxt.NetworkError as e:
        print(f"[LỖI] Lỗi mạng khi lấy dữ liệu {symbol}: {e}")
    except ccxt.ExchangeError as e:
        print(f"[LỖI] Lỗi từ sàn Binance khi lấy dữ liệu {symbol}: {e}")
    except Exception as e:
        print(f"[LỖI] Lỗi không xác định khi lấy dữ liệu {symbol}: {e}")
    return None


def process_top_200_usdt_coins():
    """Xử lý top 200 cặp USDT và gửi thông báo nếu có sự khác biệt đáng kể."""
    top_200_coins = get_top_200_usdt_coins()
    if not top_200_coins:
        print("[LỖI] Không lấy được danh sách top 200 cặp USDT.")
        return

    for symbol in top_200_coins:
        df = get_binance_klines(symbol)
        if df is None or df.empty:
            continue

        # Tính RSI, CCI và EMA50 sử dụng thư viện ta
        df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
        df['CCI'] = CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=20).cci()
        df['EMA50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()

        # Kiểm tra điều kiện khối lượng > 150% của ema21_volume
        latest_volume = df['volume'].iloc[-1]
        latest_ema21_volume = df['ema21_volume'].iloc[-1]
        volume_ratio = round(latest_volume / latest_ema21_volume, 2)  # Tính tỷ lệ và làm tròn 2 số thập phân

        if volume_ratio > 1.5:  # Chỉ gửi khi khối lượng > 150% EMA21 Volume
            # Kiểm tra chênh lệch giá
            close_prices = df['close']
            latest_close = close_prices.iloc[-1]
            previous_close = close_prices.iloc[-2]
            price_difference = ((latest_close - previous_close) / previous_close) * 100  # Giữ nguyên dấu của price_diff

            latest_rsi = df['RSI'].iloc[-1]
            latest_cci = df['CCI'].iloc[-1]
            latest_ema50 = df['EMA50'].iloc[-1]

            # Điều kiện tăng
            if price_difference > PRICE_DIFFERENCE_THRESHOLD and latest_close > latest_ema50:
                message = (
                    f"📈 {symbol}: Giá tăng {price_difference:.2f}% với {INTERVAL}.\n"
                    f"Giá: {latest_close:.4f} USDT (trên EMA50: {latest_ema50:.4f})\n"
                    f"RSI: {latest_rsi:.2f}, CCI: {latest_cci:.2f}\n"
                    f"Khối lượng gấp {volume_ratio}x EMA21"
                )
                send_to_telegram(message)

            # Điều kiện giảm
            elif price_difference < -PRICE_DIFFERENCE_THRESHOLD and latest_close < latest_ema50:
                message = (
                    f"📉 {symbol}: Giá giảm {price_difference:.2f}% với {INTERVAL}.\n"
                    f"Giá: {latest_close:.4f} USDT (dưới EMA50: {latest_ema50:.4f})\n"
                    f"RSI: {latest_rsi:.2f}, CCI: {latest_cci:.2f}\n"
                    f"Khối lượng gấp {volume_ratio}x EMA21"
                )
                send_to_telegram(message)

        time.sleep(0.5)  # Tránh gửi quá nhanh
if __name__ == "__main__":
    process_top_200_usdt_coins()
