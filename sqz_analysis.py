import os
import ccxt
import pandas as pd
import pandas_ta as ta

def sqz(n=20, timeframe='15m', limit_candles=120):
    binance = ccxt.binance()
    tickers = binance.fetch_tickers()
    stablecoins = ['USDC/USDT', 'BUSD/USDT', 'TUSD/USDT', 'DAI/USDT', 'FDUSD/USDT', 'USDP/USDT', 'GUSD/USDT']
    symbols = [s for s in tickers if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s and s not in stablecoins]
    symbols = sorted(symbols, key=lambda x: tickers[x]['quoteVolume'], reverse=True)

    for symbol in symbols[:n]:
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit_candles)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        df.ta.squeeze(append=True, lazybear=True)
        df[['SQZ_ON', 'SQZ_OFF', 'SQZ_NO']] = df[['SQZ_ON', 'SQZ_OFF', 'SQZ_NO']].fillna(0)

        df['SQZ_Duration'] = (
            df['SQZ_ON']
            .groupby((df['SQZ_ON'] != df['SQZ_ON'].shift()).cumsum())
            .cumsum()
            .where(df['SQZ_ON'] == 1, 0)
        )

        max_sqz_duration = df['SQZ_Duration'].max()
        if max_sqz_duration > 0:
<<<<<<< HEAD
            print(f"{symbol}: Nén dài nhất là {max_sqz_duration} nến")

if __name__ == "__main__":
    sqz(20, '15m', 100)
=======
            print(f"{symbol}: Nén dài nhất là {max_sqz_duration} nến")
>>>>>>> 829df27 (Cập nhật code với nhiều hàm mới)
