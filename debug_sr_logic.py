"""
Debug chi tiết logic S/R
"""

import pandas as pd
import ccxt
import pytz
from datetime import datetime
from signal_scanner import SignalScanner

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


def debug_eigenusdt():
    """Debug chi tiết EIGENUSDT"""
    
    print("\n" + "="*70)
    print("DEBUG: EIGENUSDT - Tín hiệu 13:00 02-10-2025")
    print("="*70)
    
    scanner = SignalScanner()
    
    # Lấy dữ liệu
    df_h1 = scanner.fetch_data('EIGENUSDT', '1h', limit=500)
    
    if df_h1 is None:
        print("Lỗi lấy dữ liệu")
        return
    
    # Tìm nến tại thời điểm 13:00 02-10-2025
    target_time_str = "2025-10-02 13:00:00+07:00"
    target_time = pd.to_datetime(target_time_str).tz_localize(None).tz_localize(VIETNAM_TZ)
    
    try:
        idx = df_h1.index.get_indexer([target_time], method='nearest')[0]
        candle_time = df_h1.index[idx]
        
        # CẮT DỮ LIỆU ĐẾN THỜI ĐIỂM TÍN HIỆU
        df_h1_at_signal = df_h1.iloc[:idx+1].copy()
        
        print(f"\n📅 Dữ liệu được cắt đến: {candle_time.strftime('%H:%M %d-%m-%Y')}")
        print(f"   Số nến: {len(df_h1_at_signal)}")
        
        # Phân tích S/R với dữ liệu đã cắt
        sr_result = scanner.sr.analyze(df_h1_at_signal)
        
        print(f"\n📊 PHÂN TÍCH S/R (tại thời điểm tín hiệu):")
        print(f"   Success: {sr_result['success']}")
        print(f"   Current Price: ${sr_result['current_price']:.4f}")
        print(f"   Channel Width: ${sr_result['channel_width']:.4f}")
        
        print(f"\n🔴 RESISTANCE ZONES ({len(sr_result['resistances'])} vùng):")
        for i, r in enumerate(sr_result['resistances'], 1):
            print(f"   {i}. ${r['low']:.4f} - ${r['high']:.4f} (Strength: {r['strength']})")
        
        print(f"\n🟢 SUPPORT ZONES ({len(sr_result['supports'])} vùng):")
        for i, s in enumerate(sr_result['supports'], 1):
            print(f"   {i}. ${s['low']:.4f} - ${s['high']:.4f} (Strength: {s['strength']})")
        
        if sr_result['in_channel']:
            ch = sr_result['in_channel']
            print(f"\n⚪ IN_CHANNEL:")
            print(f"   ${ch['low']:.4f} - ${ch['high']:.4f} (Strength: {ch['strength']})")
        
        # Thông tin nến
        candle_low = df_h1_at_signal['low'].iloc[-1]
        candle_high = df_h1_at_signal['high'].iloc[-1]
        candle_open = df_h1_at_signal['open'].iloc[-1]
        candle_close = df_h1_at_signal['close'].iloc[-1]
        
        print(f"\n🕐 NẾN TẠI {candle_time.strftime('%H:%M %d-%m-%Y')}:")
        print(f"   Open:  ${candle_open:.4f}")
        print(f"   High:  ${candle_high:.4f}")
        print(f"   Low:   ${candle_low:.4f}")
        print(f"   Close: ${candle_close:.4f}")
        
        # Test logic kiểm tra (dùng method mới)
        print(f"\n🔍 KIỂM TRA LOGIC (TOÀN BỘ NẾN):")
        
        # Kiểm tra nến với Support
        print(f"\n1. Kiểm tra nến [Low=${candle_low:.4f}, High=${candle_high:.4f}] với Support:")
        in_support = scanner._check_candle_touching_support(sr_result, candle_low, candle_high)
        print(f"   Result: {in_support}")
        
        if in_support:
            matched = scanner._find_matched_support(sr_result, candle_low, candle_high)
            if matched:
                print(f"   ✅ Matched zone: ${matched['low']:.4f} - ${matched['high']:.4f}")
        
        # Kiểm tra nến với Resistance
        print(f"\n2. Kiểm tra nến [Low=${candle_low:.4f}, High=${candle_high:.4f}] với Resistance:")
        in_resistance = scanner._check_candle_touching_resistance(sr_result, candle_low, candle_high)
        print(f"   Result: {in_resistance}")
        
        if in_resistance:
            matched = scanner._find_matched_resistance(sr_result, candle_low, candle_high)
            if matched:
                print(f"   ✅ Matched zone: ${matched['low']:.4f} - ${matched['high']:.4f}")
        
        # Chi tiết từng zone
        if sr_result['resistances']:
            print(f"\n3. Chi tiết kiểm tra từng Resistance zone:")
            for i, resistance in enumerate(sr_result['resistances'], 1):
                zone_low = resistance['low']
                zone_high = resistance['high']
                
                # 3 điều kiện chạm zone
                check1 = zone_low <= candle_low <= zone_high
                check2 = zone_low <= candle_high <= zone_high
                check3 = candle_low <= zone_low and candle_high >= zone_high
                
                print(f"\n   Zone {i}: ${zone_low:.4f} - ${zone_high:.4f}")
                print(f"      Low trong zone? {check1} ({zone_low:.4f} <= {candle_low:.4f} <= {zone_high:.4f})")
                print(f"      High trong zone? {check2} ({zone_low:.4f} <= {candle_high:.4f} <= {zone_high:.4f})")
                print(f"      Nến xuyên qua? {check3} ({candle_low:.4f} <= {zone_low:.4f} và {candle_high:.4f} >= {zone_high:.4f})")
                
                if check1 or check2 or check3:
                    print(f"      ✅ MATCH!")
        
        if sr_result['supports']:
            print(f"\n4. Chi tiết kiểm tra từng Support zone:")
            for i, support in enumerate(sr_result['supports'], 1):
                zone_low = support['low']
                zone_high = support['high']
                
                check1 = zone_low <= candle_low <= zone_high
                check2 = zone_low <= candle_high <= zone_high
                check3 = candle_low <= zone_low and candle_high >= zone_high
                
                print(f"\n   Zone {i}: ${zone_low:.4f} - ${zone_high:.4f}")
                print(f"      Low trong zone? {check1}")
                print(f"      High trong zone? {check2}")
                print(f"      Nến xuyên qua? {check3}")
                
                if check1 or check2 or check3:
                    print(f"      ✅ MATCH!")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    debug_eigenusdt()