"""
Support and Resistance Channel Indicator
Sử dụng logic từ support_resistance_channel.py (TradingView)
"""

import pandas as pd
import numpy as np
from typing import Dict


class SupportResistanceChannel:
    """
    Lớp tính toán Support/Resistance Channels
    Logic 100% từ support_resistance_channel.py (TradingView Pine Script -> Python)
    """
    
    def __init__(
        self,
        pivot_period: int = 10,
        channel_width_percent: float = 5.0,
        loopback_period: int = 290,
        min_strength: int = 1,
        max_channels: int = 6,
        source: str = 'High/Low'
    ):
        """Khởi tạo S/R Channel calculator"""
        self.prd = pivot_period
        self.channel_width_pct = channel_width_percent
        self.loopback = loopback_period
        self.min_strength = min_strength
        self.max_num_sr = max_channels
        self.source = source
    
    def find_pivots(self, df: pd.DataFrame):
        """
        Tìm pivot points - LOGIC CHÍNH XÁC từ TradingView
        Kiểm tra THỦ CÔNG từng nến (KHÔNG dùng rolling)
        """
        result_df = df.copy()
        
        # Xác định source
        if self.source == 'High/Low':
            src1 = df['high']
            src2 = df['low']
        else:
            src1 = df[['close', 'open']].max(axis=1)
            src2 = df[['close', 'open']].min(axis=1)
        
        # Khởi tạo cột pivot
        result_df['ph'] = np.nan
        result_df['pl'] = np.nan
        
        # Tìm Pivot High và Pivot Low - LOGIC THỦ CÔNG
        for i in range(self.prd, len(df) - self.prd):
            # Kiểm tra Pivot High
            is_pivot_high = True
            for j in range(1, self.prd + 1):
                # Phải cao hơn TẤT CẢ nến bên trái VÀ bên phải
                if src1.iloc[i] < src1.iloc[i-j] or src1.iloc[i] <= src1.iloc[i+j]:
                    is_pivot_high = False
                    break
            
            if is_pivot_high:
                result_df.loc[result_df.index[i], 'ph'] = src1.iloc[i]
            
            # Kiểm tra Pivot Low
            is_pivot_low = True
            for j in range(1, self.prd + 1):
                # Phải thấp hơn TẤT CẢ nến bên trái VÀ bên phải
                if src2.iloc[i] > src2.iloc[i-j] or src2.iloc[i] >= src2.iloc[i+j]:
                    is_pivot_low = False
                    break
            
            if is_pivot_low:
                result_df.loc[result_df.index[i], 'pl'] = src2.iloc[i]
        
        return result_df
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Phân tích S/R - LOGIC CHÍNH XÁC từ TradingView
        """
        if len(df) < self.loopback:
            return {
                'success': False,
                'message': f'Không đủ dữ liệu (cần ít nhất {self.loopback} nến)'
            }
        
        current_idx = len(df) - 1
        current_price = df.iloc[-1]['close']
        
        # Reset index để dùng integer index
        df_work = df.reset_index(drop=True)
        
        # Tìm pivots
        df_pivots = self.find_pivots(df_work)
        
        # Thu thập tất cả pivot points trong loopback period
        pivot_vals = []
        pivot_locs = []
        
        lookback_start = max(0, len(df_work) - self.loopback)
        
        for i in range(lookback_start, len(df_work)):
            if not pd.isna(df_pivots['ph'].iloc[i]):
                pivot_vals.append(df_pivots['ph'].iloc[i])
                pivot_locs.append(i)
            if not pd.isna(df_pivots['pl'].iloc[i]):
                pivot_vals.append(df_pivots['pl'].iloc[i])
                pivot_locs.append(i)
        
        if not pivot_vals:
            return {
                'success': False,
                'message': 'Không có pivot points'
            }
        
        # Tính channel width tối đa (dựa trên 300 nến gần nhất)
        lookback_300 = df_work.iloc[-300:] if len(df_work) >= 300 else df_work
        highest_300 = lookback_300['high'].max()
        lowest_300 = lookback_300['low'].min()
        max_channel_width = (highest_300 - lowest_300) * self.channel_width_pct / 100
        
        # Tìm các potential channels - LOGIC TradingView
        supres_candidates = []
        
        for j in range(len(pivot_vals)):
            lo = hi = pivot_vals[j]
            num_pp_strength = 0
            
            # Tạo channel từ pivot hiện tại
            for k in range(len(pivot_vals)):
                cpp = pivot_vals[k]
                
                # Tính width nếu thêm pivot này vào channel
                if cpp <= hi:
                    wdth = max(hi - cpp, cpp - lo)
                else:
                    wdth = cpp - lo
                
                if wdth <= max_channel_width:
                    lo = min(lo, cpp)
                    hi = max(hi, cpp)
                    num_pp_strength += 20  # Mỗi pivot có sức mạnh 20
            
            # Thêm sức mạnh từ các nến chạm vào channel
            touch_strength = 0
            lookback_check = min(self.loopback, len(df_work))
            
            for k in range(len(df_work) - lookback_check, len(df_work)):
                high_price = df_work['high'].iloc[k]
                low_price = df_work['low'].iloc[k]
                
                # Kiểm tra nếu nến chạm channel
                if (high_price <= hi and high_price >= lo) or \
                   (low_price <= hi and low_price >= lo):
                    touch_strength += 1
            
            total_strength = num_pp_strength + touch_strength
            
            # Lưu channel nếu đủ mạnh
            if total_strength >= self.min_strength * 20:
                supres_candidates.append([total_strength, hi, lo])
        
        # Chọn lọc các kênh mạnh nhất và không trùng lặp - LOGIC TradingView
        final_channels = []
        
        for _ in range(self.max_num_sr):
            best_strength = -1
            best_channel_idx = -1
            
            # Tìm kênh mạnh nhất còn lại
            for j in range(len(supres_candidates)):
                if supres_candidates[j][0] > best_strength and \
                   supres_candidates[j][0] >= self.min_strength * 20:
                    best_strength = supres_candidates[j][0]
                    best_channel_idx = j
            
            if best_channel_idx != -1:
                # Lấy kênh mạnh nhất
                best_channel = supres_candidates[best_channel_idx]
                final_channels.append({
                    'strength': best_channel[0],
                    'high': best_channel[1],
                    'low': best_channel[2]
                })
                
                hh = best_channel[1]
                ll = best_channel[2]
                
                # Vô hiệu hóa các kênh đã bị bao gồm trong kênh mạnh nhất vừa chọn
                remaining_candidates = []
                for cand in supres_candidates:
                    c_hi, c_lo = cand[1], cand[2]
                    # Nếu kênh không bị trùng lặp, giữ lại
                    if not ((c_hi <= hh and c_hi >= ll) or (c_lo <= hh and c_lo >= ll)):
                        remaining_candidates.append(cand)
                supres_candidates = remaining_candidates
            else:
                break  # Không còn kênh nào đủ mạnh
        
        # Phân loại Support/Resistance
        supports = []
        resistances = []
        in_channel = None
        
        for ch in final_channels:
            ch_low = ch['low']
            ch_high = ch['high']
            
            # Kiểm tra giá có nằm TRONG channel không
            if current_price >= ch_low and current_price <= ch_high:
                # Chỉ lấy channel đầu tiên chứa giá
                if in_channel is None:
                    in_channel = ch
            # Channel nằm dưới giá -> Support
            elif ch_high < current_price:
                supports.append(ch)
            # Channel nằm trên giá -> Resistance
            elif ch_low > current_price:
                resistances.append(ch)
        
        return {
            'success': True,
            'current_price': current_price,
            'channel_width': max_channel_width,
            'all_channels': final_channels,
            'in_channel': in_channel,
            'supports': supports,
            'resistances': resistances
        }


def calculate_support_resistance(
    df: pd.DataFrame,
    pivot_period: int = 10,
    channel_width_percent: float = 5.0,
    loopback_period: int = 290
) -> Dict:
    """Hàm tiện ích tính S/R"""
    sr = SupportResistanceChannel(
        pivot_period=pivot_period,
        channel_width_percent=channel_width_percent,
        loopback_period=loopback_period
    )
    
    return sr.analyze(df)