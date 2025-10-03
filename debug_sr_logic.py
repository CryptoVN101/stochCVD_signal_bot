"""
Debug chi tiết logic S/R với Price Action
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
    print("DEBUG: EIGENUSDT - Tín hiệu 13:00 02-10-2025 (Price Action)")
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
        
        # Thông tin nến (THÊM CLOSE)
        candle_low = df_h1_at_signal['low'].iloc[-1]
        candle_high = df_h1_at_signal['high'].iloc[-1]
        candle_open = df_h1_at_signal['open'].iloc[-1]
        candle_close = df_h1_at_signal['close'].iloc[-1]
        
        print(f"\n🕐 NẾN TẠI {candle_time.strftime('%H:%M %d-%m-%Y')}:")
        print(f"   Open:  ${candle_open:.4f}")
        print(f"   High:  ${candle_high:.4f}")
        print(f"   Low:   ${candle_low:.4f}")
        print(f"   Close: ${candle_close:.4f}")
        
        # Xác định loại nến
        if candle_close > candle_open:
            candle_type = "🟢 NẾN XANH (tăng)"
        elif candle_close < candle_open:
            candle_type = "🔴 NẾN ĐỎ (giảm)"
        else:
            candle_type = "⚪ NẾN DOJI"
        print(f"   Loại: {candle_type}")
        
        # Test logic Price Action
        print(f"\n🔍 KIỂM TRA LOGIC PRICE ACTION:")
        
        # Kiểm tra Support (LONG)
        print(f"\n1. Kiểm tra Price Action với Support (LONG):")
        print(f"   Điều kiện: Close > zone_low VÀ Low <= zone_high")
        in_support = scanner._check_candle_touching_support(
            sr_result, candle_low, candle_high, candle_close
        )
        print(f"   Result: {in_support}")
        
        if in_support:
            matched = scanner._find_matched_support(
                sr_result, candle_low, candle_high, candle_close
            )
            if matched:
                print(f"   ✅ Matched zone: ${matched['low']:.4f} - ${matched['high']:.4f}")
        
        # Kiểm tra Resistance (SHORT)
        print(f"\n2. Kiểm tra Price Action với Resistance (SHORT):")
        print(f"   Điều kiện: Close < zone_high VÀ High >= zone_low")
        in_resistance = scanner._check_candle_touching_resistance(
            sr_result, candle_low, candle_high, candle_close
        )
        print(f"   Result: {in_resistance}")
        
        if in_resistance:
            matched = scanner._find_matched_resistance(
                sr_result, candle_low, candle_high, candle_close
            )
            if matched:
                print(f"   ✅ Matched zone: ${matched['low']:.4f} - ${matched['high']:.4f}")
        
        # Chi tiết từng Resistance zone
        if sr_result['resistances']:
            print(f"\n3. Chi tiết kiểm tra từng Resistance zone:")
            for i, resistance in enumerate(sr_result['resistances'], 1):
                zone_low = resistance['low']
                zone_high = resistance['high']
                
                # Price Action SHORT
                check_close = candle_close < zone_high
                check_high = candle_high >= zone_low
                match = check_close and check_high
                
                print(f"\n   Zone {i}: ${zone_low:.4f} - ${zone_high:.4f}")
                print(f"      Close < zone_high? {check_close} (${candle_close:.4f} < ${zone_high:.4f})")
                print(f"      High >= zone_low? {check_high} (${candle_high:.4f} >= ${zone_low:.4f})")
                
                if match:
                    print(f"      ✅ PRICE ACTION MATCH!")
        
        # Chi tiết từng Support zone
        if sr_result['supports']:
            print(f"\n4. Chi tiết kiểm tra từng Support zone:")
            for i, support in enumerate(sr_result['supports'], 1):
                zone_low = support['low']
                zone_high = support['high']
                
                # Price Action LONG
                check_close = candle_close > zone_low
                check_low = candle_low <= zone_high
                match = check_close and check_low
                
                print(f"\n   Zone {i}: ${zone_low:.4f} - ${zone_high:.4f}")
                print(f"      Close > zone_low? {check_close} (${candle_close:.4f} > ${zone_low:.4f})")
                print(f"      Low <= zone_high? {check_low} (${candle_low:.4f} <= ${zone_high:.4f})")
                
                if match:
                    print(f"      ✅ PRICE ACTION MATCH!")
        
        # Kiểm tra in_channel
        if sr_result['in_channel']:
            print(f"\n5. Kiểm tra IN_CHANNEL:")
            ch = sr_result['in_channel']
            zone_low = ch['low']
            zone_high = ch['high']
            
            mid_price = (candle_low + candle_high) / 2
            distance_to_low = abs(mid_price - zone_low)
            distance_to_high = abs(mid_price - zone_high)
            
            print(f"   Channel: ${zone_low:.4f} - ${zone_high:.4f}")
            print(f"   Mid Price: ${mid_price:.4f}")
            print(f"   Distance to Low: ${distance_to_low:.4f}")
            print(f"   Distance to High: ${distance_to_high:.4f}")
            
            if distance_to_low < distance_to_high:
                print(f"   → Gần SUPPORT hơn")
                check_close = candle_close > zone_low
                check_low = candle_low <= zone_high
                print(f"      Close > zone_low? {check_close}")
                print(f"      Low <= zone_high? {check_low}")
                if check_close and check_low:
                    print(f"      ✅ SUPPORT PRICE ACTION MATCH!")
            else:
                print(f"   → Gần RESISTANCE hơn")
                check_close = candle_close < zone_high
                check_high = candle_high >= zone_low
                print(f"      Close < zone_high? {check_close}")
                print(f"      High >= zone_low? {check_high}")
                if check_close and check_high:
                    print(f"      ✅ RESISTANCE PRICE ACTION MATCH!")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    debug_eigenusdt()