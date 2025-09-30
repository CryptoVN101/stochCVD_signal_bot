"""
Scanner tín hiệu - Quét và phát hiện tín hiệu giao dịch
"""

import pandas as pd
import ccxt
import pytz
from datetime import datetime
from cvd_indicator import CVDIndicator
from stochastic_indicator import StochasticIndicator
import config

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


class SignalScanner:
    """
    Lớp quét tín hiệu giao dịch
    """
    
    def __init__(self):
        """Khởi tạo scanner"""
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.cvd = CVDIndicator(
            divergence_period=config.CVD_DIVERGENCE_PERIOD,
            cvd_period=config.CVD_PERIOD,
            cumulative_mode=config.CVD_CUMULATIVE_MODE
        )
        self.stoch = StochasticIndicator(
            k_period=config.STOCH_K_PERIOD,
            k_smooth=config.STOCH_K_SMOOTH,
            d_smooth=config.STOCH_D_SMOOTH
        )
    
    def fetch_data(self, symbol, timeframe, limit=100):
        """
        Lấy dữ liệu từ Binance
        
        Args:
            symbol: Cặp coin (ví dụ: 'BTCUSDT')
            timeframe: Khung thời gian ('15m', '1h')
            limit: Số nến
            
        Returns:
            DataFrame hoặc None nếu lỗi
        """
        try:
            # Chuyển format BTCUSDT thành BTC/USDT cho ccxt
            if '/' not in symbol:
                symbol = symbol[:-4] + '/' + symbol[-4:]
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Chuyển sang giờ Việt Nam
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df['timestamp'] = df['timestamp'].dt.tz_convert(VIETNAM_TZ)
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Lỗi khi lấy dữ liệu {symbol}: {str(e)}")
            return None
    
    def check_signal(self, symbol):
        """
        Kiểm tra tín hiệu cho 1 symbol
        
        Args:
            symbol: Mã coin (ví dụ: 'BTCUSDT')
            
        Returns:
            dict hoặc None nếu không có tín hiệu
        """
        try:
            # Lấy dữ liệu (chỉ 100 nến thay vì 500)
            df_m15 = self.fetch_data(symbol, '15m', limit=200)
            df_h1 = self.fetch_data(symbol, '1h', limit=100)
            
            if df_m15 is None or df_h1 is None:
                return None
            
            # Tính CVD trên H1
            cvd_values = self.cvd.calculate_cvd(df_h1)
            
            # Tính Stochastic
            stoch_k_m15, _ = self.stoch.calculate(df_m15)
            stoch_k_h1, _ = self.stoch.calculate(df_h1)
            
            # Tìm phân kỳ CVD trên H1 (CHỈ KIỂM TRA 30 NẾN GẦN NHẤT)
            divergence_info = self._detect_divergence_h1(df_h1, cvd_values)
            
            if not divergence_info:
                return None
            
            # Lấy giá trị Stoch tại thời điểm phân kỳ
            signal_time = divergence_info['time']
            
            # Lấy Stoch H1 tại thời điểm phân kỳ
            try:
                h1_idx = df_h1.index.get_loc(signal_time)
            except KeyError:
                # Nếu không tìm thấy exact match, tìm gần nhất
                h1_idx = df_h1.index.get_indexer([signal_time], method='nearest')[0]
            
            stoch_h1_value = stoch_k_h1.iloc[h1_idx]
            
            # Lấy Stoch M15 gần nhất
            m15_idx = df_m15.index.get_indexer([signal_time], method='nearest')[0]
            stoch_m15_value = stoch_k_m15.iloc[m15_idx]
            
            # Kiểm tra điều kiện tín hiệu
            signal = None
            
            if divergence_info['type'] == 'bullish':
                # Tín hiệu BUY: Stoch H1 < 25 & M15 < 25
                if stoch_h1_value < 25 and stoch_m15_value < 25:
                    signal = {
                        'symbol': symbol,
                        'signal_type': 'BUY',
                        'price': df_h1['close'].iloc[h1_idx],
                        'signal_time': signal_time,
                        'confirm_time': datetime.now(VIETNAM_TZ),
                        'stoch_m15': stoch_m15_value,
                        'stoch_h1': stoch_h1_value,
                        'signal_id': f"{symbol}_{signal_time.strftime('%Y%m%d%H%M')}_BUY"
                    }
            
            elif divergence_info['type'] == 'bearish':
                # Tín hiệu SELL: Stoch H1 > 75 & M15 > 75
                if stoch_h1_value > 75 and stoch_m15_value > 75:
                    signal = {
                        'symbol': symbol,
                        'signal_type': 'SELL',
                        'price': df_h1['close'].iloc[h1_idx],
                        'signal_time': signal_time,
                        'confirm_time': datetime.now(VIETNAM_TZ),
                        'stoch_m15': stoch_m15_value,
                        'stoch_h1': stoch_h1_value,
                        'signal_id': f"{symbol}_{signal_time.strftime('%Y%m%d%H%M')}_SELL"
                    }
            
            return signal
            
        except Exception as e:
            print(f"Lỗi khi kiểm tra tín hiệu {symbol}: {str(e)}")
            return None
    
    def _detect_divergence_h1(self, df_h1, cvd_values):
        """
        Phát hiện phân kỳ CVD trên H1 - CHỈ KIỂM TRA 30 NẾN GẦN NHẤT
        
        Returns:
            dict hoặc None
        """
        try:
            ema_50 = df_h1['close'].ewm(span=50, adjust=False).mean()
            n = config.CVD_DIVERGENCE_PERIOD
            
            # CHỈ KIỂM TRA 30 NẾN GẦN NHẤT (quan trọng!)
            start_idx = max(n, len(df_h1) - 30)
            
            # Tìm pivot high (bearish divergence) - chỉ trong 30 nến cuối
            pivot_highs = []
            for i in range(start_idx, len(df_h1) - n):
                is_pivot = True
                for j in range(1, n + 1):
                    if df_h1['high'].iloc[i] <= df_h1['high'].iloc[i - j] or \
                       df_h1['high'].iloc[i] <= df_h1['high'].iloc[i + j]:
                        is_pivot = False
                        break
                
                if is_pivot and df_h1['close'].iloc[i] > ema_50.iloc[i]:
                    pivot_highs.append({
                        'time': df_h1.index[i],
                        'price': df_h1['high'].iloc[i],
                        'cvd': cvd_values.iloc[i]
                    })
            
            # Kiểm tra phân kỳ giảm (lấy 2 pivot cuối)
            if len(pivot_highs) >= 2:
                prev = pivot_highs[-2]
                curr = pivot_highs[-1]
                
                time_diff = (curr['time'] - prev['time']).total_seconds() / 3600
                
                if time_diff < 30:
                    if curr['price'] > prev['price'] and curr['cvd'] < prev['cvd'] and \
                       curr['cvd'] > 0 and prev['cvd'] > 0:
                        return {
                            'type': 'bearish',
                            'time': curr['time']
                        }
            
            # Tìm pivot low (bullish divergence) - chỉ trong 30 nến cuối
            pivot_lows = []
            for i in range(start_idx, len(df_h1) - n):
                is_pivot = True
                for j in range(1, n + 1):
                    if df_h1['low'].iloc[i] >= df_h1['low'].iloc[i - j] or \
                       df_h1['low'].iloc[i] >= df_h1['low'].iloc[i + j]:
                        is_pivot = False
                        break
                
                if is_pivot and df_h1['close'].iloc[i] < ema_50.iloc[i]:
                    pivot_lows.append({
                        'time': df_h1.index[i],
                        'price': df_h1['low'].iloc[i],
                        'cvd': cvd_values.iloc[i]
                    })
            
            # Kiểm tra phân kỳ tăng (lấy 2 pivot cuối)
            if len(pivot_lows) >= 2:
                prev = pivot_lows[-2]
                curr = pivot_lows[-1]
                
                time_diff = (curr['time'] - prev['time']).total_seconds() / 3600
                
                if time_diff < 30:
                    if curr['price'] < prev['price'] and curr['cvd'] > prev['cvd'] and \
                       curr['cvd'] < 0 and prev['cvd'] < 0:
                        return {
                            'type': 'bullish',
                            'time': curr['time']
                        }
            
            return None
            
        except Exception as e:
            print(f"Lỗi khi phát hiện phân kỳ: {str(e)}")
            return None