"""
Quản lý database PostgreSQL cho bot
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

Base = declarative_base()


class WatchlistSymbol(Base):
    """
    Bảng lưu danh sách symbol đang theo dõi
    """
    __tablename__ = 'watchlist_symbols'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<WatchlistSymbol(symbol='{self.symbol}', active={self.is_active})>"


class SignalHistory(Base):
    """
    Bảng lưu lịch sử tín hiệu đã gửi (để tránh gửi trùng)
    """
    __tablename__ = 'signal_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(50), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    signal_time = Column(DateTime, nullable=False)
    price = Column(String(20), nullable=False)
    stoch_m15 = Column(String(10), nullable=False)
    stoch_h1 = Column(String(10), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SignalHistory(id='{self.signal_id}', symbol='{self.symbol}', type='{self.signal_type}')>"


class DatabaseManager:
    """
    Lớp quản lý database
    """
    
    def __init__(self, database_url=None):
        """
        Khởi tạo kết nối database
        """
        if database_url is None:
            database_url = config.DATABASE_URL
        
        # Psycopg3 dùng postgresql+psycopg thay vì postgresql+psycopg2
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
        
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_symbol(self, symbol):
        """
        Thêm symbol vào watchlist
        
        Args:
            symbol: Mã coin cần theo dõi (ví dụ: 'BTCUSDT')
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Chuẩn hóa symbol
            symbol = symbol.upper().replace('/', '')
            if not symbol.endswith('USDT'):
                symbol = symbol + 'USDT'
            
            # Kiểm tra đã tồn tại chưa
            existing = self.session.query(WatchlistSymbol).filter_by(symbol=symbol).first()
            
            if existing:
                if existing.is_active:
                    return False, f"❌ {symbol} đã có trong danh sách theo dõi"
                else:
                    # Kích hoạt lại
                    existing.is_active = True
                    self.session.commit()
                    return True, f"✅ Đã kích hoạt lại {symbol}"
            
            # Thêm mới
            new_symbol = WatchlistSymbol(symbol=symbol)
            self.session.add(new_symbol)
            self.session.commit()
            
            return True, f"✅ Đã thêm {symbol} vào danh sách theo dõi"
            
        except Exception as e:
            self.session.rollback()
            return False, f"❌ Lỗi: {str(e)}"
    
    def remove_symbol(self, symbol):
        """
        Xóa symbol khỏi watchlist
        
        Args:
            symbol: Mã coin cần xóa
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Chuẩn hóa symbol
            symbol = symbol.upper().replace('/', '')
            if not symbol.endswith('USDT'):
                symbol = symbol + 'USDT'
            
            # Tìm symbol
            existing = self.session.query(WatchlistSymbol).filter_by(symbol=symbol).first()
            
            if not existing or not existing.is_active:
                return False, f"❌ {symbol} không có trong danh sách theo dõi"
            
            # Đánh dấu không active (soft delete)
            existing.is_active = False
            self.session.commit()
            
            return True, f"✅ Đã xóa {symbol} khỏi danh sách theo dõi"
            
        except Exception as e:
            self.session.rollback()
            return False, f"❌ Lỗi: {str(e)}"
    
    def get_active_symbols(self):
        """
        Lấy danh sách symbol đang active
        
        Returns:
            list: Danh sách symbol
        """
        try:
            symbols = self.session.query(WatchlistSymbol).filter_by(is_active=True).all()
            return [s.symbol for s in symbols]
        except Exception as e:
            self.session.rollback()  # Thêm rollback
            print(f"Lỗi khi lấy danh sách symbol: {str(e)}")
            return []
    
    def get_watchlist_info(self):
        """
        Lấy thông tin chi tiết watchlist
        
        Returns:
            list: Danh sách dict chứa thông tin symbol
        """
        try:
            symbols = self.session.query(WatchlistSymbol).filter_by(is_active=True).order_by(WatchlistSymbol.added_at).all()
            return [{
                'symbol': s.symbol,
                'added_at': s.added_at
            } for s in symbols]
        except Exception as e:
            self.session.rollback()  # Thêm rollback
            print(f"Lỗi khi lấy thông tin watchlist: {str(e)}")
            return []
    
    def save_signal(self, signal_id, symbol, signal_type, signal_time, price, stoch_m15, stoch_h1):
        """
        Lưu lịch sử tín hiệu
        
        Args:
            signal_id: Unique ID của tín hiệu
            symbol: Mã coin
            signal_type: 'BUY' hoặc 'SELL'
            signal_time: Thời gian phát sinh tín hiệu
            price: Giá tại thời điểm tín hiệu
            stoch_m15: Giá trị Stoch M15
            stoch_h1: Giá trị Stoch H1
        """
        try:
            # Kiểm tra đã tồn tại chưa
            existing = self.session.query(SignalHistory).filter_by(signal_id=signal_id).first()
            if existing:
                return False  # Đã tồn tại
            
            signal = SignalHistory(
                signal_id=signal_id,
                symbol=symbol,
                signal_type=signal_type,
                signal_time=signal_time,
                price=str(price),
                stoch_m15=str(stoch_m15),
                stoch_h1=str(stoch_h1)
            )
            self.session.add(signal)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Lỗi khi lưu signal: {str(e)}")
            return False
    
    def check_signal_exists(self, signal_id):
        """
        Kiểm tra xem signal_id đã tồn tại chưa
        
        Args:
            signal_id: Unique ID của tín hiệu
            
        Returns:
            bool: True nếu đã tồn tại, False nếu chưa
        """
        try:
            existing = self.session.query(SignalHistory).filter_by(signal_id=signal_id).first()
            return existing is not None
        except Exception as e:
            self.session.rollback()  # Thêm rollback
            print(f"Lỗi khi kiểm tra signal: {str(e)}")
            return False
    
    def close(self):
        """Đóng kết nối database"""
        self.session.close()