"""
Test tín hiệu STOCH + S/R - GIỐNG HỆT BOT LIVE
Backtest chính xác như bot sẽ chạy
"""

import pandas as pd
import ccxt
import pytz
from stochastic_indicator import StochasticIndicator
from support_resistance import SupportResistanceChannel
import config

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


def fetch_data(symbol, timeframe, limit):
    """Lấy dữ liệu từ Binance"""
    exchange = ccxt.binance({'enableRateLimit': True})
    
    if '/' not in symbol:
        symbol = symbol[:-4] + '/' + symbol[-4:]
    
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df['timestamp'] = df['timestamp'].dt.tz_convert(VIETNAM_TZ)
    df.set_index('timestamp', inplace=True)
    return df


def check_signal_at_candle(df_m15, df_h1, i_h1, stoch, sr_h1_obj, sr_m15_obj):
    """
    Kiểm tra tín hiệu tại nến H1 index i_h1
    Logic giống hệt signal_scanner.py
    """
    signal_time = df_h1.index[i_h1]
    
    # Tính Stochastic
    stoch_k_m15_series, stoch_d_m15_series = stoch.calculate(df_m15.iloc[:])
    stoch_k_h1_series, stoch_d_h1_series = stoch.calculate(df_h1.iloc[:i_h1+1])
    
    # Lấy giá trị Stoch tại thời điểm signal_time
    stoch_d_h1 = stoch_d_h1_series.iloc[-1]
    stoch_k_h1 = stoch_k_h1_series.iloc[-1]
    
    # Tìm index M15 tương ứng
    m15_idx = df_m15.index.get_indexer([signal_time], method='nearest')[0]
    if m15_idx >= len(stoch_d_m15_series):
        return None
    
    stoch_d_m15 = stoch_d_m15_series.iloc[m15_idx]
    stoch_k_m15 = stoch_k_m15_series.iloc[m15_idx]
    
    # Kiểm tra điều kiện Stoch
    # LONG: %D < 25 (dây cam)
    is_long = stoch_d_h1 < 25 and stoch_d_m15 < 25
    
    # SHORT: %K > 75 (dây xanh)
    is_short = stoch_k_h1 > 75 and stoch_k_m15 > 75
    
    if not (is_long or is_short):
        return None
    
    # Tính S/R tại thời điểm đó
    sr_h1 = sr_h1_obj.analyze(df_h1.iloc[:i_h1+1])
    sr_m15 = sr_m15_obj.analyze(df_m15.iloc[:m15_idx+1])
    
    timeframes_touched = []
    
    # Check H1 in_channel
    if sr_h1['success'] and sr_h1['in_channel']:
        h1_low = df_h1['low'].iloc[i_h1]
        h1_high = df_h1['high'].iloc[i_h1]
        h1_close = df_h1['close'].iloc[i_h1]
        
        channel = sr_h1['in_channel']
        channel_low = channel['low']
        channel_high = channel['high']
        
        if is_long:
            # LONG: Low <= channel_high && Close > channel_low
            if h1_low <= channel_high and h1_close > channel_low:
                timeframes_touched.append('H1')
        
        elif is_short:
            # SHORT: High >= channel_low && Close < channel_high
            if h1_high >= channel_low and h1_close < channel_high:
                timeframes_touched.append('H1')
    
    # Check 4 nến M15
    if sr_m15['success'] and sr_m15['in_channel']:
        # Lấy 4 nến M15 cuối (bao gồm nến hiện tại)
        start_idx = max(0, m15_idx - 3)
        last_4_m15 = df_m15.iloc[start_idx:m15_idx+1]
        
        channel = sr_m15['in_channel']
        channel_low = channel['low']
        channel_high = channel['high']
        
        m15_touched = False
        for j in range(len(last_4_m15)):
            m15_low = last_4_m15['low'].iloc[j]
            m15_high = last_4_m15['high'].iloc[j]
            m15_close = last_4_m15['close'].iloc[j]
            
            if is_long:
                if m15_low <= channel_high and m15_close > channel_low:
                    m15_touched = True
                    break
            
            elif is_short:
                if m15_high >= channel_low and m15_close < channel_high:
                    m15_touched = True
                    break
        
        if m15_touched:
            timeframes_touched.insert(0, 'M15')
    
    # Tạo signal nếu có timeframe thỏa mãn
    if timeframes_touched:
        return {
            'time': signal_time,
            'type': 'BUY' if is_long else 'SELL',
            'price': df_h1['close'].iloc[i_h1],
            'stoch_k_h1': stoch_k_h1,
            'stoch_d_h1': stoch_d_h1,
            'stoch_k_m15': stoch_k_m15,
            'stoch_d_m15': stoch_d_m15,
            'timeframes': ' & '.join(timeframes_touched),
            'sr_type': 'support' if is_long else 'resistance'
        }
    
    return None


def filter_signal_by_timeframe(signal, signal_time):
    """
    Lọc tín hiệu theo timeframe giống bot live
    
    Returns:
        str: 'both', 'm15_only', hoặc None
    """
    if not signal:
        return None
    
    timeframes = signal.get('timeframes', '')
    minute = signal_time.minute
    
    # Nến H1 đóng (phút :00)
    if minute == 0:
        # Gửi tất cả tín hiệu
        return 'both'
    
    # Nến M15 đóng (phút :15, :30, :45)
    elif minute % 15 == 0:
        # CHỈ gửi tín hiệu M15 only (không có H1)
        if 'H1' in timeframes:
            # Có H1 → đợi đến giờ :00
            return None
        else:
            # M15 only → gửi ngay
            return 'm15_only'
    
    return None


def test_stoch_sr(symbol='BEAMXUSDT', lookback_candles=100):
    """
    Test Stoch + S/R - BACKTEST GIỐNG BOT LIVE
    """
    
    print(f"\n{'='*80}")
    print(f"BACKTEST TÍN HIỆU STOCH + S/R - {symbol}")
    print(f"{'='*80}")
    print(f"Logic giống hệt bot live:")
    print(f"  - Tín hiệu H1: Chỉ báo khi nến H1 đóng (:00)")
    print(f"  - Tín hiệu M15: Chỉ báo khi nến M15 đóng (:15, :30, :45, :00)")
    print(f"  - Tín hiệu M15 & H1: Chỉ báo khi cả 2 đóng (:00)")
    print(f"  - Nếu có H1 mà chưa đến :00 → KHÔNG báo")
    
    df_m15 = fetch_data(symbol, '15m', 500)
    df_h1 = fetch_data(symbol, '1h', 500)
    
    # Khởi tạo indicators
    stoch = StochasticIndicator(
        k_period=config.STOCH_K_PERIOD,
        k_smooth=config.STOCH_K_SMOOTH,
        d_smooth=config.STOCH_D_SMOOTH
    )
    
    sr_h1 = SupportResistanceChannel(
        pivot_period=config.SR_PIVOT_PERIOD,
        channel_width_percent=config.SR_CHANNEL_WIDTH_PERCENT,
        loopback_period=config.SR_LOOPBACK_PERIOD,
        min_strength=config.SR_MIN_STRENGTH,
        max_channels=config.SR_MAX_CHANNELS
    )
    
    sr_m15 = SupportResistanceChannel(
        pivot_period=config.SR_M15_PIVOT_PERIOD,
        channel_width_percent=config.SR_M15_CHANNEL_WIDTH_PERCENT,
        loopback_period=config.SR_M15_LOOPBACK_PERIOD,
        min_strength=config.SR_M15_MIN_STRENGTH,
        max_channels=config.SR_M15_MAX_CHANNELS
    )
    
    signals = []
    
    # Quét các nến H1 cuối
    start_idx = max(0, len(df_h1) - lookback_candles)
    
    for i in range(start_idx, len(df_h1)):
        signal_time = df_h1.index[i]
        
        # Kiểm tra tín hiệu
        signal = check_signal_at_candle(df_m15, df_h1, i, stoch, sr_h1, sr_m15)
        
        # Lọc theo timeframe
        send_type = filter_signal_by_timeframe(signal, signal_time)
        
        if send_type:
            signal['send_type'] = send_type
            signals.append(signal)
    
    print(f"\nKẾT QUẢ: {len(signals)} tín hiệu được báo")
    
    if signals:
        print(f"\n{'='*80}")
        
        # Thống kê
        buy_count = sum(1 for s in signals if s['type'] == 'BUY')
        sell_count = sum(1 for s in signals if s['type'] == 'SELL')
        m15_only = sum(1 for s in signals if 'H1' not in s['timeframes'])
        h1_only = sum(1 for s in signals if 'M15' not in s['timeframes'])
        both_tf = sum(1 for s in signals if 'M15' in s['timeframes'] and 'H1' in s['timeframes'])
        
        print(f"\nTHỐNG KÊ:")
        print(f"  🟢 BUY: {buy_count}")
        print(f"  🔴 SELL: {sell_count}")
        print(f"  📊 M15 only: {m15_only}")
        print(f"  📊 H1 only: {h1_only}")
        print(f"  📊 M15 & H1: {both_tf}")
        
        print(f"\n{'='*80}")
        print("CHI TIẾT CÁC TÍN HIỆU:")
        print(f"{'='*80}\n")
        
        for i, sig in enumerate(signals, 1):
            icon = "🟢" if sig['type'] == 'BUY' else "🔴"
            
            print(f"{i}. {icon} {sig['type']}")
            print(f"   Thời gian: {sig['time'].strftime('%H:%M %d-%m-%Y')} ({sig['send_type']})")
            print(f"   Giá: ${sig['price']:.4f}")
            print(f"   Stoch %K H1/M15: {sig['stoch_k_h1']:.2f} / {sig['stoch_k_m15']:.2f}")
            print(f"   Stoch %D H1/M15: {sig['stoch_d_h1']:.2f} / {sig['stoch_d_m15']:.2f}")
            print(f"   Chạm {sig['sr_type']}: {sig['timeframes']}")
            print()
    else:
        print(f"\nKhông có tín hiệu nào được báo")
    
    print(f"{'='*80}\n")


if __name__ == '__main__':
    import sys
    
    # Lấy symbol từ command line hoặc dùng mặc định
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    
    # Lấy số nến lookback (mặc định 100)
    lookback = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    test_stoch_sr(symbol, lookback)