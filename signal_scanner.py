"""
Scanner tín hiệu - Stoch + S/R
Logic S/R từ TradingView (support_resistance_channel.py)

ĐIỀU KIỆN STOCH (SIẾT CHẶT M15):
- LONG: H1 %D < 25 & M15 %D < 20
- SHORT: H1 %K > 75 & M15 %K > 80

LOGIC ĐƠN GIẢN - CHỈ CHECK OPEN:
- LONG: Nến trước Open ≥ ch_high → Giá giảm vào support
- SHORT: Nến trước Open ≤ ch_low → Giá tăng vào resistance
"""

import pandas as pd
import ccxt
import pytz
from datetime import datetime
from stochastic_indicator import StochasticIndicator
from support_resistance import SupportResistanceChannel
import config

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


class SignalScanner:
    """Lớp quét tín hiệu - STOCH + S/R"""
    
    def __init__(self):
        """Khởi tạo scanner"""
        self.exchange = ccxt.binance({'enableRateLimit': True})
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
    
    def check_signal(self, symbol):
        """Kiểm tra tín hiệu Stoch + S/R"""
        try:
            df_m15 = self.fetch_data(symbol, '15m', limit=300)
            df_h1 = self.fetch_data(symbol, '1h', limit=500)
            
            if df_m15 is None or df_h1 is None:
                return None
            
            # Tính Stochastic - LẤY CẢ %K VÀ %D
            stoch_k_m15, stoch_d_m15 = self.stoch.calculate(df_m15)
            stoch_k_h1, stoch_d_h1 = self.stoch.calculate(df_h1)
            
            return self._check_signal_stoch_sr(
                symbol, df_m15, df_h1, 
                stoch_k_m15, stoch_d_m15, 
                stoch_k_h1, stoch_d_h1
            )
            
        except Exception as e:
            print(f"Lỗi khi kiểm tra tín hiệu {symbol}: {str(e)}")
            return None
    
    def _check_signal_stoch_sr(self, symbol, df_m15, df_h1, 
                                stoch_k_m15, stoch_d_m15, 
                                stoch_k_h1, stoch_d_h1):
        """
        Signal: Stoch + S/R - Logic đơn giản: Chỉ check Open
        """
        try:
            # Lấy giá trị Stoch hiện tại
            stoch_d_h1_value = stoch_d_h1.iloc[-1]
            stoch_d_m15_value = stoch_d_m15.iloc[-1]
            stoch_k_h1_value = stoch_k_h1.iloc[-1]
            stoch_k_m15_value = stoch_k_m15.iloc[-1]
            
            signal_time = df_h1.index[-1]
            candle_close = df_h1['close'].iloc[-1]
            
            # ĐIỀU KIỆN STOCH
            is_long = stoch_d_h1_value < 25 and stoch_d_m15_value < 20
            is_short = stoch_k_h1_value > 75 and stoch_k_m15_value > 80
            
            if not (is_long or is_short):
                return None
            
            # Tính S/R
            sr_h1 = self.sr.analyze(df_h1)
            sr_m15 = self.sr_m15.analyze(df_m15)
            
            timeframes_touched = []
            
            # ========================================================================
            # CHECK H1 - LOGIC ĐƠN GIẢN
            # ========================================================================
            if sr_h1['success'] and sr_h1['in_channel']:
                h1_low = df_h1['low'].iloc[-1]
                h1_high = df_h1['high'].iloc[-1]
                h1_close = df_h1['close'].iloc[-1]
                h1_open = df_h1['open'].iloc[-1]
                
                channel = sr_h1['in_channel']
                ch_low = channel['low']
                ch_high = channel['high']
                ch_mid = (ch_low + ch_high) / 2
                
                if is_long:
                    # LONG: Nến hiện tại
                    current_in_upper = h1_close > ch_mid
                    current_in_channel = h1_close > ch_low and h1_close < ch_high
                    
                    if current_in_upper and current_in_channel and len(df_h1) > 1:
                        # Nến trước: Open trên channel
                        prev_h1_open = df_h1['open'].iloc[-2]
                        prev_valid = prev_h1_open >= ch_high
                        
                        if prev_valid:
                            # Nến hiện tại chạm support
                            if h1_low <= ch_high and h1_close > ch_low:
                                timeframes_touched.append('H1')
                
                elif is_short:
                    # SHORT: Nến hiện tại
                    current_in_lower = h1_close < ch_mid
                    current_in_channel = h1_close > ch_low and h1_close < ch_high
                    
                    if current_in_lower and current_in_channel and len(df_h1) > 1:
                        # Nến trước: Open dưới channel
                        prev_h1_open = df_h1['open'].iloc[-2]
                        prev_valid = prev_h1_open <= ch_low
                        
                        if prev_valid:
                            # Nến hiện tại chạm resistance
                            if h1_high >= ch_low and h1_close < ch_high:
                                timeframes_touched.append('H1')
            
            # ========================================================================
            # CHECK 4 NẾN M15 - LOGIC ĐƠN GIẢN
            # ========================================================================
            if sr_m15['success'] and sr_m15['in_channel']:
                last_4_m15 = df_m15.iloc[-4:]
                
                channel = sr_m15['in_channel']
                ch_low = channel['low']
                ch_high = channel['high']
                ch_mid = (ch_low + ch_high) / 2
                
                m15_touched = False
                
                for i in range(len(last_4_m15)):
                    m15_low = last_4_m15['low'].iloc[i]
                    m15_high = last_4_m15['high'].iloc[i]
                    m15_close = last_4_m15['close'].iloc[i]
                    m15_open = last_4_m15['open'].iloc[i]
                    
                    if is_long:
                        # LONG: Nến hiện tại
                        current_in_upper = m15_close > ch_mid
                        current_in_channel = m15_close > ch_low and m15_close < ch_high
                        
                        if current_in_upper and current_in_channel:
                            # Check nến trước (nếu có)
                            if i > 0:
                                prev_m15_open = last_4_m15['open'].iloc[i-1]
                                
                                # ĐƠN GIẢN: Chỉ cần Open trên channel
                                prev_valid = prev_m15_open >= ch_high
                                
                                if prev_valid:
                                    # Nến hiện tại chạm support
                                    if m15_low <= ch_high and m15_close > ch_low:
                                        m15_touched = True
                                        break
                            else:
                                # Nến đầu tiên - bỏ qua check nến trước
                                if m15_low <= ch_high and m15_close > ch_low:
                                    m15_touched = True
                                    break
                    
                    elif is_short:
                        # SHORT: Nến hiện tại
                        current_in_lower = m15_close < ch_mid
                        current_in_channel = m15_close > ch_low and m15_close < ch_high
                        
                        if current_in_lower and current_in_channel:
                            if i > 0:
                                prev_m15_open = last_4_m15['open'].iloc[i-1]
                                
                                # ĐƠN GIẢN: Chỉ cần Open dưới channel
                                prev_valid = prev_m15_open <= ch_low
                                
                                if prev_valid:
                                    # Nến hiện tại chạm resistance
                                    if m15_high >= ch_low and m15_close < ch_high:
                                        m15_touched = True
                                        break
                            else:
                                if m15_high >= ch_low and m15_close < ch_high:
                                    m15_touched = True
                                    break
                
                if m15_touched:
                    timeframes_touched.insert(0, 'M15')
            
            # Tạo signal
            if timeframes_touched:
                return {
                    'symbol': symbol,
                    'signal_type': 'BUY' if is_long else 'SELL',
                    'price': candle_close,
                    'signal_time': signal_time,
                    'confirm_time': datetime.now(VIETNAM_TZ),
                    'stoch_k_m15': stoch_k_m15_value,
                    'stoch_d_m15': stoch_d_m15_value,
                    'stoch_k_h1': stoch_k_h1_value,
                    'stoch_d_h1': stoch_d_h1_value,
                    'signal_id': f"{symbol}_{signal_time.strftime('%Y%m%d%H%M')}_{'BUY' if is_long else 'SELL'}_SR",
                    'timeframes': ' & '.join(timeframes_touched),
                    'sr_type': 'support' if is_long else 'resistance'
                }
            
            return None
            
        except Exception as e:
            print(f"Lỗi _check_signal_stoch_sr: {str(e)}")
            import traceback
            traceback.print_exc()
            return None