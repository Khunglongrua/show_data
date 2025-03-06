#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import time
import requests
from datetime import datetime, timedelta
from binance.client import Client
from binance.enums import *

# Thông tin API Key (Nên dùng biến môi trường để bảo mật)
API_KEY = ""  # Để trống nếu muốn test không cần API
API_SECRET = ""  # Để trống nếu muốn test không cần API
DISCORD_WEBHOOK_URL = ""  # Thay bằng URL của bạn nếu có

# Cấu hình ngưỡng cắt lỗ và thời gian tối đa giữ lệnh (có thể thay đổi)
MAX_LOSS_RATIO = -0.30  # Cắt lỗ khi lỗ 30%
MAX_HOLD_TIME_HOURS = 3  # Thời gian tối đa giữ lệnh (giờ)
PARTIAL_PROFIT_RATIO = 0.50  # Tỷ lệ lợi nhuận để chốt lời một phần
PARTIAL_CLOSE_1H = 0.50  # Chốt 50% lợi nhuận sau 1 giờ nếu đạt tỷ lệ lợi nhuận
PARTIAL_CLOSE_2H = 0.30  # Chốt 30% lợi nhuận sau 2 giờ nếu đạt tỷ lệ lợi nhuận

# Kết nối với Binance nếu có API Key
client = None
if API_KEY and API_SECRET:
    client = Client(API_KEY, API_SECRET, tld='com')
    print("Kết nối với Binance thành công.")
else:
    print("[GIẢ LẬP] Không có API Key, chạy ở chế độ mô phỏng.")

print("Bot đóng vị thế đang hoạt động ...")

# Hàm gửi thông báo lên Discord
def send_discord_notification(message):
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    print(message)  # In thông tin ra console

# Hàm lấy vị thế hiện tại
def get_open_positions():
    if client:
        positions = client.futures_account()['positions']
        open_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
        return open_positions
    else:
        print("[GIẢ LẬP] Không có API Key, trả về vị thế mô phỏng.")
        # Dữ liệu giả lập cho test
        return [
            {'symbol': 'BTCUSDT', 'positionAmt': '0.01', 'entryPrice': '20000', 'markPrice': '21000', 'unrealizedProfit': '100', 'leverage': '10', 'updateTime': str(int(time.time() * 1000))}
        ]

# Hàm đóng một phần lệnh futures
def close_partial_position(symbol, percentage):
    if client:
        try:
            position_info = next((pos for pos in get_open_positions() if pos['symbol'] == symbol), None)
            if not position_info:
                print(f"No open position found for {symbol}")
                return
            
            position_amt = float(position_info['positionAmt']) * percentage
            side = ORDER_SIDE_BUY if position_amt < 0 else ORDER_SIDE_SELL
            
            order = client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=abs(position_amt),
                reduceOnly=True
            )
            message = f"Partially closed {percentage * 100}% of position for {symbol}: {order}"
            send_discord_notification(message)
        except Exception as e:
            print(f"Error closing partial position for {symbol}: {e}")
    else:
        print(f"[GIẢ LẬP] Đã đóng {percentage * 100}% vị thế cho {symbol}")

# Hàm kiểm tra các điều kiện cắt lệnh
def should_close_position(pos):
    symbol = pos['symbol']
    entry_price = float(pos['entryPrice'])
    mark_price = float(pos['markPrice'])
    unrealized_pnl = float(pos['unrealizedProfit'])
    leverage = float(pos['leverage'])
    position_amt = abs(float(pos['positionAmt']))
    position_value = position_amt * entry_price / leverage
    entry_time = datetime.fromtimestamp(float(pos['updateTime']) / 1000)
    elapsed_time = datetime.utcnow() - entry_time
    profit_ratio = unrealized_pnl / position_value if position_value > 0 else 0
    
    if position_value > 0 and profit_ratio <= MAX_LOSS_RATIO:
        message = f"Closed position {symbol} due to loss threshold reached: {profit_ratio * 100:.2f}%"
        send_discord_notification(message)
        return True

    if elapsed_time > timedelta(hours=MAX_HOLD_TIME_HOURS):
        message = f"Closed position {symbol} due to exceeding maximum hold time of {MAX_HOLD_TIME_HOURS} hours"
        send_discord_notification(message)
        return True

    if elapsed_time > timedelta(hours=1) and profit_ratio >= PARTIAL_PROFIT_RATIO:
        message = f"Closing 30% of position for {symbol} after 1 hour with profit ratio {profit_ratio * 100:.2f}%"
        send_discord_notification(message)
        close_partial_position(symbol, PARTIAL_CLOSE_1H)

    if elapsed_time > timedelta(hours=2) and profit_ratio >= PARTIAL_PROFIT_RATIO:
        message = f"Closing 50% of position for {symbol} after 2 hours with profit ratio {profit_ratio * 100:.2f}%"
        send_discord_notification(message)
        close_partial_position(symbol, PARTIAL_CLOSE_2H)

    return False

# Kiểm tra vị thế hiện tại và đóng lệnh nếu thỏa mãn điều kiện
def check_and_close_positions():
    open_positions = get_open_positions()
    for pos in open_positions:
        if should_close_position(pos):
            close_partial_position(pos['symbol'], 1.0)  # Đóng toàn bộ nếu thỏa mãn điều kiện

# Chạy kiểm tra khi file được gọi trực tiếp
if __name__ == "__main__":
    check_and_close_positions()


