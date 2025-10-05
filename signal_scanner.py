"""
Scanner tín hiệu - Quét và phát hiện 2 loại tín hiệu:
1. Stoch + S/R (kiểm tra cả M15 và H1)
2. Stoch + CVD
"""

import pandas as pd
import ccxt
import pytz
from datetime import datetime
from cvd_indicator import CVDIndicator
from stochastic_indicator import StochasticIndicator
from support_resistance import SupportResistanceChannel
import config

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


class SignalScanner:
    """
    Lớp quét tín hiệu giao dịch - hỗ trợ 2 loại tín hiệu độc lập
    """
    
    def __init__(self):
        """Khởi tạo scanner"""
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.cvd = CVDIndicator(
            divergence_period=config.CVD_DIVERGENCE_PERIOD,
            cvd_period=config.CVD_PERIOD,
            cumulative_mode=config.CVD_CUMULATIVE_MODE,
            min_swing_distance=config.CVD_MIN_SWING_DISTANCE
        )
        self.stoch = StochasticIndicator(
            k_period=config.STOCH_K_PERIOD,
            k_smooth=config.STOCH_K_SMOOTH,
            d_smooth=config.STOCH_D_SMOOTH
        )
        # S/R cho H1
        self.sr = SupportResistanceChannel(
            pivot_period=config.SR_PIVOT_PERIOD,
            channel_width_percent=config.SR_CHANNEL_WIDTH_PERCENT,
            loopback_period=config.SR_LOOPBACK_PERIOD,
            min_strength=config.SR_MIN_STRENGTH,
            max_channels=config.SR_MAX_CHANNELS
        )
        # S/R cho M15
        self.sr_m15 = SupportResistanceChannel(
            pivot_period=config.SR_M15_PIVOT_PERIOD,
            channel_width_percent=config.SR_M15_CHANNEL_WIDTH_PERCENT,
            loopback_period=config.SR_M15_LOOPBACK_PERIOD,
            min_strength=config.SR_M15_MIN_STRENGTH,
            max_channels=config.SR_M15_MAX_CHANNELS
        )
    
    def fetch_data(self, symbol, timeframe, limit=100):
        """Lấy dữ liệu từ Binance"""
        try:
            if '/' not in symbol:
                symbol = symbol[:-4] + '/' + symbol[-4:]
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df['timestamp'] = df['timestamp'].dt.tz_convert(VIETNAM_TZ)
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Lỗi khi lấy dữ liệu {symbol}: {str(e)}")
            return None
    
    def check_all_signals(self, symbol):
        """Kiểm tra TẤT CẢ loại tín hiệu cho 1 symbol"""
        result = {
            'stoch_sr': None,
            'stoch_cvd': None
        }
        
        try:
            # Lấy dữ liệu
            df_m15 = self.fetch_data(symbol, '15m', limit=300)
            df_h1 = self.fetch_data(symbol, '1h', limit=500)
            
            if df_m15 is None or df_h1 is None:
                return result
            
            # Tính Stochastic
            stoch_k_m15, _ = self.stoch.calculate(df_m15)
            stoch_k_h1, _ = self.stoch.calculate(df_h1)
            
            # Kiểm tra Signal Type 1: Stoch + S/R
            if config.SIGNAL_STOCH_SR_ENABLED:
                result['stoch_sr'] = self._check_signal_stoch_sr(
                    symbol, df_m15, df_h1, stoch_k_m15, stoch_k_h1
                )
            
            # Kiểm tra Signal Type 2: Stoch + CVD
            if config.SIGNAL_STOCH_CVD_ENABLED:
                result['stoch_cvd'] = self._check_signal_stoch_cvd(
                    symbol, df_m15, df_h1, stoch_k_m15, stoch_k_h1
                )
            
            return result
            
        except Exception as e:
            print(f"Lỗi khi kiểm tra tín hiệu {symbol}: {str(e)}")
            return result
    
    def _check_signal_stoch_sr(self, symbol, df_m15, df_h1, stoch_k_m15, stoch_k_h1):
        """
        Signal Type 1: Stoch + S/R
        - Kiểm tra Stoch trước
        - Kiểm tra 4 nến M15 trong nến H1
        - Kiểm tra nến H1
        """
        try:
            stoch_h1_value = stoch_k_h1.iloc[-1]
            stoch_m15_value = stoch_k_m15.iloc[-1]
            signal_time = df_h1.index[-1]
            candle_close = df_h1['close'].iloc[-1]
            
            # Kiểm tra Stoch điều kiện trước
            is_long = stoch_h1_value < 25 and stoch_m15_value < 25
            is_short = stoch_h1_value > 75 and stoch_m15_value > 75
            
            if not (is_long or is_short):
                return None
            
            # Tính S/R H1
            sr_h1 = self.sr.analyze(df_h1)
            
            # Tính S/R M15
            sr_m15 = self.sr_m15.analyze(df_m15)
            
            timeframes_touched = []
            
            # Check H1
            if sr_h1['success']:
                h1_low = df_h1['low'].iloc[-1]
                h1_high = df_h1['high'].iloc[-1]
                h1_close = df_h1['close'].iloc[-1]
                
                if is_long:
                    if self._check_candle_touching_support(sr_h1, h1_low, h1_high, h1_close):
                        timeframes_touched.append('H1')
                else:  # SHORT
                    if self._check_candle_touching_resistance(sr_h1, h1_low, h1_high, h1_close):
                        timeframes_touched.append('H1')
            
            # Check 4 nến M15 trong nến H1
            if sr_m15['success']:
                # Lấy 4 nến M15 cuối (trong nến H1 hiện tại)
                last_4_m15 = df_m15.iloc[-4:]
                
                m15_touched = False
                for i in range(len(last_4_m15)):
                    m15_low = last_4_m15['low'].iloc[i]
                    m15_high = last_4_m15['high'].iloc[i]
                    m15_close = last_4_m15['close'].iloc[i]
                    
                    if is_long:
                        if self._check_candle_touching_support(sr_m15, m15_low, m15_high, m15_close):
                            m15_touched = True
                            break
                    else:  # SHORT
                        if self._check_candle_touching_resistance(sr_m15, m15_low, m15_high, m15_close):
                            m15_touched = True
                            break
                
                if m15_touched:
                    timeframes_touched.insert(0, 'M15')  # M15 đứng trước
            
            # Tạo signal nếu có ít nhất 1 khung chạm
            if timeframes_touched:
                return {
                    'symbol': symbol,
                    'signal_type': 'BUY' if is_long else 'SELL',
                    'signal_category': 'STOCH_SR',
                    'price': candle_close,
                    'signal_time': signal_time,
                    'confirm_time': datetime.now(VIETNAM_TZ),
                    'stoch_m15': stoch_m15_value,
                    'stoch_h1': stoch_h1_value,
                    'signal_id': f"{symbol}_{signal_time.strftime('%Y%m%d%H%M')}_{'BUY' if is_long else 'SELL'}_SR",
                    'timeframes': ' & '.join(timeframes_touched),
                    'sr_type': 'support' if is_long else 'resistance'
                }
            
            return None
            
        except Exception as e:
            print(f"Lỗi _check_signal_stoch_sr: {str(e)}")
            return None
    
    def _check_signal_stoch_cvd(self, symbol, df_m15, df_h1, stoch_k_m15, stoch_k_h1):
        """Signal Type 2: Stoch + CVD"""
        try:
            cvd_values = self.cvd.calculate_cvd(df_h1)
            divergence_info = self._detect_divergence_h1(df_h1, cvd_values)
            
            if not divergence_info:
                return None
            
            signal_time = divergence_info['time']
            
            try:
                h1_idx = df_h1.index.get_loc(signal_time)
            except KeyError:
                h1_idx = df_h1.index.get_indexer([signal_time], method='nearest')[0]
            
            stoch_h1_value = stoch_k_h1.iloc[h1_idx]
            m15_idx = df_m15.index.get_indexer([signal_time], method='nearest')[0]
            stoch_m15_value = stoch_k_m15.iloc[m15_idx]
            
            signal = None
            
            if divergence_info['type'] == 'bullish':
                if stoch_h1_value < 25 and stoch_m15_value < 25:
                    signal = {
                        'symbol': symbol,
                        'signal_type': 'BUY',
                        'signal_category': 'STOCH_CVD',
                        'price': df_h1['close'].iloc[h1_idx],
                        'signal_time': signal_time,
                        'confirm_time': datetime.now(VIETNAM_TZ),
                        'stoch_m15': stoch_m15_value,
                        'stoch_h1': stoch_h1_value,
                        'signal_id': f"{symbol}_{signal_time.strftime('%Y%m%d%H%M')}_BUY_CVD",
                        'cvd_info': {
                            'prev_cvd': divergence_info.get('prev_cvd'),
                            'curr_cvd': divergence_info.get('curr_cvd')
                        }
                    }
            
            elif divergence_info['type'] == 'bearish':
                if stoch_h1_value > 75 and stoch_m15_value > 75:
                    signal = {
                        'symbol': symbol,
                        'signal_type': 'SELL',
                        'signal_category': 'STOCH_CVD',
                        'price': df_h1['close'].iloc[h1_idx],
                        'signal_time': signal_time,
                        'confirm_time': datetime.now(VIETNAM_TZ),
                        'stoch_m15': stoch_m15_value,
                        'stoch_h1': stoch_h1_value,
                        'signal_id': f"{symbol}_{signal_time.strftime('%Y%m%d%H%M')}_SELL_CVD",
                        'cvd_info': {
                            'prev_cvd': divergence_info.get('prev_cvd'),
                            'curr_cvd': divergence_info.get('curr_cvd')
                        }
                    }
            
            return signal
            
        except Exception as e:
            print(f"Lỗi _check_signal_stoch_cvd: {str(e)}")
            return None
    
    def _detect_divergence_h1(self, df_h1, cvd_values):
        """Phát hiện phân kỳ CVD trên H1 - CHỈ KIỂM TRA 30 NẾN GẦN NHẤT"""
        try:
            ema_50 = df_h1['close'].ewm(span=50, adjust=False).mean()
            n = config.CVD_DIVERGENCE_PERIOD
            min_distance = config.CVD_MIN_SWING_DISTANCE
            
            # CHỈ KIỂM TRA 30 NẾN GẦN NHẤT
            start_idx = max(n, len(df_h1) - 30)
            
            # Tìm pivot high (bearish divergence)
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
                        'idx': i,
                        'time': df_h1.index[i],
                        'price': df_h1['high'].iloc[i],
                        'cvd': cvd_values.iloc[i]
                    })
            
            # Kiểm tra phân kỳ giảm
            if len(pivot_highs) >= 2:
                prev = pivot_highs[-2]
                curr = pivot_highs[-1]
                distance = curr['idx'] - prev['idx']
                
                if distance >= min_distance and distance < 30:
                    if curr['price'] > prev['price'] and curr['cvd'] < prev['cvd'] and \
                       curr['cvd'] > 0 and prev['cvd'] > 0:
                        return {
                            'type': 'bearish',
                            'time': curr['time'],
                            'prev_cvd': prev['cvd'],
                            'curr_cvd': curr['cvd']
                        }
            
            # Tìm pivot low (bullish divergence)
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
                        'idx': i,
                        'time': df_h1.index[i],
                        'price': df_h1['low'].iloc[i],
                        'cvd': cvd_values.iloc[i]
                    })
            
            # Kiểm tra phân kỳ tăng
            if len(pivot_lows) >= 2:
                prev = pivot_lows[-2]
                curr = pivot_lows[-1]
                distance = curr['idx'] - prev['idx']
                
                if distance >= min_distance and distance < 30:
                    if curr['price'] < prev['price'] and curr['cvd'] > prev['cvd'] and \
                       curr['cvd'] < 0 and prev['cvd'] < 0:
                        return {
                            'type': 'bullish',
                            'time': curr['time'],
                            'prev_cvd': prev['cvd'],
                            'curr_cvd': curr['cvd']
                        }
            
            return None
            
        except Exception as e:
            print(f"Lỗi khi phát hiện phân kỳ: {str(e)}")
            return None
    
    def _check_candle_touching_support(self, result, candle_low, candle_high, candle_close):
        """Kiểm tra Price Action với Support"""
        if not result['success']:
            return False
        
        for support in result['supports']:
            zone_low = support['low']
            zone_high = support['high']
            
            if candle_close > zone_low and candle_low <= zone_high:
                return True
        
        if result['in_channel']:
            channel = result['in_channel']
            zone_low = channel['low']
            zone_high = channel['high']
            
            mid_price = (candle_low + candle_high) / 2
            distance_to_low = abs(mid_price - zone_low)
            distance_to_high = abs(mid_price - zone_high)
            
            if distance_to_low < distance_to_high:
                if candle_close > zone_low and candle_low <= zone_high:
                    return True
        
        return False
    
    def _check_candle_touching_resistance(self, result, candle_low, candle_high, candle_close):
        """Kiểm tra Price Action với Resistance"""
        if not result['success']:
            return False
        
        for resistance in result['resistances']:
            zone_low = resistance['low']
            zone_high = resistance['high']
            
            if candle_close < zone_high and candle_high >= zone_low:
                return True
        
        if result['in_channel']:
            channel = result['in_channel']
            zone_low = channel['low']
            zone_high = channel['high']
            
            mid_price = (candle_low + candle_high) / 2
            distance_to_low = abs(mid_price - zone_low)
            distance_to_high = abs(mid_price - zone_high)
            
            if distance_to_high < distance_to_low:
                if candle_close < zone_high and candle_high >= zone_low:
                    return True
        
        return False