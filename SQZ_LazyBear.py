#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import pandas as pd
import ccxt
import requests
import pandas_ta as ta
from datetime import datetime


def get_latest_excel_files(directory, count=2):
    """
    Lấy danh sách file Excel mới nhất theo thứ tự thời gian (tối đa count file).
    """
    try:
        files = sorted(
            [f for f in os.listdir(directory) if f.endswith(".xlsx")],
            key=lambda x: os.path.getmtime(os.path.join(directory, x)),
            reverse=True
        )
        return files[:count]
    except Exception as e:
        print(f"Lỗi khi lấy file Excel mới nhất: {e}")
        return []


def find_missing_symbols(current_file, previous_file):
    """
    Tìm các symbol bị mất trong file hiện tại so với file trước đó.
    """
    try:
        current_df = pd.read_excel(current_file)
        previous_df = pd.read_excel(previous_file)
        
        current_symbols = set(current_df['Symbol'])
        previous_symbols = set(previous_df['Symbol'])
        
        missing_symbols = list(previous_symbols - current_symbols)
        return missing_symbols
    except Exception as e:
        print(f"Lỗi khi tìm symbol bị mất: {e}")
        return []


def delete_old_excel_files(directory, keep_count=2):
    """
    Xóa các file Excel cũ trong thư mục làm việc, chỉ giữ lại số lượng file mới nhất.
    """
    try:
        files = sorted(
            [f for f in os.listdir(directory) if f.endswith(".xlsx")],
            key=lambda x: os.path.getmtime(os.path.join(directory, x)),
            reverse=True
        )
        
        files_to_delete = files[keep_count:]
        for file in files_to_delete:
            os.remove(os.path.join(directory, file))
            print(f"Đã xóa file cũ: {file}")
    except Exception as e:
        print(f"Lỗi khi xóa file cũ: {e}")


def send_to_telegram(symbol, adx, sqz_duration, bot_token, chat_id):
    """
    Gửi báo cáo từng symbol qua Telegram ngay khi phát hiện.
    """
    try:
        message = (
            f"📢 *Phát hiện Symbol thỏa mãn!* 📊\n"
            f"📊 *Symbol:* {symbol}\n"
            f"📈 *ADX:* {adx}\n"
            f"💥 *SQZ_Duration:* {sqz_duration}\n"
        )
        
        # Gửi tin nhắn qua Telegram
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print(f"Đã gửi báo cáo cho {symbol} thành công đến Telegram.")
        else:
            print(f"Đã có lỗi khi gửi báo cáo cho {symbol} đến Telegram: {response.status_code}")
    except Exception as e:
        print(f"Lỗi khi gửi báo cáo tới Telegram: {e}")


def get_binance_klines(symbol, timeframe, limit=100):
    """
    Lấy dữ liệu nến từ Binance bằng CCXT.
    """
    exchange = ccxt.binance()
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        print(f"Lỗi lấy dữ liệu {symbol}: {e}")
        return None


def calculate_indicators(df, window=20):
    """
    Tính toán các chỉ báo cần thiết: ADX và SQZ_Duration.
    """
    df.ta.squeeze(length=window, append=True, lazybear=True)
    adx = df.ta.adx(length=window)
    df['ADX'] = adx['ADX_20']
    df['SQZ_Duration'] = (
        df['SQZ_ON']
        .groupby((df['SQZ_ON'] != df['SQZ_ON'].shift()).cumsum())
        .cumsum()
        .where(df['SQZ_ON'] == 1, 0)
    )
    return df.round(2)


def get_top_100_usdt_coins():
    """
    Lấy danh sách top 100 cặp giao dịch USDT có khối lượng cao nhất.
    """
    exchange = ccxt.binance()
    tickers = exchange.fetch_tickers()
    df = pd.DataFrame([tickers[symbol] for symbol in tickers])
    df = df[df['symbol'].str.endswith('/USDT')]
    stablecoins = ["USDC/USDT", "BUSD/USDT", "TUSD/USDT", "DAI/USDT", "FDUSD/USDT", "USDP/USDT", "GUSD/USDT"]
    df = df[~df['symbol'].isin(stablecoins)]
    df = df.nlargest(100, 'quoteVolume')
    return df['symbol'].tolist()


def process_top_100_usdt_coins(timeframe="15m", limit=100, window=20, bot_token=None, chat_id=None):
    """
    Phân tích top 100 cặp USDT và gửi từng symbol thỏa mãn qua Telegram ngay khi phát hiện.
    """
    try:
        symbols = get_top_100_usdt_coins()
        print(f"\n--- Đang phân tích top 100 cặp USDT ---")
        
        for symbol in symbols:
            try:
                df = get_binance_klines(symbol, timeframe, limit)
                if df is None or df.empty:
                    print(f"Bỏ qua {symbol} do không có dữ liệu.")
                    continue
                
                df = calculate_indicators(df, window)
                last_row = df.iloc[-1]
                
                if last_row['close'] < 0.5:
                    print(f"Bỏ qua {symbol} do giá đóng cửa thấp.")
                    continue
                
                # Kiểm tra điều kiện ADX và SQZ_Duration
                if last_row['ADX'] > set_adx and last_row['SQZ_Duration'] > set_sqz:
                    print(f"{symbol}: ADX = {last_row['ADX']}, SQZ_Duration = {last_row['SQZ_Duration']}")
                    
                    # Gửi báo cáo từng symbol ngay lập tức
                    if bot_token and chat_id:
                        send_to_telegram(
                            symbol=symbol,
                            adx=last_row['ADX'],
                            sqz_duration=last_row['SQZ_Duration'],
                            bot_token=bot_token,
                            chat_id=chat_id
                        )
            except Exception as e:
                print(f"Lỗi khi xử lý {symbol}: {e}")
                continue  # Bỏ qua symbol bị lỗi và tiếp tục symbol tiếp theo
        
    except Exception as e:
        print(f"Lỗi xử lý chung: {e}")


if __name__ == "__main__":
    working_directory = "/home/dzu/Desktop/crypto_data"
    os.makedirs(working_directory, exist_ok=True)
    os.chdir(working_directory)
    
    set_adx = 15
    set_sqz = 5
    
    # Telegram bot token và chat ID
    telegram_bot_token = "6190624249:AAEjI1Ug13BdyOqW2SghymsriH7-GCAm_3k"
    telegram_chat_id = "-4748330586"
    
    process_top_100_usdt_coins(
        bot_token=telegram_bot_token,
        chat_id=telegram_chat_id
    )

