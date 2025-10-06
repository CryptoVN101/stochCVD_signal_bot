"""
Test tín hiệu STOCH + S/R - Logic mới chính xác
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


def test_stoch_sr(symbol='ZROUSDT'):
    """Test Stoch + S/R - Logic mới"""
    
    print(f"\n{'='*80}")
    print(f"TEST TÍN HIỆU STOCH + S/R - {symbol}")
    print(f"{'='*80}")
    print(f"Logic mới:")
    print(f"  LONG: %D(cam) H1<25 & M15<25, Low<=channel_high & Close>channel_low")
    print(f"  SHORT: %K(xanh) H1>75 & M15>75, High>=channel_low & Close<channel_high")
    
    df_m15 = fetch_data(symbol, '15m', 500)
    df_h1 = fetch_data(symbol, '1h', 500)
    
    # Stochastic - ĐỔI TÊN BIẾN ĐỂ TRÁNH XUNG ĐỘT
    stoch = StochasticIndicator(
        k_period=config.STOCH_K_PERIOD,
        k_smooth=config.STOCH_K_SMOOTH,
        d_smooth=config.STOCH_D_SMOOTH
    )
    stoch_k_m15_series, stoch_d_m15_series = stoch.calculate(df_m15)
    stoch_k_h1_series, stoch_d_h1_series = stoch.calculate(df_h1)
    
    # S/R
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
    
    # Quét 50 nến H1 cuối
    for i in range(len(df_h1) - 50, len(df_h1)):
        signal_time = df_h1.index[i]
        
        # Lấy giá trị Stoch tại index i
        k_h1 = stoch_k_h1_series.iloc[i]
        d_h1 = stoch_d_h1_series.iloc[i]
        
        m15_idx = df_m15.index.get_indexer([signal_time], method='nearest')[0]
        k_m15 = stoch_k_m15_series.iloc[m15_idx]
        d_m15 = stoch_d_m15_series.iloc[m15_idx]
        
        # Điều kiện Stoch
        is_long = d_h1 < 25 and d_m15 < 25
        is_short = k_h1 > 75 and k_m15 > 75
        
        if not (is_long or is_short):
            continue
        
        # S/R
        result_h1 = sr_h1.analyze(df_h1.iloc[:i+1])
        result_m15 = sr_m15.analyze(df_m15.iloc[:m15_idx+1])
        
        timeframes = []
        
        # Check H1 in_channel
        if result_h1['success'] and result_h1['in_channel']:
            h1_low = df_h1['low'].iloc[i]
            h1_high = df_h1['high'].iloc[i]
            h1_close = df_h1['close'].iloc[i]
            
            ch = result_h1['in_channel']
            
            if is_long:
                if h1_low <= ch['high'] and h1_close > ch['low']:
                    timeframes.append('H1')
            elif is_short:
                if h1_high >= ch['low'] and h1_close < ch['high']:
                    timeframes.append('H1')
        
        # Check 4 nến M15 in_channel
        if result_m15['success'] and result_m15['in_channel']:
            last_4_m15 = df_m15.iloc[m15_idx-3:m15_idx+1]
            ch = result_m15['in_channel']
            
            m15_touched = False
            for j in range(len(last_4_m15)):
                m15_low = last_4_m15['low'].iloc[j]
                m15_high = last_4_m15['high'].iloc[j]
                m15_close = last_4_m15['close'].iloc[j]
                
                if is_long:
                    if m15_low <= ch['high'] and m15_close > ch['low']:
                        m15_touched = True
                        break
                elif is_short:
                    if m15_high >= ch['low'] and m15_close < ch['high']:
                        m15_touched = True
                        break
            
            if m15_touched:
                timeframes.insert(0, 'M15')
        
        if timeframes:
            signals.append({
                'time': signal_time,
                'type': 'MUA' if is_long else 'BÁN',
                'price': df_h1['close'].iloc[i],
                'stoch_k_h1': k_h1,
                'stoch_d_h1': d_h1,
                'stoch_k_m15': k_m15,
                'stoch_d_m15': d_m15,
                'timeframes': ' & '.join(timeframes),
                'sr_type': 'hỗ trợ' if is_long else 'kháng cự'
            })
    
    print(f"\nKẾT QUẢ: {len(signals)} tín hiệu")
    
    if signals:
        print(f"\n{'='*80}")
        for i, sig in enumerate(signals, 1):
            icon = "🟢" if sig['type'] == 'MUA' else "🔴"
            
            print(f"\n{i}. {icon} {sig['type']}")
            print(f"   Thời gian: {sig['time'].strftime('%H:%M %d-%m-%Y')}")
            print(f"   Giá: ${sig['price']:.4f}")
            print(f"   Stoch %K H1/M15: {sig['stoch_k_h1']:.2f} / {sig['stoch_k_m15']:.2f}")
            print(f"   Stoch %D H1/M15: {sig['stoch_d_h1']:.2f} / {sig['stoch_d_m15']:.2f}")
            print(f"   Chạm {sig['sr_type']}: {sig['timeframes']}")
    else:
        print(f"\nKhông có tín hiệu")
    
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    test_stoch_sr('LDOUSDT')