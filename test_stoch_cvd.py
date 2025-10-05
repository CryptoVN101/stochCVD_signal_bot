"""
Test tín hiệu STOCH + CVD
Điều kiện:
- CVD phân kỳ trên H1
- Stoch H1 < 25 & M15 < 25 (LONG) hoặc H1 > 75 & M15 > 75 (SHORT)
"""

import pandas as pd
import ccxt
import pytz
from signal_scanner import SignalScanner

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


def test_stoch_cvd(symbol='BTCUSDT'):
    """Test Stoch + CVD signal"""
    
    print(f"\n{'='*70}")
    print(f"TEST TÍN HIỆU STOCH + CVD - {symbol}")
    print(f"{'='*70}")
    
    scanner = SignalScanner()
    
    # Lấy dữ liệu
    df_m15 = scanner.fetch_data(symbol, '15m', limit=300)
    df_h1 = scanner.fetch_data(symbol, '1h', limit=500)
    
    if df_m15 is None or df_h1 is None:
        print("❌ Không lấy được dữ liệu")
        return
    
    # Tính Stochastic
    stoch_k_m15, _ = scanner.stoch.calculate(df_m15)
    stoch_k_h1, _ = scanner.stoch.calculate(df_h1)
    
    print(f"\n📊 STOCHASTIC HIỆN TẠI:")
    print(f"   H1:  {stoch_k_h1.iloc[-1]:.2f}")
    print(f"   M15: {stoch_k_m15.iloc[-1]:.2f}")
    
    # Kiểm tra tín hiệu
    signal = scanner._check_signal_stoch_cvd(symbol, df_m15, df_h1, stoch_k_m15, stoch_k_h1)
    
    if signal:
        icon = "🟢" if signal['signal_type'] == 'BUY' else "🔴"
        print(f"\n{icon} TÌM THẤY TÍN HIỆU {signal['signal_type']}!")
        print(f"   Thời gian: {signal['signal_time'].strftime('%H:%M %d-%m-%Y')}")
        print(f"   Giá: ${signal['price']:.4f}")
        print(f"   Stoch H1/M15: {signal['stoch_h1']:.2f} / {signal['stoch_m15']:.2f}")
        
        if signal.get('cvd_info'):
            cvd = signal['cvd_info']
            print(f"   CVD: {cvd['prev_cvd']:.2f} → {cvd['curr_cvd']:.2f}")
        
        print(f"\n📱 MESSAGE GỬI TELEGRAM:")
        print(f"   🔶 Token: {symbol} (Bybit)")
        print(f"   {icon} Tín hiệu đảo chiều {'BUY/LONG' if signal['signal_type']=='BUY' else 'SELL/SHORT'} - Stoch + CVD")
        print(f"   💰 Giá xác nhận: ${signal['price']:.4f}")
    else:
        print(f"\n⚪ KHÔNG CÓ TÍN HIỆU")
        print(f"   Lý do: CVD không phân kỳ hoặc Stoch không thỏa điều kiện")
    
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    test_stoch_cvd('EIGENUSDT')