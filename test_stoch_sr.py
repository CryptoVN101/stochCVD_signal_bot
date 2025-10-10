"""
Test tín hiệu STOCH + S/R - GIỐNG HẾT BOT LIVE

ĐIỀU KIỆN STOCH (SIẾT CHẶT M15):
- LONG: H1 %D < 25 & M15 %D < 20
- SHORT: H1 %K > 75 & M15 %K > 80

LOGIC ĐƠN GIẢN - CHỈ CHECK OPEN:
- LONG: Nến trước Open ≥ ch_high
- SHORT: Nến trước Open ≤ ch_low
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
    """Kiểm tra tín hiệu - Logic đơn giản: Chỉ check Open"""
    signal_time = df_h1.index[i_h1]
    
    # Tính Stochastic
    stoch_k_m15_series, stoch_d_m15_series = stoch.calculate(df_m15.iloc[:])
    stoch_k_h1_series, stoch_d_h1_series = stoch.calculate(df_h1.iloc[:i_h1+1])
    
    stoch_d_h1 = stoch_d_h1_series.iloc[-1]
    stoch_k_h1 = stoch_k_h1_series.iloc[-1]
    
    m15_idx = df_m15.index.get_indexer([signal_time], method='nearest')[0]
    if m15_idx >= len(stoch_d_m15_series):
        return None
    
    stoch_d_m15 = stoch_d_m15_series.iloc[m15_idx]
    stoch_k_m15 = stoch_k_m15_series.iloc[m15_idx]
    
    # ĐIỀU KIỆN STOCH
    is_long = stoch_d_h1 < 25 and stoch_d_m15 < 20
    is_short = stoch_k_h1 > 75 and stoch_k_m15 > 80
    
    if not (is_long or is_short):
        return None
    
    # Tính S/R
    sr_h1 = sr_h1_obj.analyze(df_h1.iloc[:i_h1+1])
    sr_m15 = sr_m15_obj.analyze(df_m15.iloc[:m15_idx+1])
    
    timeframes_touched = []
    
    # CHECK H1
    if sr_h1['success'] and sr_h1['in_channel']:
        h1_low = df_h1['low'].iloc[i_h1]
        h1_high = df_h1['high'].iloc[i_h1]
        h1_close = df_h1['close'].iloc[i_h1]
        
        channel = sr_h1['in_channel']
        ch_low = channel['low']
        ch_high = channel['high']
        ch_mid = (ch_low + ch_high) / 2
        
        if is_long:
            current_in_upper = h1_close > ch_mid
            current_in_channel = h1_close > ch_low and h1_close < ch_high
            
            if current_in_upper and current_in_channel and i_h1 > 0:
                prev_h1_open = df_h1['open'].iloc[i_h1-1]
                prev_valid = prev_h1_open >= ch_high
                
                if prev_valid:
                    if h1_low <= ch_high and h1_close > ch_low:
                        timeframes_touched.append('H1')
        
        elif is_short:
            current_in_lower = h1_close < ch_mid
            current_in_channel = h1_close > ch_low and h1_close < ch_high
            
            if current_in_lower and current_in_channel and i_h1 > 0:
                prev_h1_open = df_h1['open'].iloc[i_h1-1]
                prev_valid = prev_h1_open <= ch_low
                
                if prev_valid:
                    if h1_high >= ch_low and h1_close < ch_high:
                        timeframes_touched.append('H1')
    
    # CHECK 4 NẾN M15
    if sr_m15['success'] and sr_m15['in_channel']:
        start_idx = max(0, m15_idx - 3)
        last_4_m15 = df_m15.iloc[start_idx:m15_idx+1]
        
        channel = sr_m15['in_channel']
        ch_low = channel['low']
        ch_high = channel['high']
        ch_mid = (ch_low + ch_high) / 2
        
        m15_touched = False
        
        for j in range(len(last_4_m15)):
            m15_low = last_4_m15['low'].iloc[j]
            m15_high = last_4_m15['high'].iloc[j]
            m15_close = last_4_m15['close'].iloc[j]
            
            if is_long:
                current_in_upper = m15_close > ch_mid
                current_in_channel = m15_close > ch_low and m15_close < ch_high
                
                if current_in_upper and current_in_channel:
                    if j > 0:
                        prev_m15_open = last_4_m15['open'].iloc[j-1]
                        prev_valid = prev_m15_open >= ch_high
                        
                        if prev_valid:
                            if m15_low <= ch_high and m15_close > ch_low:
                                m15_touched = True
                                break
                    else:
                        if m15_low <= ch_high and m15_close > ch_low:
                            m15_touched = True
                            break
            
            elif is_short:
                current_in_lower = m15_close < ch_mid
                current_in_channel = m15_close > ch_low and m15_close < ch_high
                
                if current_in_lower and current_in_channel:
                    if j > 0:
                        prev_m15_open = last_4_m15['open'].iloc[j-1]
                        prev_valid = prev_m15_open <= ch_low
                        
                        if prev_valid:
                            if m15_high >= ch_low and m15_close < ch_high:
                                m15_touched = True
                                break
                    else:
                        if m15_high >= ch_low and m15_close < ch_high:
                            m15_touched = True
                            break
        
        if m15_touched:
            timeframes_touched.insert(0, 'M15')
    
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
    """Lọc tín hiệu theo timeframe"""
    if not signal:
        return None
    
    timeframes = signal.get('timeframes', '')
    minute = signal_time.minute
    
    if minute == 0:
        return 'both'
    elif minute % 15 == 0:
        if 'H1' in timeframes:
            return None
        else:
            return 'm15_only'
    
    return None


def test_stoch_sr(symbol='BTCUSDT', lookback_candles=100):
    """Test Stoch + S/R - Logic đơn giản: Chỉ check Open"""
    
    print(f"\n{'='*80}")
    print(f"BACKTEST TIN HIEU STOCH + S/R - {symbol}")
    print(f"{'='*80}")
    print(f"DIEU KIEN STOCH (SIET CHAT M15):")
    print(f"  - LONG: H1 %D < 25 & M15 %D < 20")
    print(f"  - SHORT: H1 %K > 75 & M15 %K > 80")
    print(f"\nLOGIC DON GIAN - CHI CHECK OPEN:")
    print(f"  LONG:  Nen truoc Open >= ch_high (gia giam vao support)")
    print(f"  SHORT: Nen truoc Open <= ch_low (gia tang vao resistance)")
    
    df_m15 = fetch_data(symbol, '15m', 500)
    df_h1 = fetch_data(symbol, '1h', 500)
    
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
    start_idx = max(0, len(df_h1) - lookback_candles)
    
    for i in range(start_idx, len(df_h1)):
        signal_time = df_h1.index[i]
        signal = check_signal_at_candle(df_m15, df_h1, i, stoch, sr_h1, sr_m15)
        send_type = filter_signal_by_timeframe(signal, signal_time)
        
        if send_type:
            signal['send_type'] = send_type
            signals.append(signal)
    
    print(f"\nKET QUA: {len(signals)} tin hieu duoc bao")
    
    if signals:
        print(f"\n{'='*80}")
        
        buy_count = sum(1 for s in signals if s['type'] == 'BUY')
        sell_count = sum(1 for s in signals if s['type'] == 'SELL')
        m15_only = sum(1 for s in signals if 'H1' not in s['timeframes'])
        h1_only = sum(1 for s in signals if 'M15' not in s['timeframes'])
        both_tf = sum(1 for s in signals if 'M15' in s['timeframes'] and 'H1' in s['timeframes'])
        
        print(f"\nTHONG KE:")
        print(f"  🟢 BUY: {buy_count}")
        print(f"  🔴 SELL: {sell_count}")
        print(f"  📊 M15 only: {m15_only}")
        print(f"  📊 H1 only: {h1_only}")
        print(f"  📊 M15 & H1: {both_tf}")
        
        print(f"\n{'='*80}")
        print("CHI TIET CAC TIN HIEU:")
        print(f"{'='*80}\n")
        
        for i, sig in enumerate(signals, 1):
            icon = "🟢" if sig['type'] == 'BUY' else "🔴"
            
            print(f"{i}. {icon} {sig['type']}")
            print(f"   Thoi gian: {sig['time'].strftime('%H:%M %d-%m-%Y')} ({sig['send_type']})")
            print(f"   Gia: ${sig['price']:.4f}")
            print(f"   Stoch %K H1/M15: {sig['stoch_k_h1']:.2f} / {sig['stoch_k_m15']:.2f}")
            print(f"   Stoch %D H1/M15: {sig['stoch_d_h1']:.2f} / {sig['stoch_d_m15']:.2f}")
            print(f"   Cham {sig['sr_type']}: {sig['timeframes']}")
            print()
    else:
        print(f"\nKhong co tin hieu nao duoc bao")
    
    print(f"{'='*80}\n")


if __name__ == '__main__':
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    lookback = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    test_stoch_sr(symbol, lookback)