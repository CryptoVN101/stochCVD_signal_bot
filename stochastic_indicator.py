"""
Chỉ báo Stochastic Oscillator
Tính toán chỉ số %K và %D
"""

import pandas as pd
import numpy as np


class StochasticIndicator:
    """
    Lớp tính toán chỉ báo Stochastic
    """
    
    def __init__(self, k_period=16, k_smooth=16, d_smooth=8):
        """
        Khởi tạo chỉ báo Stochastic
        
        Args:
            k_period: Độ dài chu kỳ %K - mặc định 16
            k_smooth: Độ làm mượt %K - mặc định 16  
            d_smooth: Độ làm mượt %D - mặc định 8
        """
        self.k_period = k_period
        self.k_smooth = k_smooth
        self.d_smooth = d_smooth
    
    def calculate(self, df):
        """
        Tính toán chỉ báo Stochastic
        
        Args:
            df: DataFrame với cột ['high', 'low', 'close']
            
        Returns:
            tuple: (%K, %D)
        """
        # Tính highest high và lowest low trong k_period
        highest_high = df['high'].rolling(window=self.k_period).max()
        lowest_low = df['low'].rolling(window=self.k_period).min()
        
        # Tính %K chưa làm mượt
        raw_k = 100 * (df['close'] - lowest_low) / (highest_high - lowest_low)
        
        # Xử lý chia cho 0
        raw_k = raw_k.fillna(50)
        
        # Làm mượt %K bằng SMA
        k_line = raw_k.rolling(window=self.k_smooth).mean()
        
        # Tính %D (SMA của %K)
        d_line = k_line.rolling(window=self.d_smooth).mean()
        
        return k_line, d_line
    
    def analyze(self, df):
        """
        Phân tích đầy đủ Stochastic
        
        Args:
            df: DataFrame với cột ['high', 'low', 'close']
            
        Returns:
            dict: Kết quả phân tích
        """
        # Tính toán %K và %D
        k_line, d_line = self.calculate(df)
        
        # Lấy giá trị hiện tại
        current_k = k_line.iloc[-1]
        current_d = d_line.iloc[-1]
        
        # Xác định trạng thái
        oversold = current_k < 20  # Quá bán
        overbought = current_k > 80  # Quá mua
        
        result = {
            'success': True,
            'k_value': current_k,
            'd_value': current_d,
            'oversold': oversold,
            'overbought': overbought,
            'k_series': k_line,
            'd_series': d_line
        }
        
        return result


# Hàm tiện ích
def calculate_stochastic(df, k_period=16, k_smooth=16, d_smooth=8):
    """
    Hàm tiện ích tính Stochastic
    
    Args:
        df: DataFrame với cột ['high', 'low', 'close']
        k_period: Độ dài chu kỳ %K
        k_smooth: Độ làm mượt %K
        d_smooth: Độ làm mượt %D
        
    Returns:
        dict: Kết quả phân tích
    """
    indicator = StochasticIndicator(k_period, k_smooth, d_smooth)
    return indicator.analyze(df)