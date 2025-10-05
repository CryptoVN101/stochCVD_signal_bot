"""
Chỉ báo CVD (Cumulative Volume Delta) Divergence Oscillator
Tái tạo hoàn toàn từ TradingView Pine Script
"""

import pandas as pd
import numpy as np


class CVDIndicator:
    """
    Lớp tính toán chỉ báo CVD và phát hiện phân kỳ (divergence)
    """
    
    def __init__(self, divergence_period=2, cvd_period=24, cumulative_mode='EMA', min_swing_distance=5):
        """
        Khởi tạo chỉ báo CVD
        
        Args:
            divergence_period: Chu kỳ phát hiện phân kỳ (fractal period) - mặc định 2
            cvd_period: Chu kỳ tính CVD - mặc định 24
            cumulative_mode: Chế độ tích lũy 'Periodic' hoặc 'EMA' - mặc định 'EMA'
            min_swing_distance: Khoảng cách tối thiểu giữa 2 pivot (số nến) - mặc định 5
        """
        self.divergence_period = divergence_period
        self.cvd_period = cvd_period
        self.cumulative_mode = cumulative_mode
        self.min_swing_distance = min_swing_distance
        
    def calculate_delta(self, df):
        """
        Tính Volume Delta (chênh lệch khối lượng mua/bán)
        
        Args:
            df: DataFrame với cột ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            Series chứa giá trị delta
        """
        # Tính buying volume (khối lượng mua)
        buying_volume = df['volume'] * ((df['close'] - df['low']) / (df['high'] - df['low']))
        
        # Tính selling volume (khối lượng bán)
        selling_volume = df['volume'] * ((df['high'] - df['close']) / (df['high'] - df['low']))
        
        # Delta = Buying - Selling
        delta = buying_volume - selling_volume
        
        # Xử lý trường hợp high = low (tránh chia cho 0)
        delta = delta.fillna(0)
        
        return delta
    
    def calculate_cvd(self, df):
        """
        Tính Cumulative Volume Delta
        
        Args:
            df: DataFrame với cột ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            Series chứa giá trị CVD
        """
        # Tính delta
        delta = self.calculate_delta(df)
        
        # Tính CVD theo chế độ
        if self.cumulative_mode == 'Periodic':
            # Chế độ Periodic: Tổng delta trong chu kỳ
            cvd = delta.rolling(window=self.cvd_period).sum()
        else:  # EMA
            # Chế độ EMA: Trung bình động mũ của delta
            cvd = delta.ewm(span=self.cvd_period, adjust=False).mean()
        
        return cvd
    
    def find_pivot_high(self, series, period):
        """
        Tìm điểm pivot high (đỉnh)
        
        Args:
            series: Series giá trị cần tìm pivot
            period: Chu kỳ pivot
            
        Returns:
            Series boolean, True tại vị trí pivot high
        """
        pivot_high = pd.Series(False, index=series.index)
        
        for i in range(period, len(series) - period):
            # Kiểm tra xem điểm i có phải là đỉnh không
            is_pivot = True
            center_value = series.iloc[i]
            
            # So sánh với các điểm trước và sau
            for j in range(1, period + 1):
                if series.iloc[i - j] >= center_value or series.iloc[i + j] >= center_value:
                    is_pivot = False
                    break
            
            pivot_high.iloc[i] = is_pivot
        
        return pivot_high
    
    def find_pivot_low(self, series, period):
        """
        Tìm điểm pivot low (đáy)
        
        Args:
            series: Series giá trị cần tìm pivot
            period: Chu kỳ pivot
            
        Returns:
            Series boolean, True tại vị trí pivot low
        """
        pivot_low = pd.Series(False, index=series.index)
        
        for i in range(period, len(series) - period):
            # Kiểm tra xem điểm i có phải là đáy không
            is_pivot = True
            center_value = series.iloc[i]
            
            # So sánh với các điểm trước và sau
            for j in range(1, period + 1):
                if series.iloc[i - j] <= center_value or series.iloc[i + j] <= center_value:
                    is_pivot = False
                    break
            
            pivot_low.iloc[i] = is_pivot
        
        return pivot_low
    
    def detect_bearish_divergence(self, df, cvd):
        """
        Phát hiện phân kỳ giảm (Bearish Divergence)
        Giá tạo đỉnh cao hơn nhưng CVD tạo đỉnh thấp hơn
        
        Args:
            df: DataFrame giá
            cvd: Series CVD
            
        Returns:
            tuple: (has_divergence, divergence_info)
        """
        n = self.divergence_period
        
        # Tính EMA 50 để xác định xu hướng
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Tìm pivot high cho giá
        price_pivot_high = self.find_pivot_high(df['high'], n)
        
        # Lọc pivot trong uptrend (giá > EMA50)
        uptrend = df['close'] > ema_50
        price_pivot_high = price_pivot_high & uptrend
        
        # Lấy 2 pivot gần nhất
        pivot_indices = df.index[price_pivot_high].tolist()
        
        if len(pivot_indices) < 2:
            return False, None
        
        # Lấy 2 pivot cuối
        prev_pivot_idx = pivot_indices[-2]
        last_pivot_idx = pivot_indices[-1]
        
        # Tính khoảng cách giữa 2 pivot (số nến)
        if isinstance(df.index, pd.DatetimeIndex):
            prev_pos = df.index.get_loc(prev_pivot_idx)
            last_pos = df.index.get_loc(last_pivot_idx)
            distance = last_pos - prev_pos
        else:
            distance = last_pivot_idx - prev_pivot_idx
        
        # MỚI: Kiểm tra khoảng cách tối thiểu
        if distance < self.min_swing_distance:
            return False, None
        
        # Kiểm tra khoảng cách không quá xa (< 30 nến)
        if distance >= 30:
            return False, None
        
        # Lấy giá tại các pivot
        prev_price = df.loc[prev_pivot_idx, 'high']
        last_price = df.loc[last_pivot_idx, 'high']
        
        # Lấy CVD tại các pivot
        prev_cvd = cvd.loc[prev_pivot_idx]
        last_cvd = cvd.loc[last_pivot_idx]
        
        # Kiểm tra điều kiện phân kỳ giảm
        # Giá tăng nhưng CVD giảm
        # CVD phải > 0 (đang trong vùng mua)
        if (last_price > prev_price and 
            last_cvd < prev_cvd and 
            last_cvd > 0 and prev_cvd > 0):
            
            divergence_info = {
                'type': 'bearish',
                'prev_price': prev_price,
                'last_price': last_price,
                'prev_cvd': prev_cvd,
                'last_cvd': last_cvd,
                'prev_idx': prev_pivot_idx,
                'last_idx': last_pivot_idx
            }
            
            return True, divergence_info
        
        return False, None
    
    def detect_bullish_divergence(self, df, cvd):
        """
        Phát hiện phân kỳ tăng (Bullish Divergence)
        Giá tạo đáy thấp hơn nhưng CVD tạo đáy cao hơn
        
        Args:
            df: DataFrame giá
            cvd: Series CVD
            
        Returns:
            tuple: (has_divergence, divergence_info)
        """
        n = self.divergence_period
        
        # Tính EMA 50 để xác định xu hướng
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # Tìm pivot low cho giá
        price_pivot_low = self.find_pivot_low(df['low'], n)
        
        # Lọc pivot trong downtrend (giá < EMA50)
        downtrend = df['close'] < ema_50
        price_pivot_low = price_pivot_low & downtrend
        
        # Lấy 2 pivot gần nhất
        pivot_indices = df.index[price_pivot_low].tolist()
        
        if len(pivot_indices) < 2:
            return False, None
        
        # Lấy 2 pivot cuối
        prev_pivot_idx = pivot_indices[-2]
        last_pivot_idx = pivot_indices[-1]
        
        # Tính khoảng cách giữa 2 pivot (số nến)
        if isinstance(df.index, pd.DatetimeIndex):
            prev_pos = df.index.get_loc(prev_pivot_idx)
            last_pos = df.index.get_loc(last_pivot_idx)
            distance = last_pos - prev_pos
        else:
            distance = last_pivot_idx - prev_pivot_idx
        
        # MỚI: Kiểm tra khoảng cách tối thiểu
        if distance < self.min_swing_distance:
            return False, None
        
        # Kiểm tra khoảng cách không quá xa (< 30 nến)
        if distance >= 30:
            return False, None
        
        # Lấy giá tại các pivot
        prev_price = df.loc[prev_pivot_idx, 'low']
        last_price = df.loc[last_pivot_idx, 'low']
        
        # Lấy CVD tại các pivot
        prev_cvd = cvd.loc[prev_pivot_idx]
        last_cvd = cvd.loc[last_pivot_idx]
        
        # Kiểm tra điều kiện phân kỳ tăng
        # Giá giảm nhưng CVD tăng
        # CVD phải < 0 (đang trong vùng bán)
        if (last_price < prev_price and 
            last_cvd > prev_cvd and 
            last_cvd < 0 and prev_cvd < 0):
            
            divergence_info = {
                'type': 'bullish',
                'prev_price': prev_price,
                'last_price': last_price,
                'prev_cvd': prev_cvd,
                'last_cvd': last_cvd,
                'prev_idx': prev_pivot_idx,
                'last_idx': last_pivot_idx
            }
            
            return True, divergence_info
        
        return False, None
    
    def analyze(self, df):
        """
        Phân tích đầy đủ CVD và phát hiện phân kỳ
        
        Args:
            df: DataFrame với cột ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            dict: Kết quả phân tích
        """
        # Đảm bảo df có đủ dữ liệu
        if len(df) < 100:
            return {
                'success': False,
                'message': 'Không đủ dữ liệu để phân tích (cần ít nhất 100 nến)'
            }
        
        # Tính CVD
        cvd = self.calculate_cvd(df)
        
        # Phát hiện phân kỳ tăng
        has_bull_div, bull_info = self.detect_bullish_divergence(df, cvd)
        
        # Phát hiện phân kỳ giảm
        has_bear_div, bear_info = self.detect_bearish_divergence(df, cvd)
        
        # Lấy giá trị CVD hiện tại
        current_cvd = cvd.iloc[-1]
        
        result = {
            'success': True,
            'current_cvd': current_cvd,
            'has_bullish_divergence': has_bull_div,
            'bullish_divergence_info': bull_info,
            'has_bearish_divergence': has_bear_div,
            'bearish_divergence_info': bear_info,
            'cvd_series': cvd  # Trả về toàn bộ series để vẽ đồ thị nếu cần
        }
        
        return result


# Hàm tiện ích để sử dụng nhanh
def detect_cvd_divergence(df, divergence_period=2, cvd_period=24, cumulative_mode='EMA', min_swing_distance=5):
    """
    Hàm tiện ích phát hiện phân kỳ CVD
    
    Args:
        df: DataFrame với cột ['open', 'high', 'low', 'close', 'volume']
        divergence_period: Chu kỳ phân kỳ (mặc định 2)
        cvd_period: Chu kỳ CVD (mặc định 24)
        cumulative_mode: Chế độ tích lũy 'Periodic' hoặc 'EMA'
        min_swing_distance: Khoảng cách tối thiểu giữa swings (mặc định 5)
        
    Returns:
        dict: Kết quả phân tích
    """
    indicator = CVDIndicator(divergence_period, cvd_period, cumulative_mode, min_swing_distance)
    return indicator.analyze(df)