"""
Test chỉ báo S/R - Sát logic bot live
"""

import pandas as pd
import ccxt
import pytz
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


def test_sr(symbol='ZROUSDT'):
    """Test S/R - Logic bot live"""
    
    print(f"\n{'='*80}")
    print(f"TEST CHI BAO S/R - {symbol}")
    print(f"{'='*80}")
    
    df_m15 = fetch_data(symbol, '15m', 500)
    df_h1 = fetch_data(symbol, '1h', 500)
    
    # S/R H1
    sr_h1 = SupportResistanceChannel(
        pivot_period=config.SR_PIVOT_PERIOD,
        channel_width_percent=config.SR_CHANNEL_WIDTH_PERCENT,
        loopback_period=config.SR_LOOPBACK_PERIOD,
        min_strength=config.SR_MIN_STRENGTH,
        max_channels=config.SR_MAX_CHANNELS
    )
    result_h1 = sr_h1.analyze(df_h1)
    
    # S/R M15
    sr_m15 = SupportResistanceChannel(
        pivot_period=config.SR_M15_PIVOT_PERIOD,
        channel_width_percent=config.SR_M15_CHANNEL_WIDTH_PERCENT,
        loopback_period=config.SR_M15_LOOPBACK_PERIOD,
        min_strength=config.SR_M15_MIN_STRENGTH,
        max_channels=config.SR_M15_MAX_CHANNELS
    )
    result_m15 = sr_m15.analyze(df_m15)
    
    # Hiển thị H1
    print(f"\nKHUNG H1")
    print("-" * 80)
    
    if not result_h1['success']:
        print(f"Loi: {result_h1['message']}")
    else:
        current_price = result_h1['current_price']
        print(f"Gia hien tai: ${current_price:.4f}")
        print(f"Channel Width: ${result_h1['channel_width']:.4f}")
        print(f"Tong so channels: {len(result_h1['all_channels'])}")
        
        if result_h1['in_channel']:
            ch = result_h1['in_channel']
            ch_mid = (ch['low'] + ch['high']) / 2
            position = "duoi trung diem" if current_price < ch_mid else "tren trung diem"
            
            print(f"\nTRONG CHANNEL (gia {position}):")
            print(f"  ${ch['low']:.4f} - ${ch['high']:.4f}")
            print(f"  Mid: ${ch_mid:.4f}")
            print(f"  Do manh: {ch['strength']}")
            print(f"  => Channel nay duoc phan loai: {'Resistance' if current_price < ch_mid else 'Support'}")
        
        if result_h1['resistances']:
            print(f"\nKHANG CU ({len(result_h1['resistances'])}):")
            for i, r in enumerate(result_h1['resistances'], 1):
                print(f"  {i}. ${r['low']:.4f} - ${r['high']:.4f} (Do manh: {r['strength']})")
        else:
            print(f"\nKHANG CU: Khong co")
        
        if result_h1['supports']:
            print(f"\nHO TRO ({len(result_h1['supports'])}):")
            for i, s in enumerate(result_h1['supports'], 1):
                print(f"  {i}. ${s['low']:.4f} - ${s['high']:.4f} (Do manh: {s['strength']})")
        else:
            print(f"\nHO TRO: Khong co")
    
    # Hiển thị M15
    print(f"\n\nKHUNG M15")
    print("-" * 80)
    
    if not result_m15['success']:
        print(f"Loi: {result_m15['message']}")
    else:
        current_price = result_m15['current_price']
        print(f"Gia hien tai: ${current_price:.4f}")
        print(f"Channel Width: ${result_m15['channel_width']:.4f}")
        print(f"Tong so channels: {len(result_m15['all_channels'])}")
        
        if result_m15['in_channel']:
            ch = result_m15['in_channel']
            ch_mid = (ch['low'] + ch['high']) / 2
            position = "duoi trung diem" if current_price < ch_mid else "tren trung diem"
            
            print(f"\nTRONG CHANNEL (gia {position}):")
            print(f"  ${ch['low']:.4f} - ${ch['high']:.4f}")
            print(f"  Mid: ${ch_mid:.4f}")
            print(f"  Do manh: {ch['strength']}")
            print(f"  => Channel nay duoc phan loai: {'Resistance' if current_price < ch_mid else 'Support'}")
        
        if result_m15['resistances']:
            print(f"\nKHANG CU ({len(result_m15['resistances'])}):")
            for i, r in enumerate(result_m15['resistances'], 1):
                print(f"  {i}. ${r['low']:.4f} - ${r['high']:.4f} (Do manh: {r['strength']})")
        else:
            print(f"\nKHANG CU: Khong co")
        
        if result_m15['supports']:
            print(f"\nHO TRO ({len(result_m15['supports'])}):")
            for i, s in enumerate(result_m15['supports'], 1):
                print(f"  {i}. ${s['low']:.4f} - ${s['high']:.4f} (Do manh: {s['strength']})")
        else:
            print(f"\nHO TRO: Khong co")
    
    # TEST LOGIC BOT: Kiểm tra nến hiện tại
    print(f"\n\nTEST LOGIC BOT - NEN HIEN TAI")
    print("=" * 80)
    
    # Nến H1
    if result_h1['success'] and result_h1['in_channel']:
        h1_low = df_h1['low'].iloc[-1]
        h1_high = df_h1['high'].iloc[-1]
        h1_close = df_h1['close'].iloc[-1]
        
        ch = result_h1['in_channel']
        
        print(f"\nH1 - Nen hien tai:")
        print(f"  Low: ${h1_low:.4f}, High: ${h1_high:.4f}, Close: ${h1_close:.4f}")
        print(f"  Channel: ${ch['low']:.4f} - ${ch['high']:.4f}")
        
        # Check LONG
        long_cond = h1_low <= ch['high'] and h1_close > ch['low']
        print(f"\n  Dieu kien LONG: Low <= channel_high & Close > channel_low")
        print(f"    {h1_low:.4f} <= {ch['high']:.4f} ? {h1_low <= ch['high']}")
        print(f"    {h1_close:.4f} > {ch['low']:.4f} ? {h1_close > ch['low']}")
        print(f"    => THOA: {long_cond}")
        
        # Check SHORT
        short_cond = h1_high >= ch['low'] and h1_close < ch['high']
        print(f"\n  Dieu kien SHORT: High >= channel_low & Close < channel_high")
        print(f"    {h1_high:.4f} >= {ch['low']:.4f} ? {h1_high >= ch['low']}")
        print(f"    {h1_close:.4f} < {ch['high']:.4f} ? {h1_close < ch['high']}")
        print(f"    => THOA: {short_cond}")
    
    # Nến M15
    if result_m15['success'] and result_m15['in_channel']:
        m15_low = df_m15['low'].iloc[-1]
        m15_high = df_m15['high'].iloc[-1]
        m15_close = df_m15['close'].iloc[-1]
        
        ch = result_m15['in_channel']
        
        print(f"\n\nM15 - Nen hien tai:")
        print(f"  Low: ${m15_low:.4f}, High: ${m15_high:.4f}, Close: ${m15_close:.4f}")
        print(f"  Channel: ${ch['low']:.4f} - ${ch['high']:.4f}")
        
        # Check LONG
        long_cond = m15_low <= ch['high'] and m15_close > ch['low']
        print(f"\n  Dieu kien LONG: Low <= channel_high & Close > channel_low")
        print(f"    {m15_low:.4f} <= {ch['high']:.4f} ? {m15_low <= ch['high']}")
        print(f"    {m15_close:.4f} > {ch['low']:.4f} ? {m15_close > ch['low']}")
        print(f"    => THOA: {long_cond}")
        
        # Check SHORT
        short_cond = m15_high >= ch['low'] and m15_close < ch['high']
        print(f"\n  Dieu kien SHORT: High >= channel_low & Close < channel_high")
        print(f"    {m15_high:.4f} >= {ch['low']:.4f} ? {m15_high >= ch['low']}")
        print(f"    {m15_close:.4f} < {ch['high']:.4f} ? {m15_close < ch['high']}")
        print(f"    => THOA: {short_cond}")
    
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    test_sr('ZROUSDT')