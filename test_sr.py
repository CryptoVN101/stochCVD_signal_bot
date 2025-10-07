"""
Test chỉ báo S/R - Đúng logic support_resistance.py mới
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


def test_sr(symbol='PENDLEUSDT'):
    """Test S/R - Logic mới (in_channel không nằm trong supports/resistances)"""
    
    print(f"\n{'='*80}")
    print(f"TEST CHI BAO S/R - {symbol}")
    print(f"{'='*80}")
    print(f"Logic moi:")
    print(f"  - in_channel: Gia DANG NAM TRONG channel")
    print(f"  - supports: Cac channel DUOI gia (khong bao gom in_channel)")
    print(f"  - resistances: Cac channel TREN gia (khong bao gom in_channel)")
    
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
    print(f"\n{'='*80}")
    print(f"KHUNG H1")
    print(f"{'='*80}")
    
    if not result_h1['success']:
        print(f"Loi: {result_h1['message']}")
    else:
        current_price = result_h1['current_price']
        print(f"\nGia hien tai: ${current_price:.4f}")
        print(f"Channel Width: ${result_h1['channel_width']:.4f}")
        print(f"Tong so channels: {len(result_h1['all_channels'])}")
        
        # IN_CHANNEL (giá đang nằm trong)
        if result_h1['in_channel']:
            ch = result_h1['in_channel']
            ch_mid = (ch['low'] + ch['high']) / 2
            position = "duoi trung diem" if current_price < ch_mid else "tren trung diem"
            
            print(f"\n*** IN_CHANNEL (gia DANG NAM TRONG) ***")
            print(f"  Range: ${ch['low']:.4f} - ${ch['high']:.4f}")
            print(f"  Mid: ${ch_mid:.4f}")
            print(f"  Vi tri gia: {position}")
            print(f"  Do manh: {ch['strength']}")
            
            # TEST ĐIỀU KIỆN CHẠM
            h1_low = df_h1['low'].iloc[-1]
            h1_high = df_h1['high'].iloc[-1]
            h1_close = df_h1['close'].iloc[-1]
            
            print(f"\n  Nen hien tai H1:")
            print(f"    Low: ${h1_low:.4f}, High: ${h1_high:.4f}, Close: ${h1_close:.4f}")
            
            # Check LONG
            long_cond = h1_low <= ch['high'] and h1_close > ch['low']
            print(f"\n  Dieu kien LONG: Low <= ch_high & Close > ch_low")
            print(f"    {h1_low:.4f} <= {ch['high']:.4f} & {h1_close:.4f} > {ch['low']:.4f}")
            print(f"    => THOA: {long_cond}")
            
            # Check SHORT
            short_cond = h1_high >= ch['low'] and h1_close < ch['high']
            print(f"\n  Dieu kien SHORT: High >= ch_low & Close < ch_high")
            print(f"    {h1_high:.4f} >= {ch['low']:.4f} & {h1_close:.4f} < {ch['high']:.4f}")
            print(f"    => THOA: {short_cond}")
        else:
            print(f"\n*** IN_CHANNEL: Khong co (gia khong nam trong channel nao) ***")
        
        # KHÁNG CỰ (trên giá)
        if result_h1['resistances']:
            print(f"\n*** KHANG CU - TREN GIA ({len(result_h1['resistances'])}) ***")
            for i, r in enumerate(result_h1['resistances'], 1):
                print(f"  {i}. ${r['low']:.4f} - ${r['high']:.4f} (Do manh: {r['strength']})")
        else:
            print(f"\n*** KHANG CU: Khong co ***")
        
        # HỖ TRỢ (dưới giá)
        if result_h1['supports']:
            print(f"\n*** HO TRO - DUOI GIA ({len(result_h1['supports'])}) ***")
            for i, s in enumerate(result_h1['supports'], 1):
                print(f"  {i}. ${s['low']:.4f} - ${s['high']:.4f} (Do manh: {s['strength']})")
        else:
            print(f"\n*** HO TRO: Khong co ***")
    
    # Hiển thị M15
    print(f"\n\n{'='*80}")
    print(f"KHUNG M15")
    print(f"{'='*80}")
    
    if not result_m15['success']:
        print(f"Loi: {result_m15['message']}")
    else:
        current_price = result_m15['current_price']
        print(f"\nGia hien tai: ${current_price:.4f}")
        print(f"Channel Width: ${result_m15['channel_width']:.4f}")
        print(f"Tong so channels: {len(result_m15['all_channels'])}")
        
        # IN_CHANNEL (giá đang nằm trong)
        if result_m15['in_channel']:
            ch = result_m15['in_channel']
            ch_mid = (ch['low'] + ch['high']) / 2
            position = "duoi trung diem" if current_price < ch_mid else "tren trung diem"
            
            print(f"\n*** IN_CHANNEL (gia DANG NAM TRONG) ***")
            print(f"  Range: ${ch['low']:.4f} - ${ch['high']:.4f}")
            print(f"  Mid: ${ch_mid:.4f}")
            print(f"  Vi tri gia: {position}")
            print(f"  Do manh: {ch['strength']}")
            
            # TEST ĐIỀU KIỆN CHẠM - Kiểm tra 4 nến M15 cuối
            print(f"\n  Kiem tra 4 nen M15 cuoi:")
            last_4_m15 = df_m15.iloc[-4:]
            
            for j in range(len(last_4_m15)):
                m15_time = last_4_m15.index[j]
                m15_low = last_4_m15['low'].iloc[j]
                m15_high = last_4_m15['high'].iloc[j]
                m15_close = last_4_m15['close'].iloc[j]
                
                print(f"\n    Nen {j+1} ({m15_time.strftime('%H:%M')}):")
                print(f"      Low: ${m15_low:.4f}, High: ${m15_high:.4f}, Close: ${m15_close:.4f}")
                
                long_cond = m15_low <= ch['high'] and m15_close > ch['low']
                short_cond = m15_high >= ch['low'] and m15_close < ch['high']
                
                print(f"      LONG: {long_cond}, SHORT: {short_cond}")
        else:
            print(f"\n*** IN_CHANNEL: Khong co (gia khong nam trong channel nao) ***")
        
        # KHÁNG CỰ (trên giá)
        if result_m15['resistances']:
            print(f"\n*** KHANG CU - TREN GIA ({len(result_m15['resistances'])}) ***")
            for i, r in enumerate(result_m15['resistances'], 1):
                print(f"  {i}. ${r['low']:.4f} - ${r['high']:.4f} (Do manh: {r['strength']})")
        else:
            print(f"\n*** KHANG CU: Khong co ***")
        
        # HỖ TRỢ (dưới giá)
        if result_m15['supports']:
            print(f"\n*** HO TRO - DUOI GIA ({len(result_m15['supports'])}) ***")
            for i, s in enumerate(result_m15['supports'], 1):
                print(f"  {i}. ${s['low']:.4f} - ${s['high']:.4f} (Do manh: {s['strength']})")
        else:
            print(f"\n*** HO TRO: Khong co ***")
    
    print(f"\n{'='*80}")
    print("TOM TAT LOGIC:")
    print(f"{'='*80}")
    print("1. in_channel: CHI chua gia dang nam TRONG channel")
    print("2. supports: Cac channel DUOI gia (ch_high < current_price)")
    print("3. resistances: Cac channel TREN gia (ch_low > current_price)")
    print("4. Bot chi bao tin hieu khi in_channel != None")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    test_sr(symbol)