"""
Test tín hiệu với filter S/R
"""

import pandas as pd
import ccxt
import pytz
from signal_scanner import SignalScanner

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


def test_signal_with_sr():
    """Test tín hiệu có S/R filter"""
    
    symbols = ["EIGENUSDT"]
    
    print("\n" + "="*70)
    print("TEST TÍN HIỆU VỚI FILTER SUPPORT/RESISTANCE")
    print("="*70)
    
    scanner = SignalScanner()
    
    for symbol in symbols:
        print(f"\n{'='*70}")
        print(f"Đang quét {symbol}...")
        print(f"{'='*70}")
        
        try:
            signal = scanner.check_signal(symbol)
            
            if signal:
                print(f"\n🎯 TÌM THẤY TÍN HIỆU!")
                print(f"   Symbol: {signal['symbol']}")
                print(f"   Type: {signal['signal_type']}")
                print(f"   Price: ${signal['price']:.4f}")
                print(f"   Stoch M15: {signal['stoch_m15']:.2f}")
                print(f"   Stoch H1: {signal['stoch_h1']:.2f}")
                print(f"   Signal Time: {signal['signal_time'].strftime('%H:%M %d-%m-%Y')}")
                print(f"   Signal ID: {signal['signal_id']}")
            else:
                print(f"\n⚪ Không có tín hiệu")
                
        except Exception as e:
            print(f"\n❌ Lỗi: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("HOÀN THÀNH TEST")
    print("="*70)


if __name__ == '__main__':
    test_signal_with_sr()