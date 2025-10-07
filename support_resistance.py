"""
Support and Resistance Channel Indicator
Chuyển từ Pine Script - FIX LOGIC PHÂN LOẠI
"""

import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from typing import List, Dict, Tuple, Optional


class SupportResistanceChannel:
    """
    Lớp tính toán Support/Resistance Channels
    Logic giống y hệt Pine Script
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
    
    def find_pivots(self, df: pd.DataFrame) -> List[Tuple[int, float, str]]:
        """
        Tìm pivot points - GIỐNG PINE SCRIPT
        """
        if self.source == 'High/Low':
            src1 = df['high'].values
            src2 = df['low'].values
        else:
            src1 = np.maximum(df['close'].values, df['open'].values)
            src2 = np.minimum(df['close'].values, df['open'].values)
        
        # Tìm pivot highs
        ph_indices = argrelextrema(src1, np.greater_equal, order=self.prd)[0]
        pivot_highs = [(i, src1[i], 'H') for i in ph_indices]
        
        # Tìm pivot lows
        pl_indices = argrelextrema(src2, np.less_equal, order=self.prd)[0]
        pivot_lows = [(i, src2[i], 'L') for i in pl_indices]
        
        # Kết hợp và sắp xếp theo thời gian giảm dần
        all_pivots = pivot_highs + pivot_lows
        all_pivots.sort(key=lambda x: x[0], reverse=True)
        
        return all_pivots
    
    def get_sr_vals(
        self,
        pivots: List[Tuple[int, float, str]],
        ind: int,
        cwidth: float
    ) -> Tuple[float, float, int]:
        """
        Tìm SR channel cho một pivot point - LOGIC PINE SCRIPT
        """
        lo = pivots[ind][1]
        hi = lo
        numpp = 0
        
        for y in range(len(pivots)):
            cpp = pivots[y][1]
            wdth = hi - cpp if cpp <= hi else cpp - lo
            
            if wdth <= cwidth:
                if cpp <= hi:
                    lo = min(lo, cpp)
                else:
                    hi = max(hi, cpp)
                numpp += 20
        
        return hi, lo, numpp
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Phân tích và tìm Support/Resistance channels
        FIX: Phân loại in_channel ĐÚNG
        """
        if len(df) < self.loopback:
            return {
                'success': False,
                'message': f'Không đủ dữ liệu (cần ít nhất {self.loopback} nến)'
            }
        
        current_idx = len(df) - 1
        current_price = df.iloc[-1]['close']
        
        # Tìm pivots
        pivots = self.find_pivots(df)
        
        # Lọc pivots trong loopback period
        pivots = [p for p in pivots if current_idx - p[0] <= self.loopback]
        
        if len(pivots) < 2:
            return {
                'success': False,
                'message': 'Không đủ pivot points'
            }
        
        # Tính channel width tối đa
        prdhighest = df['high'].tail(300).max()
        prdlowest = df['low'].tail(300).min()
        cwidth = (prdhighest - prdlowest) * self.channel_width_pct / 100
        
        # Tính SR levels và strengths
        supres = []
        for x in range(len(pivots)):
            hi, lo, strength = self.get_sr_vals(pivots, x, cwidth)
            
            # Thêm strength từ việc giá chạm vào channel
            s = 0
            for y in range(min(self.loopback, len(df))):
                idx = len(df) - 1 - y
                if idx >= 0:
                    bar_high = df.iloc[idx]['high']
                    bar_low = df.iloc[idx]['low']

                    if (bar_high <= hi and bar_high >= lo) or \
                        (bar_low <= hi and bar_low >= lo):
                        s += 1
            
            strength += s
            supres.append({'strength': strength, 'high': hi, 'low': lo})
        
        # Sắp xếp theo strength và lọc overlap
        supres.sort(key=lambda x: x['strength'], reverse=True)
        
        channels = []
        for sr in supres:
            if sr['strength'] >= self.min_strength * 20:
                # Kiểm tra overlap với channels đã có
                is_overlap = False
                for ch in channels:
                    if (sr['high'] <= ch['high'] and sr['high'] >= ch['low']) or \
                       (sr['low'] <= ch['high'] and sr['low'] >= ch['low']):
                        is_overlap = True
                        break
                
                if not is_overlap:
                    channels.append(sr)
                    
                if len(channels) >= self.max_num_sr:
                    break
        
        # FIX: Phân loại Support/Resistance ĐÚNG
        supports = []
        resistances = []
        in_channel = None
        
        for ch in channels:
            ch_low = ch['low']
            ch_high = ch['high']
            ch_mid = (ch_low + ch_high) / 2
            
            # Kiểm tra giá có nằm trong channel không
            if ch_low <= current_price <= ch_high:
                # PRICE IN CHANNEL - CHỈ GÁN in_channel, KHÔNG THÊM VÀO supports/resistances
                if in_channel is None:
                    in_channel = ch
                
                # KHÔNG làm gì thêm ở đây - để signal_scanner tự phân loại
            
            elif ch_high < current_price:
                # Channel dưới giá → Support
                supports.append(ch)
            
            elif ch_low > current_price:
                # Channel trên giá → Resistance
                resistances.append(ch)
        
        return {
            'success': True,
            'supports': supports,
            'resistances': resistances,
            'in_channel': in_channel,
            'all_channels': channels,
            'current_price': current_price,
            'channel_width': cwidth
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