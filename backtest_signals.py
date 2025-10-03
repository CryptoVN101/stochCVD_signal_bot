"""
Backtest tín hiệu - Quét toàn bộ lịch sử để tìm tín hiệu
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


class SignalBacktest:
    """
    Lớp backtest tín hiệu - quét toàn bộ lịch sử
    """
    
    def __init__(self):
        """Khởi tạo backtest"""
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
        self.sr = SupportResistanceChannel(
            pivot_period=config.SR_PIVOT_PERIOD,
            channel_width_percent=config.SR_CHANNEL_WIDTH_PERCENT,
            loopback_period=config.SR_LOOPBACK_PERIOD,
            min_strength=config.SR_MIN_STRENGTH,
            max_channels=config.SR_MAX_CHANNELS
        )
    
    def fetch_data(self, symbol, timeframe, limit=1000):
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
    
    def find_all_divergences(self, df_h1, cvd_values):
        """
        Tìm TẤT CẢ phân kỳ CVD trong toàn bộ lịch sử
        
        Returns:
            list: Danh sách các phân kỳ
        """
        try:
            ema_50 = df_h1['close'].ewm(span=50, adjust=False).mean()
            n = config.CVD_DIVERGENCE_PERIOD
            
            all_divergences = []
            
            # QUÉT TOÀN BỘ - không giới hạn 30 nến
            start_idx = n
            end_idx = len(df_h1) - n
            
            # Tìm tất cả pivot high (bearish)
            pivot_highs = []
            for i in range(start_idx, end_idx):
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
            
            # Tìm phân kỳ giảm
            for i in range(1, len(pivot_highs)):
                prev = pivot_highs[i-1]
                curr = pivot_highs[i]
                
                time_diff = (curr['time'] - prev['time']).total_seconds() / 3600
                
                if time_diff < 30:
                    if curr['price'] > prev['price'] and curr['cvd'] < prev['cvd'] and \
                       curr['cvd'] > 0 and prev['cvd'] > 0:
                        all_divergences.append({
                            'type': 'bearish',
                            'time': curr['time'],
                            'idx': curr['idx'],
                            'prev_price': prev['price'],
                            'curr_price': curr['price'],
                            'prev_cvd': prev['cvd'],
                            'curr_cvd': curr['cvd']
                        })
            
            # Tìm tất cả pivot low (bullish)
            pivot_lows = []
            for i in range(start_idx, end_idx):
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
            
            # Tìm phân kỳ tăng
            for i in range(1, len(pivot_lows)):
                prev = pivot_lows[i-1]
                curr = pivot_lows[i]
                
                time_diff = (curr['time'] - prev['time']).total_seconds() / 3600
                
                if time_diff < 30:
                    if curr['price'] < prev['price'] and curr['cvd'] > prev['cvd'] and \
                       curr['cvd'] < 0 and prev['cvd'] < 0:
                        all_divergences.append({
                            'type': 'bullish',
                            'time': curr['time'],
                            'idx': curr['idx'],
                            'prev_price': prev['price'],
                            'curr_price': curr['price'],
                            'prev_cvd': prev['cvd'],
                            'curr_cvd': curr['cvd']
                        })
            
            return all_divergences
            
        except Exception as e:
            print(f"Lỗi khi tìm phân kỳ: {str(e)}")
            return []
    
    def check_candle_touching_support(self, result, candle_low, candle_high, candle_close):
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
    
    def check_candle_touching_resistance(self, result, candle_low, candle_high, candle_close):
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
    
    def backtest_symbol(self, symbol, limit=1000):
        """
        Backtest toàn bộ lịch sử cho 1 symbol
        
        Args:
            symbol: Mã coin (ví dụ: 'BTCUSDT')
            limit: Số nến H1 cần lấy
            
        Returns:
            list: Danh sách tín hiệu tìm được
        """
        print(f"\n{'='*70}")
        print(f"BACKTEST: {symbol}")
        print(f"{'='*70}")
        
        # Lấy dữ liệu
        df_m15 = self.fetch_data(symbol, '15m', limit=limit)
        df_h1 = self.fetch_data(symbol, '1h', limit=limit)
        
        if df_m15 is None or df_h1 is None:
            return []
        
        print(f"Dữ liệu H1: {len(df_h1)} nến")
        print(f"Từ: {df_h1.index[0].strftime('%H:%M %d-%m-%Y')}")
        print(f"Đến: {df_h1.index[-1].strftime('%H:%M %d-%m-%Y')}")
        
        # Tính CVD và Stochastic
        cvd_values = self.cvd.calculate_cvd(df_h1)
        stoch_k_m15, _ = self.stoch.calculate(df_m15)
        stoch_k_h1, _ = self.stoch.calculate(df_h1)
        
        # Tìm tất cả phân kỳ
        print(f"\nĐang tìm tất cả phân kỳ CVD...")
        all_divergences = self.find_all_divergences(df_h1, cvd_values)
        print(f"Tìm thấy {len(all_divergences)} phân kỳ")
        
        # Kiểm tra từng phân kỳ
        signals = []
        
        for div in all_divergences:
            h1_idx = div['idx']
            signal_time = div['time']
            
            # Lấy Stochastic
            stoch_h1_value = stoch_k_h1.iloc[h1_idx]
            m15_idx = df_m15.index.get_indexer([signal_time], method='nearest')[0]
            stoch_m15_value = stoch_k_m15.iloc[m15_idx]
            
            # Lấy OHLC
            candle_low = df_h1['low'].iloc[h1_idx]
            candle_high = df_h1['high'].iloc[h1_idx]
            candle_close = df_h1['close'].iloc[h1_idx]
            
            # Phân tích S/R tại thời điểm đó
            df_h1_at_signal = df_h1.iloc[:h1_idx+1].copy()
            sr_result = self.sr.analyze(df_h1_at_signal)
            
            signal = None
            
            if div['type'] == 'bullish':
                # BUY: H1 < 25 & M15 < 25 & chạm Support
                in_support = self.check_candle_touching_support(
                    sr_result, candle_low, candle_high, candle_close
                )
                
                if stoch_h1_value < 25 and stoch_m15_value < 25 and in_support:
                    signal = {
                        'symbol': symbol,
                        'type': 'BUY',
                        'time': signal_time,
                        'price': candle_close,
                        'stoch_m15': stoch_m15_value,
                        'stoch_h1': stoch_h1_value,
                        'cvd_prev': div['prev_cvd'],
                        'cvd_curr': div['curr_cvd']
                    }
            
            elif div['type'] == 'bearish':
                # SELL: H1 > 75 & M15 > 75 & chạm Resistance
                in_resistance = self.check_candle_touching_resistance(
                    sr_result, candle_low, candle_high, candle_close
                )
                
                if stoch_h1_value > 75 and stoch_m15_value > 75 and in_resistance:
                    signal = {
                        'symbol': symbol,
                        'type': 'SELL',
                        'time': signal_time,
                        'price': candle_close,
                        'stoch_m15': stoch_m15_value,
                        'stoch_h1': stoch_h1_value,
                        'cvd_prev': div['prev_cvd'],
                        'cvd_curr': div['curr_cvd']
                    }
            
            if signal:
                signals.append(signal)
        
        return signals


def main():
    """Chạy backtest"""
    
    print("\n" + "="*70)
    print("BACKTEST TÍN HIỆU - QUÉT TOÀN BỘ LỊCH SỬ")
    print("="*70)
    
    backtest = SignalBacktest()
    
    # Danh sách coin cần test
    symbols = ['BTCUSDT']
    
    all_signals = []
    
    for symbol in symbols:
        signals = backtest.backtest_symbol(symbol, limit=1000)
        all_signals.extend(signals)
        
        # Hiển thị kết quả
        if signals:
            print(f"\n🎯 TÌM THẤY {len(signals)} TÍN HIỆU:")
            print("-" * 70)
            
            for i, sig in enumerate(signals, 1):
                icon = "🟢" if sig['type'] == 'BUY' else "🔴"
                print(f"\n{i}. {icon} {sig['type']}")
                print(f"   Thời gian: {sig['time'].strftime('%H:%M %d-%m-%Y')}")
                print(f"   Giá: ${sig['price']:.4f}")
                print(f"   Stoch M15: {sig['stoch_m15']:.2f}")
                print(f"   Stoch H1: {sig['stoch_h1']:.2f}")
                print(f"   CVD: {sig['cvd_prev']:.2f} → {sig['cvd_curr']:.2f}")
        else:
            print(f"\n⚪ Không tìm thấy tín hiệu nào")
    
    # Tổng kết
    print(f"\n{'='*70}")
    print(f"TỔNG KẾT BACKTEST")
    print(f"{'='*70}")
    print(f"Tổng số tín hiệu: {len(all_signals)}")
    
    buy_signals = [s for s in all_signals if s['type'] == 'BUY']
    sell_signals = [s for s in all_signals if s['type'] == 'SELL']
    
    print(f"Tín hiệu BUY: {len(buy_signals)}")
    print(f"Tín hiệu SELL: {len(sell_signals)}")
    
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()