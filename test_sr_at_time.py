"""
Tool kiểm tra S/R tại THỜI ĐIỂM CỤ THỂ

LOGIC ĐƠN GIẢN - CHỈ CHECK OPEN:
- LONG: Nến trước Open ≥ ch_high
- SHORT: Nến trước Open ≤ ch_low
"""

import pandas as pd
import ccxt
import pytz
from datetime import datetime
from support_resistance import SupportResistanceChannel
from stochastic_indicator import StochasticIndicator
import config

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


def fetch_data_until_time(symbol, timeframe, target_time, limit=1000):
    """Lấy dữ liệu từ Binance TỚI thời điểm cụ thể"""
    exchange = ccxt.binance({'enableRateLimit': True})
    
    if '/' not in symbol:
        symbol = symbol[:-4] + '/' + symbol[-4:]
    
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df['timestamp'] = df['timestamp'].dt.tz_convert(VIETNAM_TZ)
    df.set_index('timestamp', inplace=True)
    
    df = df[df.index <= target_time]
    return df


def test_sr_at_specific_time(symbol, target_time_str):
    """Kiểm tra S/R tại thời điểm cụ thể - Logic đơn giản"""
    
    target_time = VIETNAM_TZ.localize(datetime.strptime(target_time_str, "%Y-%m-%d %H:%M:%S"))
    
    print(f"\n{'='*80}")
    print(f"KIEM TRA S/R TAI THOI DIEM CU THE")
    print(f"{'='*80}")
    print(f"Symbol: {symbol}")
    print(f"Thoi diem: {target_time.strftime('%H:%M:%S %d-%m-%Y')}")
    print(f"{'='*80}")
    
    print(f"\nDang lay du lieu...")
    df_m15 = fetch_data_until_time(symbol, '15m', target_time, limit=1000)
    df_h1 = fetch_data_until_time(symbol, '1h', target_time, limit=1000)
    
    if len(df_m15) == 0 or len(df_h1) == 0:
        print(f"❌ KHONG CO DU LIEU tai thoi diem nay!")
        return
    
    if target_time not in df_h1.index:
        print(f"❌ Khong tim thay nen H1 tai {target_time}")
        print(f"Nen H1 gan nhat: {df_h1.index[-1]}")
        return
    
    h1_idx = df_h1.index.get_loc(target_time)
    
    # Tính Stochastic
    stoch = StochasticIndicator(
        k_period=config.STOCH_K_PERIOD,
        k_smooth=config.STOCH_K_SMOOTH,
        d_smooth=config.STOCH_D_SMOOTH
    )
    
    stoch_k_h1, stoch_d_h1 = stoch.calculate(df_h1)
    stoch_k_m15, stoch_d_m15 = stoch.calculate(df_m15)
    
    m15_idx = df_m15.index.get_indexer([target_time], method='nearest')[0]
    
    stoch_k_h1_val = stoch_k_h1.iloc[h1_idx]
    stoch_d_h1_val = stoch_d_h1.iloc[h1_idx]
    stoch_k_m15_val = stoch_k_m15.iloc[m15_idx]
    stoch_d_m15_val = stoch_d_m15.iloc[m15_idx]
    
    print(f"\n{'='*80}")
    print(f"STOCHASTIC TAI THOI DIEM NAY")
    print(f"{'='*80}")
    print(f"H1:  %K = {stoch_k_h1_val:.2f}, %D = {stoch_d_h1_val:.2f}")
    print(f"M15: %K = {stoch_k_m15_val:.2f}, %D = {stoch_d_m15_val:.2f}")
    
    is_long = stoch_d_h1_val < 25 and stoch_d_m15_val < 20
    is_short = stoch_k_h1_val > 75 and stoch_k_m15_val > 80
    
    print(f"\nDIEU KIEN STOCH:")
    print(f"  LONG:  H1 %D < 25 & M15 %D < 20")
    print(f"         {stoch_d_h1_val:.2f} < 25 & {stoch_d_m15_val:.2f} < 20")
    print(f"         => {is_long}")
    print(f"  SHORT: H1 %K > 75 & M15 %K > 80")
    print(f"         {stoch_k_h1_val:.2f} > 75 & {stoch_k_m15_val:.2f} > 80")
    print(f"         => {is_short}")
    
    if not (is_long or is_short):
        print(f"\n❌ STOCH KHONG THOA DIEU KIEN → Khong nen co tin hieu!")
        return
    
    signal_type = "LONG" if is_long else "SHORT"
    print(f"\n✅ STOCH THOA DIEU KIEN → Tin hieu: {signal_type}")
    
    # Tính S/R
    print(f"\n{'='*80}")
    print(f"SUPPORT/RESISTANCE TAI THOI DIEM NAY")
    print(f"{'='*80}")
    
    sr_h1_obj = SupportResistanceChannel(
        pivot_period=config.SR_PIVOT_PERIOD,
        channel_width_percent=config.SR_CHANNEL_WIDTH_PERCENT,
        loopback_period=config.SR_LOOPBACK_PERIOD,
        min_strength=config.SR_MIN_STRENGTH,
        max_channels=config.SR_MAX_CHANNELS
    )
    sr_h1 = sr_h1_obj.analyze(df_h1.iloc[:h1_idx+1])
    
    sr_m15_obj = SupportResistanceChannel(
        pivot_period=config.SR_M15_PIVOT_PERIOD,
        channel_width_percent=config.SR_M15_CHANNEL_WIDTH_PERCENT,
        loopback_period=config.SR_M15_LOOPBACK_PERIOD,
        min_strength=config.SR_M15_MIN_STRENGTH,
        max_channels=config.SR_M15_MAX_CHANNELS
    )
    sr_m15 = sr_m15_obj.analyze(df_m15.iloc[:m15_idx+1])
    
    h1_candle = df_h1.iloc[h1_idx]
    h1_low = h1_candle['low']
    h1_high = h1_candle['high']
    h1_close = h1_candle['close']
    
    print(f"\nNEN H1 TAI {target_time.strftime('%H:%M %d-%m-%Y')}:")
    print(f"  Low:   ${h1_low:.4f}")
    print(f"  High:  ${h1_high:.4f}")
    print(f"  Close: ${h1_close:.4f}")
    
    # Kiểm tra H1
    print(f"\n{'='*80}")
    print(f"KIEM TRA H1 IN_CHANNEL - LOGIC DON GIAN")
    print(f"{'='*80}")
    
    h1_touched = False
    
    if sr_h1['success'] and sr_h1['in_channel']:
        ch = sr_h1['in_channel']
        ch_low = ch['low']
        ch_high = ch['high']
        ch_mid = (ch_low + ch_high) / 2
        
        print(f"\n✅ CO IN_CHANNEL:")
        print(f"  Range: ${ch_low:.4f} - ${ch_high:.4f}")
        print(f"  Mid:   ${ch_mid:.4f}")
        print(f"  Strength: {ch['strength']}")
        
        if h1_close > ch_mid:
            position = "NUA TREN"
            position_emoji = "🟢"
        else:
            position = "NUA DUOI"
            position_emoji = "🔴"
        
        print(f"\n  {position_emoji} VI TRI GIA HIEN TAI: {position}")
        
        # Check Close còn trong channel
        in_channel = h1_close > ch_low and h1_close < ch_high
        print(f"  Close trong channel: {in_channel}")
        
        if is_long:
            print(f"\n  KIEM TRA LONG:")
            print(f"    1. Close > Mid? {h1_close:.4f} > {ch_mid:.4f} = {h1_close > ch_mid}")
            print(f"    2. Close trong channel? {in_channel}")
            
            if h1_close > ch_mid and in_channel and h1_idx > 0:
                prev_h1_open = df_h1['open'].iloc[h1_idx-1]
                
                print(f"\n    3. KIEM TRA NEN TRUOC:")
                print(f"       Prev Open: ${prev_h1_open:.4f}")
                print(f"       Open >= ch_high? {prev_h1_open:.4f} >= {ch_high:.4f}")
                
                prev_valid = prev_h1_open >= ch_high
                print(f"       => Nen truoc HOP LE: {prev_valid}")
                
                if prev_valid:
                    touch_cond = h1_low <= ch_high and h1_close > ch_low
                    print(f"\n    4. Nen hien tai cham support?")
                    print(f"       Low <= ch_high & Close > ch_low")
                    print(f"       {h1_low:.4f} <= {ch_high:.4f} & {h1_close:.4f} > {ch_low:.4f}")
                    print(f"       => {touch_cond}")
                    
                    if touch_cond:
                        h1_touched = True
                        print(f"\n    ✅ H1 THOA DIEU KIEN LONG!")
                else:
                    print(f"\n    ❌ NEN TRUOC KHONG HOP LE (Open < ch_high)")
            else:
                if not (h1_close > ch_mid):
                    print(f"    ❌ Close khong o nua tren")
                elif not in_channel:
                    print(f"    ❌ Close khong trong channel (da breakout)")
                else:
                    print(f"    ❌ Khong co nen truoc")
        
        elif is_short:
            print(f"\n  KIEM TRA SHORT:")
            print(f"    1. Close < Mid? {h1_close:.4f} < {ch_mid:.4f} = {h1_close < ch_mid}")
            print(f"    2. Close trong channel? {in_channel}")
            
            if h1_close < ch_mid and in_channel and h1_idx > 0:
                prev_h1_open = df_h1['open'].iloc[h1_idx-1]
                
                print(f"\n    3. KIEM TRA NEN TRUOC:")
                print(f"       Prev Open: ${prev_h1_open:.4f}")
                print(f"       Open <= ch_low? {prev_h1_open:.4f} <= {ch_low:.4f}")
                
                prev_valid = prev_h1_open <= ch_low
                print(f"       => Nen truoc HOP LE: {prev_valid}")
                
                if prev_valid:
                    touch_cond = h1_high >= ch_low and h1_close < ch_high
                    print(f"\n    4. Nen hien tai cham resistance?")
                    print(f"       High >= ch_low & Close < ch_high")
                    print(f"       {h1_high:.4f} >= {ch_low:.4f} & {h1_close:.4f} < {ch_high:.4f}")
                    print(f"       => {touch_cond}")
                    
                    if touch_cond:
                        h1_touched = True
                        print(f"\n    ✅ H1 THOA DIEU KIEN SHORT!")
                else:
                    print(f"\n    ❌ NEN TRUOC KHONG HOP LE")
            else:
                if not (h1_close < ch_mid):
                    print(f"    ❌ Close khong o nua duoi")
                elif not in_channel:
                    print(f"    ❌ Close khong trong channel (da breakout)")
                else:
                    print(f"    ❌ Khong co nen truoc")
    else:
        print(f"\n❌ KHONG CO IN_CHANNEL H1")
    
    # Kiểm tra M15
    print(f"\n{'='*80}")
    print(f"KIEM TRA M15 IN_CHANNEL (4 nen cuoi) - LOGIC DON GIAN")
    print(f"{'='*80}")
    
    m15_touched = False
    
    if sr_m15['success'] and sr_m15['in_channel']:
        ch = sr_m15['in_channel']
        ch_low = ch['low']
        ch_high = ch['high']
        ch_mid = (ch_low + ch_high) / 2
        
        print(f"\n✅ CO IN_CHANNEL:")
        print(f"  Range: ${ch_low:.4f} - ${ch_high:.4f}")
        print(f"  Mid:   ${ch_mid:.4f}")
        print(f"  Strength: {ch['strength']}")
        
        start_idx = max(0, m15_idx - 3)
        last_4_m15 = df_m15.iloc[start_idx:m15_idx+1]
        
        print(f"\n  KIEM TRA 4 NEN M15 CUOI:")
        
        for i in range(len(last_4_m15)):
            m15_time = last_4_m15.index[i]
            m15_low = last_4_m15['low'].iloc[i]
            m15_high = last_4_m15['high'].iloc[i]
            m15_close = last_4_m15['close'].iloc[i]
            
            print(f"\n    Nen {i+1} ({m15_time.strftime('%H:%M %d-%m')}):")
            print(f"      Low: ${m15_low:.4f}, High: ${m15_high:.4f}, Close: ${m15_close:.4f}")
            
            if m15_close > ch_mid:
                position = "NUA TREN"
                position_emoji = "🟢"
            else:
                position = "NUA DUOI"
                position_emoji = "🔴"
            
            in_channel = m15_close > ch_low and m15_close < ch_high
            print(f"      {position_emoji} Vi tri: {position}, Trong channel: {in_channel}")
            
            if is_long and m15_close > ch_mid and in_channel:
                if i > 0:
                    prev_m15_open = last_4_m15['open'].iloc[i-1]
                    prev_valid = prev_m15_open >= ch_high
                    
                    print(f"      Nen truoc Open >= ch_high: {prev_valid}")
                    
                    if prev_valid and m15_low <= ch_high and m15_close > ch_low:
                        m15_touched = True
                        print(f"      ✅ THOA DIEU KIEN LONG!")
            
            elif is_short and m15_close < ch_mid and in_channel:
                if i > 0:
                    prev_m15_open = last_4_m15['open'].iloc[i-1]
                    prev_valid = prev_m15_open <= ch_low
                    
                    print(f"      Nen truoc Open <= ch_low: {prev_valid}")
                    
                    if prev_valid and m15_high >= ch_low and m15_close < ch_high:
                        m15_touched = True
                        print(f"      ✅ THOA DIEU KIEN SHORT!")
    else:
        print(f"\n❌ KHONG CO IN_CHANNEL M15")
    
    # Kết luận
    print(f"\n{'='*80}")
    print(f"KET LUAN")
    print(f"{'='*80}")
    
    timeframes_touched = []
    if h1_touched:
        timeframes_touched.append('H1')
    if m15_touched:
        timeframes_touched.append('M15')
    
    if timeframes_touched:
        print(f"\n✅ TIN HIEU {signal_type} DUNG!")
        print(f"   Cham S/R: {' & '.join(timeframes_touched)}")
        print(f"   Logic: Nen truoc Open ngoai channel → Gia giam/tang vao S/R")
    else:
        print(f"\n❌ TIN HIEU {signal_type} SAI!")
        print(f"   Ly do: Nen truoc khong hop le hoac gia da breakout")
    
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Cach dung: python test_sr_at_time.py SYMBOL 'YYYY-MM-DD HH:MM:SS'")
        print("Vi du: python test_sr_at_time.py CAKEUSDT '2025-10-09 19:00:00'")
        sys.exit(1)
    
    symbol = sys.argv[1]
    time_str = sys.argv[2]
    
    test_sr_at_specific_time(symbol, time_str)