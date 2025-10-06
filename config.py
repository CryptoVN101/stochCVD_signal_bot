"""
File cấu hình cho bot
"""

import os
from dotenv import load_dotenv
import pytz

# Load biến môi trường từ file .env
load_dotenv()

# ============================================
# CẤU HÌNH MÚIGỜ
# ============================================
TIMEZONE = pytz.timezone('Asia/Ho_Chi_Minh')  # Múi giờ Việt Nam UTC+7

# ============================================
# CẤU HÌNH TELEGRAM BOT
# ============================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', 'YOUR_CHANNEL_ID_HERE')

# ============================================
# CẤU HÌNH DATABASE (PostgreSQL)
# ============================================
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/stochcvd_db')

# ============================================
# CẤU HÌNH CHỈ BÁO STOCHASTIC
# ============================================
STOCH_K_PERIOD = 16      # %K Length
STOCH_K_SMOOTH = 16      # %K Smoothing
STOCH_D_SMOOTH = 8       # %D Smoothing

# ============================================
# CẤU HÌNH CHỈ BÁO CVD
# ============================================
CVD_DIVERGENCE_PERIOD = 2        # Divergence Fractal Periods
CVD_PERIOD = 24                  # CVD Period
CVD_CUMULATIVE_MODE = 'EMA'      # Cumulative Mode: 'Periodic' hoặc 'EMA'
CVD_MARKET_TYPE = 'Crypto'       # Market Ultra Data: 'Crypto', 'Forex', 'Stock'
CVD_MIN_SWING_DISTANCE = 5       # Khoảng cách tối thiểu giữa 2 pivot (số nến)

# ============================================
# CẤU HÌNH ĐIỀU KIỆN TÍN HIỆU
# ============================================
# Ngưỡng Stochastic
STOCH_OVERSOLD = 20   # Ngưỡng quá bán
STOCH_OVERBOUGHT = 80 # Ngưỡng quá mua

# Ngưỡng H1 cho tín hiệu
STOCH_H1_THRESHOLD_LOW = 25   # Ngưỡng thấp H1
STOCH_H1_THRESHOLD_HIGH = 75  # Ngưỡng cao H1

# Tỷ lệ win
WIN_RATE_NORMAL = 60  # Tỷ lệ win thường
WIN_RATE_HIGH = 80    # Tỷ lệ win cao

# ============================================
# CẤU HÌNH KHUNG THỜI GIAN
# ============================================
TIMEFRAME_M15 = '15m'  # Khung 15 phút
TIMEFRAME_H1 = '1h'    # Khung 1 giờ

# Số lượng nến cần lấy để phân tích
CANDLES_LIMIT = 500

# ============================================
# CẤU HÌNH BOT
# ============================================
# Thời gian quét (giây)
SCAN_INTERVAL = 60  # Quét mỗi 60 giây

# Danh sách coin/token mặc định
DEFAULT_SYMBOLS = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
]

# ============================================
# CẤU HÌNH HIỂN THỊ
# ============================================
# Template message
MESSAGE_TEMPLATE = """
🔶 Token: {symbol}
{signal_icon} Tín hiệu đảo chiều {signal_type}
⏰ Khung thời gian: M15
💰 Giá xác nhận: {price}
🔍 Tỷ lệ Win: {win_rate}%
---------------------------------
Thời gian gốc: {original_time}
Thời gian xác nhận: {confirm_time}
Stoch (M15/H1): {stoch_m15:.2f} / {stoch_h1:.2f}
"""

# Emoji cho tín hiệu
SIGNAL_EMOJI_BUY = "🟢"
SIGNAL_EMOJI_SELL = "🔴"

# ============================================
# CẤU HÌNH LOGGING
# ============================================
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ============================================
# CẤU HÌNH SUPPORT/RESISTANCE CHANNEL (H1)
# ============================================
SR_PIVOT_PERIOD = 10              # Chu kỳ pivot
SR_CHANNEL_WIDTH_PERCENT = 5.0    # % độ rộng channel
SR_LOOPBACK_PERIOD = 290          # Số nến nhìn lại
SR_MIN_STRENGTH = 1               # Strength tối thiểu
SR_MAX_CHANNELS = 6               # Số channels hiển thị
SR_ENABLED = True                 # Bật/tắt filter S/R

# ============================================
# CẤU HÌNH S/R CHO KHUNG M15 (RIÊNG)
# ============================================
SR_M15_PIVOT_PERIOD = 5               # Pivot nhỏ hơn H1
SR_M15_CHANNEL_WIDTH_PERCENT = 3.0    # Hẹp hơn H1
SR_M15_LOOPBACK_PERIOD = 200          # Ít hơn H1
SR_M15_MIN_STRENGTH = 1
SR_M15_MAX_CHANNELS = 6

# ============================================
# CẤU HÌNH LOẠI TÍN HIỆU
# ============================================
SIGNAL_STOCH_SR_ENABLED = True    # Bật tín hiệu Stoch + S/R