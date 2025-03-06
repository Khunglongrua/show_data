import os
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from ta.trend import IchimokuIndicator

def ve_ichimoku(symbol, timeframe='15m', limit_candles=120):
    # Initialize Binance object using ccxt
    binance = ccxt.binance()

    # Fetch candles data
    def get_candles(symbol, timeframe, limit=120):
        if not '/' in symbol:
            symbol = symbol.replace("USDT", "/USDT")
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    df = get_candles(symbol, timeframe, limit_candles)
    ichimoku = IchimokuIndicator(high=df['high'], low=df['low'], window1=9, window2=26, window3=52)
    df['tenkan_sen'] = ichimoku.ichimoku_conversion_line()
    df['kijun_sen'] = ichimoku.ichimoku_base_line()
    df['senkou_span_a'] = ichimoku.ichimoku_a()
    df['senkou_span_b'] = ichimoku.ichimoku_b()
    df['chikou_span'] = df['close'].shift(-26)

    # Không xóa NaN để giữ đường Chikou Span thẳng
    df.ffill(inplace=True)  # Điền giá trị còn thiếu

    apds = [
        mpf.make_addplot(df['tenkan_sen'], color='blue', linestyle='--', width=1),
        mpf.make_addplot(df['kijun_sen'], color='red', linestyle='--', width=1),
        mpf.make_addplot(df['senkou_span_a'], color='green', width=1),
        mpf.make_addplot(df['senkou_span_b'], color='brown', width=1),
        mpf.make_addplot(df['chikou_span'], color='purple', linestyle=':', width=1)
    ]

    mc = mpf.make_marketcolors(up='#26A69A', down='#EF5350', wick='black', edge='black', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='-', rc={'font.size': 10})

    mpf.plot(df, type='candle', style=s, volume=True, addplot=apds,
             title=f'{symbol} - Ichimoku Cloud',
             ylabel='Price',
             ylabel_lower='Volume',
             figsize=(18, 9),
             fill_between=[
                dict(
                    y1=df['senkou_span_a'].values,
                    y2=df['senkou_span_b'].values,
                    where=(df['senkou_span_a'] >= df['senkou_span_b']),
                    alpha=0.3, color='green'
                ),
                dict(
                    y1=df['senkou_span_a'].values,
                    y2=df['senkou_span_b'].values,
                    where=(df['senkou_span_a'] < df['senkou_span_b']),
                    alpha=0.3, color='red'
                )
             ])
