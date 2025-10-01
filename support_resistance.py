"""
Support and Resistance Channel Indicator
Tái tạo từ TradingView Pine Script
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional


class SupportResistanceChannel:
    """
    Lớp tính toán Support/Resistance Channels
    Dựa trên thuật toán từ TradingView
    """
    
    def __init__(
        self,
        pivot_period: int = 10,
        channel_width_percent: float = 5.0,
        loopback_period: int = 290,
        min_strength: int = 1,
        max_channels: int = 6
    ):
        """
        Khởi tạo S/R Channel calculator
        
        Args:
            pivot_period: Chu kỳ pivot (mặc định 10)
            channel_width_percent: % độ rộng channel tối đa (mặc định 5%)
            loopback_period: Số nến nhìn lại để tính (mặc định 290)
            min_strength: Strength tối thiểu (mặc định 1)
            max_channels: Số channels tối đa hiển thị (mặc định 6)
        """
        self.pivot_period = pivot_period
        self.channel_width_percent = channel_width_percent
        self.loopback_period = loopback_period
        self.min_strength = min_strength
        self.max_channels = max_channels
    
    def find_pivot_high(self, high_series: pd.Series) -> pd.Series:
        """
        Tìm Pivot High
        
        Args:
            high_series: Series giá cao
            
        Returns:
            Series boolean, True tại vị trí pivot high
        """
        n = self.pivot_period
        pivot_high = pd.Series(False, index=high_series.index)
        
        for i in range(n, len(high_series) - n):
            is_pivot = True
            center = high_series.iloc[i]
            
            # Kiểm tra left bars
            for j in range(1, n + 1):
                if high_series.iloc[i - j] >= center:
                    is_pivot = False
                    break
            
            if not is_pivot:
                continue
            
            # Kiểm tra right bars
            for j in range(1, n + 1):
                if high_series.iloc[i + j] >= center:
                    is_pivot = False
                    break
            
            pivot_high.iloc[i] = is_pivot
        
        return pivot_high
    
    def find_pivot_low(self, low_series: pd.Series) -> pd.Series:
        """
        Tìm Pivot Low
        
        Args:
            low_series: Series giá thấp
            
        Returns:
            Series boolean, True tại vị trí pivot low
        """
        n = self.pivot_period
        pivot_low = pd.Series(False, index=low_series.index)
        
        for i in range(n, len(low_series) - n):
            is_pivot = True
            center = low_series.iloc[i]
            
            # Kiểm tra left bars
            for j in range(1, n + 1):
                if low_series.iloc[i - j] <= center:
                    is_pivot = False
                    break
            
            if not is_pivot:
                continue
            
            # Kiểm tra right bars
            for j in range(1, n + 1):
                if low_series.iloc[i + j] <= center:
                    is_pivot = False
                    break
            
            pivot_low.iloc[i] = is_pivot
        
        return pivot_low
    
    def calculate_channel_width(self, df: pd.DataFrame) -> float:
        """
        Tính độ rộng channel động
        
        Args:
            df: DataFrame với cột high, low
            
        Returns:
            float: Độ rộng channel tối đa
        """
        # Lấy 300 nến gần nhất (hoặc ít hơn nếu không đủ)
        lookback = min(300, len(df))
        recent_data = df.iloc[-lookback:]
        
        highest = recent_data['high'].max()
        lowest = recent_data['low'].min()
        
        channel_width = (highest - lowest) * self.channel_width_percent / 100
        
        return channel_width
    
    def get_sr_values(
        self,
        pivot_values: List[float],
        pivot_index: int,
        channel_width: float
    ) -> Tuple[float, float, int]:
        """
        Tính giá trị channel cho 1 pivot point
        
        Args:
            pivot_values: Danh sách tất cả pivot values
            pivot_index: Index của pivot đang xét
            channel_width: Độ rộng channel tối đa
            
        Returns:
            Tuple (hi, lo, strength)
        """
        lo = pivot_values[pivot_index]
        hi = pivot_values[pivot_index]
        num_pivots = 0
        
        # Tìm các pivot khác nằm trong channel
        for other_pivot in pivot_values:
            # Tính width nếu thêm pivot này vào
            if other_pivot <= hi:
                potential_width = hi - other_pivot
            else:
                potential_width = other_pivot - lo
            
            # Nếu vẫn nằm trong channel width cho phép
            if potential_width <= channel_width:
                if other_pivot <= hi:
                    lo = min(lo, other_pivot)
                else:
                    hi = max(hi, other_pivot)
                
                num_pivots += 20  # Mỗi pivot = 20 điểm
        
        return hi, lo, num_pivots
    
    def calculate_strength_from_bars(
        self,
        df: pd.DataFrame,
        channel_high: float,
        channel_low: float,
        loopback: int
    ) -> int:
        """
        Tính strength dựa trên số lần price test channel
        
        Args:
            df: DataFrame với high, low
            channel_high: Đỉnh channel
            channel_low: Đáy channel
            loopback: Số nến nhìn lại
            
        Returns:
            int: Strength score
        """
        strength = 0
        recent_data = df.iloc[-loopback:]
        
        for i in range(len(recent_data)):
            bar_high = recent_data['high'].iloc[i]
            bar_low = recent_data['low'].iloc[i]
            
            # Kiểm tra high có chạm channel không
            if bar_high <= channel_high and bar_high >= channel_low:
                strength += 1
            
            # Kiểm tra low có chạm channel không
            if bar_low <= channel_high and bar_low >= channel_low:
                strength += 1
        
        return strength
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Phân tích và tìm Support/Resistance channels
        
        Args:
            df: DataFrame với cột high, low, close
            
        Returns:
            Dict chứa thông tin channels
        """
        if len(df) < self.loopback_period:
            return {
                'success': False,
                'message': f'Không đủ dữ liệu (cần ít nhất {self.loopback_period} nến)'
            }
        
        # Tính channel width động
        channel_width = self.calculate_channel_width(df)
        
        # Tìm pivot points trong loopback period
        recent_df = df.iloc[-self.loopback_period:]
        pivot_high_mask = self.find_pivot_high(recent_df['high'])
        pivot_low_mask = self.find_pivot_low(recent_df['low'])
        
        # Lấy giá trị pivot
        pivot_values = []
        
        for i in range(len(recent_df)):
            if pivot_high_mask.iloc[i]:
                pivot_values.append(recent_df['high'].iloc[i])
            elif pivot_low_mask.iloc[i]:
                pivot_values.append(recent_df['low'].iloc[i])
        
        if len(pivot_values) < 2:
            return {
                'success': False,
                'message': 'Không đủ pivot points'
            }
        
        # Tạo channels cho mỗi pivot
        channels = []
        
        for idx in range(len(pivot_values)):
            hi, lo, base_strength = self.get_sr_values(
                pivot_values,
                idx,
                channel_width
            )
            
            # Tính thêm strength từ bars
            bar_strength = self.calculate_strength_from_bars(
                recent_df,
                hi,
                lo,
                self.loopback_period
            )
            
            total_strength = base_strength + bar_strength
            
            if total_strength >= self.min_strength * 20:
                channels.append({
                    'high': hi,
                    'low': lo,
                    'strength': total_strength
                })
        
        # Loại bỏ channels trùng lặp (ĐÃ SỬA)
        unique_channels = []
        seen_positions = set()
        
        for channel in channels:
            # Tạo key duy nhất cho channel (làm tròn đến 4 chữ số)
            key = (round(channel['low'], 4), round(channel['high'], 4))
            
            if key in seen_positions:
                # Tìm channel đã tồn tại
                for idx, existing in enumerate(unique_channels):
                    existing_key = (round(existing['low'], 4), round(existing['high'], 4))
                    if existing_key == key:
                        # Giữ channel có strength cao hơn
                        if channel['strength'] > existing['strength']:
                            unique_channels[idx] = channel
                        break
            else:
                seen_positions.add(key)
                unique_channels.append(channel)
        
        # Sắp xếp theo strength
        sorted_channels = sorted(
            unique_channels,
            key=lambda x: x['strength'],
            reverse=True
        )
        
        # Giữ top channels
        top_channels = sorted_channels[:self.max_channels]
        
        # Phân loại Support/Resistance
        current_price = df['close'].iloc[-1]
        supports = []
        resistances = []
        in_channel = None
        
        for channel in top_channels:
            if channel['high'] < current_price and channel['low'] < current_price:
                supports.append(channel)
            elif channel['high'] > current_price and channel['low'] > current_price:
                resistances.append(channel)
            else:
                in_channel = channel
        
        return {
            'success': True,
            'supports': supports,
            'resistances': resistances,
            'in_channel': in_channel,
            'all_channels': top_channels,
            'current_price': current_price,
            'channel_width': channel_width
        }
    
    def is_price_in_support(self, df: pd.DataFrame) -> bool:
        """
        Kiểm tra giá có nằm trong vùng support không
        
        Args:
            df: DataFrame
            
        Returns:
            bool: True nếu trong support zone
        """
        result = self.analyze(df)
        
        if not result['success']:
            return False
        
        # Kiểm tra có trong channel nào đó không
        if result['in_channel']:
            # Kiểm tra xem channel này gần support hay resistance hơn
            current_price = result['current_price']
            channel = result['in_channel']
            
            # Nếu giá gần đáy channel hơn → coi như support
            distance_to_low = abs(current_price - channel['low'])
            distance_to_high = abs(current_price - channel['high'])
            
            return distance_to_low < distance_to_high
        
        # Kiểm tra có support gần không (trong vòng 1% giá)
        current_price = result['current_price']
        tolerance = current_price * 0.01
        
        for support in result['supports']:
            if abs(current_price - support['high']) < tolerance:
                return True
        
        return False
    
    def is_price_in_resistance(self, df: pd.DataFrame) -> bool:
        """
        Kiểm tra giá có nằm trong vùng resistance không
        
        Args:
            df: DataFrame
            
        Returns:
            bool: True nếu trong resistance zone
        """
        result = self.analyze(df)
        
        if not result['success']:
            return False
        
        # Kiểm tra có trong channel nào đó không
        if result['in_channel']:
            # Kiểm tra xem channel này gần support hay resistance hơn
            current_price = result['current_price']
            channel = result['in_channel']
            
            # Nếu giá gần đỉnh channel hơn → coi như resistance
            distance_to_low = abs(current_price - channel['low'])
            distance_to_high = abs(current_price - channel['high'])
            
            return distance_to_high < distance_to_low
        
        # Kiểm tra có resistance gần không (trong vòng 1% giá)
        current_price = result['current_price']
        tolerance = current_price * 0.01
        
        for resistance in result['resistances']:
            if abs(current_price - resistance['low']) < tolerance:
                return True
        
        return False


def calculate_support_resistance(
    df: pd.DataFrame,
    pivot_period: int = 10,
    channel_width_percent: float = 5.0,
    loopback_period: int = 290
) -> Dict:
    """
    Hàm tiện ích tính S/R
    
    Args:
        df: DataFrame với high, low, close
        pivot_period: Chu kỳ pivot
        channel_width_percent: % độ rộng channel
        loopback_period: Số nến nhìn lại
        
    Returns:
        Dict kết quả
    """
    sr = SupportResistanceChannel(
        pivot_period=pivot_period,
        channel_width_percent=channel_width_percent,
        loopback_period=loopback_period
    )
    
    return sr.analyze(df)