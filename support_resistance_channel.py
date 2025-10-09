import requests
import pandas as pd
import numpy as np
from datetime import datetime

# ==============================================================================
# PHẦN 1: HÀM LẤY DỮ LIỆU TỪ BINANCE API
# ==============================================================================
def get_binance_klines(symbol, interval, limit=500):
    """
    Lấy dữ liệu nến (klines) từ API công khai của Binance.
    """
    url = f"https://api.binance.com/api/v3/klines"
    params = {
        'symbol': symbol.upper(),
        'interval': interval,
        'limit': limit
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Ném lỗi nếu request không thành công
        data = response.json()
        
        # Chuyển đổi dữ liệu sang Pandas DataFrame
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Chọn các cột cần thiết và chuyển đổi kiểu dữ liệu
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        for col in df.columns:
            if col == 'timestamp':
                df[col] = pd.to_datetime(df[col], unit='ms')
            else:
                df[col] = pd.to_numeric(df[col])
        
        return df
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gọi API Binance: {e}")
        return None

# ==============================================================================
# PHẦN 2: HÀM TÍNH TOÁN CHỈ BÁO
# ==============================================================================
def calculate_sr_channels(df, 
                          prd=10, 
                          ppsrc='High/Low', 
                          channel_w_pct=5, 
                          min_strength=1, 
                          max_num_sr=6, 
                          loopback=290):
    """
    Hàm chính để tính toán các kênh Hỗ trợ và Kháng cự.
    """
    # --------------------------------------------------------------------------
    # Bước 1: Xác định các điểm Pivot (tương đương ta.pivothigh, ta.pivotlow)
    # --------------------------------------------------------------------------
    src1 = df['high'] if ppsrc == 'High/Low' else df[['close', 'open']].max(axis=1)
    src2 = df['low'] if ppsrc == 'High/Low' else df[['close', 'open']].min(axis=1)

    df['ph'] = np.nan
    df['pl'] = np.nan

    for i in range(prd, len(df) - prd):
        # Kiểm tra Pivot High
        is_pivot_high = True
        for j in range(1, prd + 1):
            if src1[i] < src1[i-j] or src1[i] <= src1[i+j]:
                is_pivot_high = False
                break
        if is_pivot_high:
            df.loc[i, 'ph'] = src1[i]

        # Kiểm tra Pivot Low
        is_pivot_low = True
        for j in range(1, prd + 1):
            if src2[i] > src2[i-j] or src2[i] >= src2[i+j]:
                is_pivot_low = False
                break
        if is_pivot_low:
            df.loc[i, 'pl'] = src2[i]
            
    # --------------------------------------------------------------------------
    # Bước 2: Xử lý logic chính (tính toán lặp qua từng nến)
    # Pine script chạy trên mỗi nến, vì vậy chúng ta mô phỏng logic đó.
    # --------------------------------------------------------------------------
    pivot_vals = []
    pivot_locs = []
    
    # Các cột để lưu kết quả kênh
    for i in range(max_num_sr):
        df[f'sr_{i}_top'] = np.nan
        df[f'sr_{i}_bottom'] = np.nan

    # Vòng lặp chính qua từng thanh nến (bắt đầu từ loopback để có đủ dữ liệu)
    for i in range(loopback, len(df)):
        # Cập nhật danh sách các pivots trong khoảng `loopback`
        is_new_pivot = False
        if not pd.isna(df['ph'][i]):
            pivot_vals.insert(0, df['ph'][i])
            pivot_locs.insert(0, i)
            is_new_pivot = True
        if not pd.isna(df['pl'][i]):
            pivot_vals.insert(0, df['pl'][i])
            pivot_locs.insert(0, i)
            is_new_pivot = True
            
        # Xóa các pivot cũ
        while pivot_locs and (i - pivot_locs[-1] > loopback):
            pivot_vals.pop()
            pivot_locs.pop()

        # Khi có pivot mới, tính toán lại tất cả các kênh
        if is_new_pivot:
            # Tính chiều rộng kênh tối đa (dựa trên 300 nến gần nhất)
            highest_300 = df['high'][i-300:i].max()
            lowest_300 = df['low'][i-300:i].min()
            cwidth = (highest_300 - lowest_300) * channel_w_pct / 100
            
            # ------------------------------------------------------------------
            # Tìm tất cả các kênh tiềm năng và sức mạnh ban đầu
            # ------------------------------------------------------------------
            supres_candidates = []
            for j in range(len(pivot_vals)):
                lo = hi = pivot_vals[j]
                num_pp_strength = 0
                
                # Tạo kênh từ pivot hiện tại
                for k in range(len(pivot_vals)):
                    cpp = pivot_vals[k]
                    wdth = (hi - cpp) if cpp <= hi else (cpp - lo)
                    if wdth <= cwidth:
                        lo = min(lo, cpp)
                        hi = max(hi, cpp)
                        num_pp_strength += 20 # Mỗi pivot có sức mạnh 20
                
                # Thêm sức mạnh từ các nến chạm vào kênh
                touch_strength = 0
                for k in range(i - loopback, i):
                    if (df['high'][k] <= hi and df['high'][k] >= lo) or \
                       (df['low'][k] <= hi and df['low'][k] >= lo):
                        touch_strength += 1
                
                total_strength = num_pp_strength + touch_strength
                supres_candidates.append([total_strength, hi, lo])

            # ------------------------------------------------------------------
            # Chọn lọc các kênh mạnh nhất và không trùng lặp
            # ------------------------------------------------------------------
            final_channels = []
            
            # Lặp để chọn ra `max_num_sr` kênh mạnh nhất
            for _ in range(max_num_sr):
                best_strength = -1
                best_channel_idx = -1
                
                # Tìm kênh mạnh nhất còn lại
                for j in range(len(supres_candidates)):
                    # Chỉ xét các kênh có sức mạnh >= min_strength
                    if supres_candidates[j][0] > best_strength and supres_candidates[j][0] >= min_strength * 20:
                        best_strength = supres_candidates[j][0]
                        best_channel_idx = j

                if best_channel_idx != -1:
                    # Lấy kênh mạnh nhất
                    best_channel = supres_candidates[best_channel_idx]
                    final_channels.append(best_channel)
                    hh = best_channel[1]
                    ll = best_channel[2]

                    # Vô hiệu hóa các kênh đã bị bao gồm trong kênh mạnh nhất vừa chọn
                    # để tránh trùng lặp.
                    remaining_candidates = []
                    for cand in supres_candidates:
                        c_hi, c_lo = cand[1], cand[2]
                        # Nếu kênh không bị trùng lặp, giữ lại
                        if not ((c_hi <= hh and c_hi >= ll) or (c_lo <= hh and c_lo >= ll)):
                            remaining_candidates.append(cand)
                    supres_candidates = remaining_candidates

                else:
                    break # Không còn kênh nào đủ mạnh
            
            # Sắp xếp các kênh cuối cùng theo giá trị từ cao đến thấp
            final_channels.sort(key=lambda x: x[1], reverse=True)

            # Gán kết quả vào DataFrame
            for j in range(len(final_channels)):
                if j < max_num_sr:
                    df.loc[i, f'sr_{j}_top'] = final_channels[j][1]
                    df.loc[i, f'sr_{j}_bottom'] = final_channels[j][2]
        
    # Điền tiếp các giá trị kênh cho các nến sau đó (ffill)
    for i in range(max_num_sr):
        df[f'sr_{i}_top'] = df[f'sr_{i}_top'].ffill()
        df[f'sr_{i}_bottom'] = df[f'sr_{i}_bottom'].ffill()
        
    return df


# ==============================================================================
# PHẦN 3: THỰC THI VÀ HIỂN THỊ KẾT QUẢ
# ==============================================================================
if __name__ == "__main__":
    # --- CẤU HÌNH ---
    SYMBOL = 'BTCUSDT'
    TIMEFRAMES = ['15m', '1h'] # Khung M15 và H1
    
    # --- CÁC THAM SỐ CỦA CHỈ BÁO (giống trong TradingView) ---
    params = {
        'prd': 10,                 # Pivot Period [cite: 1]
        'ppsrc': 'High/Low',       # Source [cite: 1]
        'channel_w_pct': 5,        # Maximum Channel Width % [cite: 1]
        'min_strength': 1,         # Minimum Strength (ít nhất 2 pivot) [cite: 2]
        'max_num_sr': 6,           # Maximum Number of S/R [cite: 2]
        'loopback': 290            # Loopback Period [cite: 2]
    }

    for tf in TIMEFRAMES:
        print(f"\n================ Đang xử lý {SYMBOL} trên khung {tf} ================")
        
        # Lấy dữ liệu
        df_klines = get_binance_klines(SYMBOL, tf, limit=1000)
        
        if df_klines is not None and not df_klines.empty:
            # Tính toán chỉ báo
            df_result = calculate_sr_channels(df_klines, **params)
            
            # Hiển thị kết quả cho 10 nến cuối cùng
            print(f"Các kênh Hỗ trợ/Kháng cự cho {SYMBOL} ({tf}):")
            
            # Lấy dòng dữ liệu cuối cùng
            last_row = df_result.iloc[-1]
            
            print(f"Dữ liệu tại nến cuối cùng ({last_row['timestamp']}):")
            print(f"  Close: {last_row['close']}")
            print("-" * 30)
            
            has_channels = False
            for i in range(params['max_num_sr']):
                top = last_row[f'sr_{i}_top']
                bottom = last_row[f'sr_{i}_bottom']
                
                if not pd.isna(top):
                    has_channels = True
                    # Xác định là Hỗ trợ hay Kháng cự
                    if last_row['close'] < bottom:
                        channel_type = "Kháng cự (Resistance)"
                    elif last_row['close'] > top:
                        channel_type = "Hỗ trợ (Support)"
                    else:
                        channel_type = "Trong kênh (In Channel)"
                        
                    print(f"  Kênh {i+1} ({channel_type}):")
                    print(f"    - Top:    {top:.2f}")
                    print(f"    - Bottom: {bottom:.2f}")
            
            if not has_channels:
                print("Không tìm thấy kênh Hỗ trợ/Kháng cự nào đủ mạnh tại nến cuối cùng.")
        else:
            print(f"Không thể lấy dữ liệu cho {SYMBOL} trên khung {tf}.")