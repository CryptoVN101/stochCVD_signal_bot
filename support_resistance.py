"""
Chỉ báo Support/Resistance Channel
Phát hiện vùng hỗ trợ và kháng cự dựa trên pivot points
"""

import pandas as pd
import numpy as np


class SupportResistanceChannel:
    """
    Lớp tính toán vùng Support/Resistance Channel
    """
    
    def __init__(self, pivot_period=10, channel_width_percent=5.0, 
                 loopback_period=290, min_strength=1, max_channels=6):
        """
        Khởi tạo chỉ báo S/R
        
        Args:
            pivot_period: Chu kỳ pivot (default: 10)
            channel_width_percent: % độ rộng channel (default: 5.0)
            loopback_period: Số nến nhìn lại (default: 290)
            min_strength: Độ mạnh tối thiểu (default: 1)
            max_channels: Số channels tối đa (default: 6)
        """
        self.pivot_period = pivot_period
        self.channel_width_percent = channel_width_percent
        self.loopback_period = loopback_period
        self.min_strength = min_strength
        self.max_channels = max_channels
    
    def find_pivots(self, df):
        """
        Tìm các điểm pivot high và pivot low
        
        Args:
            df: DataFrame với cột ['high', 'low']
            
        Returns:
            DataFrame với cột ['ph', 'pl'] (pivot high/low)
        """
        result_df = df.copy()
        
        # Tính pivot high
        high_rolling = df['high'].rolling(
            window=2 * self.pivot_period + 1, 
            center=True
        ).max()
        result_df['ph'] = np.where(
            df['high'] == high_rolling, 
            df['high'], 
            np.nan
        )
        
        # Tính pivot low
        low_rolling = df['low'].rolling(
            window=2 * self.pivot_period + 1, 
            center=True
        ).min()
        result_df['pl'] = np.where(
            df['low'] == low_rolling, 
            df['low'], 
            np.nan
        )
        
        return result_df
    
    def calculate_channels(self, df):
        """
        Tính toán các kênh S/R
        
        Args:
            df: DataFrame với cột ['high', 'low', 'close']
            
        Returns:
            list: Danh sách các channel với format:
                  {'low': float, 'high': float, 'strength': int}
        """
        # Tìm pivots
        df_pivots = self.find_pivots(df)
        
        # Lấy dữ liệu trong loopback period
        lookback_start = max(0, len(df) - self.loopback_period)
        recent_data = df_pivots.iloc[lookback_start:]
        
        # Thu thập tất cả pivot points
        pivot_points = []
        for idx in range(len(recent_data)):
            if not np.isnan(recent_data['ph'].iloc[idx]):
                pivot_points.append({
                    'price': recent_data['ph'].iloc[idx],
                    'index': lookback_start + idx
                })
            if not np.isnan(recent_data['pl'].iloc[idx]):
                pivot_points.append({
                    'price': recent_data['pl'].iloc[idx],
                    'index': lookback_start + idx
                })
        
        if not pivot_points:
            return []
        
        # Sắp xếp theo index mới nhất
        pivot_points.sort(key=lambda x: x['index'], reverse=True)
        
        # Tính channel width tối đa
        lookback_300 = df.iloc[-300:] if len(df) >= 300 else df
        highest_300 = lookback_300['high'].max()
        lowest_300 = lookback_300['low'].min()
        max_channel_width = (highest_300 - lowest_300) * self.channel_width_percent / 100
        
        # Tìm các potential channels
        potential_channels = []
        
        for pivot in pivot_points:
            lo = pivot['price']
            hi = pivot['price']
            num_pp_in_channel = 0
            
            # Nhóm các pivot points gần nhau
            for other_pivot in pivot_points:
                cpp = other_pivot['price']
                
                # Tính width nếu thêm pivot này vào channel
                if cpp <= hi:
                    width = max(hi - cpp, cpp - lo)
                else:
                    width = cpp - lo
                
                if width <= max_channel_width:
                    lo = min(lo, cpp)
                    hi = max(hi, cpp)
                    num_pp_in_channel += 1
            
            # Tính strength
            strength = num_pp_in_channel * 20
            
            # Đếm số nến chạm vào channel
            lookback_check = min(self.loopback_period, len(df))
            for i in range(lookback_check):
                bar_idx = -1 - i
                high_price = df['high'].iloc[bar_idx]
                low_price = df['low'].iloc[bar_idx]
                
                # Kiểm tra nếu nến chạm channel
                if (high_price <= hi and high_price >= lo) or \
                   (low_price <= hi and low_price >= lo):
                    strength += 1
            
            # Lưu channel nếu đủ mạnh
            if strength >= self.min_strength * 20:
                potential_channels.append({
                    'high': hi,
                    'low': lo,
                    'strength': strength
                })
        
        # Sắp xếp theo strength
        potential_channels.sort(key=lambda x: x['strength'], reverse=True)
        
        # Loại bỏ channels bị bao phủ
        sr_channels = []
        for channel in potential_channels:
            if len(sr_channels) >= self.max_channels:
                break
            
            # Kiểm tra xem channel này có bị bao phủ bởi channel nào đã có không
            is_included = any(
                channel['high'] <= ex_ch['high'] and channel['low'] >= ex_ch['low']
                for ex_ch in sr_channels
            )
            
            if not is_included:
                sr_channels.append(channel)
        
        return sr_channels
    
    def analyze(self, df):
        """
        Phân tích đầy đủ S/R
        
        Args:
            df: DataFrame với cột ['high', 'low', 'close']
            
        Returns:
            dict: Kết quả phân tích với format:
                {
                    'success': bool,
                    'message': str (nếu lỗi),
                    'current_price': float,
                    'channel_width': float,
                    'all_channels': list,
                    'in_channel': dict hoặc None,
                    'supports': list,
                    'resistances': list
                }
        """
        try:
            if df is None or len(df) < self.pivot_period * 2 + 1:
                return {
                    'success': False,
                    'message': 'Không đủ dữ liệu để tính S/R'
                }
            
            # Tính channels
            channels = self.calculate_channels(df)
            
            if not channels:
                return {
                    'success': False,
                    'message': 'Không tìm thấy channel nào'
                }
            
            # Lấy giá hiện tại
            current_price = df['close'].iloc[-1]
            
            # Tính channel width
            lookback_300 = df.iloc[-300:] if len(df) >= 300 else df
            highest_300 = lookback_300['high'].max()
            lowest_300 = lookback_300['low'].min()
            channel_width = (highest_300 - lowest_300) * self.channel_width_percent / 100
            
            # Phân loại channels
            in_channel = None
            supports = []
            resistances = []
            
            for channel in channels:
                ch_low = channel['low']
                ch_high = channel['high']
                
                # Kiểm tra giá có nằm TRONG channel không
                if current_price >= ch_low and current_price <= ch_high:
                    # Chỉ lấy channel đầu tiên chứa giá
                    if in_channel is None:
                        in_channel = channel
                # Channel nằm dưới giá -> Support
                elif ch_high < current_price:
                    supports.append(channel)
                # Channel nằm trên giá -> Resistance
                elif ch_low > current_price:
                    resistances.append(channel)
            
            return {
                'success': True,
                'current_price': current_price,
                'channel_width': channel_width,
                'all_channels': channels,
                'in_channel': in_channel,
                'supports': supports,
                'resistances': resistances
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi phân tích S/R: {str(e)}'
            }


# Hàm tiện ích
def analyze_support_resistance(df, pivot_period=10, channel_width_percent=5.0,
                               loopback_period=290, min_strength=1, max_channels=6):
    """
    Hàm tiện ích phân tích S/R
    
    Args:
        df: DataFrame với cột ['high', 'low', 'close']
        pivot_period: Chu kỳ pivot
        channel_width_percent: % độ rộng channel
        loopback_period: Số nến nhìn lại
        min_strength: Độ mạnh tối thiểu
        max_channels: Số channels tối đa
        
    Returns:
        dict: Kết quả phân tích
    """
    sr = SupportResistanceChannel(
        pivot_period=pivot_period,
        channel_width_percent=channel_width_percent,
        loopback_period=loopback_period,
        min_strength=min_strength,
        max_channels=max_channels
    )
    return sr.analyze(df)