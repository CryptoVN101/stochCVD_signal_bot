"""
Bot Telegram - CryptoVN 101
Gửi tín hiệu giao dịch lên channel
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

import config
from database import DatabaseManager
from signal_scanner import SignalScanner

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Lớp quản lý Telegram Bot
    """
    
    def __init__(self):
        """Khởi tạo bot"""
        self.db = DatabaseManager()
        self.scanner = SignalScanner()
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Đăng ký các lệnh
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("add", self.cmd_add))
        self.app.add_handler(CommandHandler("remove", self.cmd_remove))
        self.app.add_handler(CommandHandler("list", self.cmd_list))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        
        # Thêm các symbol mặc định nếu chưa có
        self._init_default_symbols()
    
    def _init_default_symbols(self):
        """Thêm các symbol mặc định vào database"""
        for symbol in config.DEFAULT_SYMBOLS:
            symbol_clean = symbol.replace('/', '')
            self.db.add_symbol(symbol_clean)
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /start"""
        welcome_msg = """
🤖 <b>Bot CryptoVN 101 - Tín hiệu StochCVD</b>

Chào mừng! Bot sẽ tự động gửi tín hiệu giao dịch lên channel.

<b>Các lệnh có sẵn:</b>
/add BTCUSDT - Thêm coin vào danh sách theo dõi
/remove BTCUSDT - Xóa coin khỏi danh sách
/list - Xem danh sách đang theo dõi
/help - Hướng dẫn sử dụng

<b>Thiết lập:</b>
📊 CVD: Fractal=1, Period=16, Mode=EMA, Khung H1
📈 Stochastic: K=16, Smooth=16, D=8
📍 Support/Resistance: Filter tín hiệu tại vùng quan trọng

<b>Điều kiện tín hiệu:</b>
🟢 BUY: CVD phân kỳ tăng + Stoch H1<25 & M15<25 + Low chạm Support
🔴 SELL: CVD phân kỳ giảm + Stoch H1>75 & M15>75 + High chạm Resistance
"""
        await update.message.reply_text(welcome_msg, parse_mode=ParseMode.HTML)
    
    async def cmd_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /add SYMBOL"""
        if not context.args:
            await update.message.reply_text("⚠️ Cách dùng: /add BTCUSDT")
            return
        
        symbol = context.args[0]
        success, message = self.db.add_symbol(symbol)
        await update.message.reply_text(message)
        
        if success:
            logger.info(f"Đã thêm {symbol} vào watchlist")
    
    async def cmd_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /remove SYMBOL"""
        if not context.args:
            await update.message.reply_text("⚠️ Cách dùng: /remove BTCUSDT")
            return
        
        symbol = context.args[0]
        success, message = self.db.remove_symbol(symbol)
        await update.message.reply_text(message)
        
        if success:
            logger.info(f"Đã xóa {symbol} khỏi watchlist")
    
    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /list"""
        watchlist = self.db.get_watchlist_info()
        
        if not watchlist:
            await update.message.reply_text("📝 Danh sách theo dõi đang trống")
            return
        
        msg = f"📝 <b>Danh sách đang theo dõi ({len(watchlist)} coin):</b>\n\n"
        
        for idx, item in enumerate(watchlist, 1):
            added_time = item['added_at'].strftime('%d-%m-%Y %H:%M')
            msg += f"{idx}. <code>{item['symbol']}</code>\n"
            msg += f"   ├ Thêm lúc: {added_time}\n\n"
        
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /help"""
        help_msg = """
📚 <b>HƯỚNG DẪN SỬ DỤNG BOT</b>

<b>1. Thêm coin theo dõi:</b>
/add BTCUSDT
/add BTC (tự động thêm USDT)
/add ETH

<b>2. Xóa coin:</b>
/remove BTCUSDT
/remove BTC

<b>3. Xem danh sách:</b>
/list

<b>4. Giải thích tín hiệu:</b>

🟢 <b>Tín hiệu BUY/LONG:</b>
- CVD báo phân kỳ tăng trên H1
- Stochastic H1 < 25 VÀ M15 < 25
- Low của nến chạm vùng Support
→ Tín hiệu đảo chiều tăng

🔴 <b>Tín hiệu SELL/SHORT:</b>
- CVD báo phân kỳ giảm trên H1
- Stochastic H1 > 75 VÀ M15 > 75
- High của nến chạm vùng Resistance
→ Tín hiệu đảo chiều giảm

⚠️ <b>Lưu ý:</b>
- Đây chỉ là công cụ hỗ trợ
- Luôn sử dụng stop loss
- Không giao dịch toàn bộ vốn
"""
        await update.message.reply_text(help_msg, parse_mode=ParseMode.HTML)
    
    def format_signal_message(self, signal):
        """
        Format message tín hiệu
        
        Args:
            signal: Dict chứa thông tin tín hiệu
            
        Returns:
            str: Message đã format
        """
        symbol = signal['symbol']
        signal_type = signal['signal_type']
        price = signal['price']
        signal_time = signal['signal_time']
        confirm_time = signal['confirm_time']
        stoch_m15 = signal['stoch_m15']
        stoch_h1 = signal['stoch_h1']
        
        # Icon và text
        if signal_type == 'BUY':
            icon = "🟢"
            type_text = "BUY/LONG"
        else:
            icon = "🔴"
            type_text = "SELL/SHORT"
        
        # Format thời gian
        signal_time_str = signal_time.strftime('%H:%M %d-%m-%Y')
        confirm_time_str = confirm_time.strftime('%H:%M %d-%m-%Y')
        
        # Thêm thông tin S/R nếu có
        sr_info = ""
        if signal.get('sr_zone'):
            sr_zone = signal['sr_zone']
            if sr_zone['low'] and sr_zone['high']:
                zone_type = "Support" if sr_zone['type'] == 'support' else "Resistance"
                sr_info = f"📍 Vùng {zone_type}: ${sr_zone['low']:.4f} - ${sr_zone['high']:.4f}\n"
        
        message = f"""
🔶 Token: {symbol}
{icon} Tín hiệu đảo chiều {type_text}
⏰ Khung thời gian: H1
💰 Giá xác nhận: {price:.4f}
{sr_info}---------------------------------
Thời gian gốc: {signal_time_str}
Thời gian xác nhận: {confirm_time_str}
Stoch (M15/H1): {stoch_m15:.2f} / {stoch_h1:.2f}
"""
        return message.strip()
    
    async def send_signal_to_channel(self, signal):
        """
        Gửi tín hiệu lên channel
        
        Args:
            signal: Dict chứa thông tin tín hiệu
        """
        try:
            message = self.format_signal_message(signal)
            
            await self.app.bot.send_message(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                text=message
            )
            
            logger.info(f"Đã gửi tín hiệu {signal['signal_type']} cho {signal['symbol']}")
            
            # Lưu vào database
            saved = self.db.save_signal(
                signal_id=signal['signal_id'],
                symbol=signal['symbol'],
                signal_type=signal['signal_type'],
                signal_time=signal['signal_time'],
                price=signal['price'],
                stoch_m15=signal['stoch_m15'],
                stoch_h1=signal['stoch_h1']
            )
            
            if saved:
                logger.info(f"Đã lưu tín hiệu vào database (ID: {signal['signal_id']})")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi tín hiệu: {str(e)}")
    
    async def scan_loop(self):
        """
        Vòng lặp quét tín hiệu liên tục
        """
        logger.info("Bắt đầu quét tín hiệu...")
        
        while True:
            try:
                # Lấy danh sách symbols
                symbols = self.db.get_active_symbols()
                
                if not symbols:
                    logger.warning("Không có symbol nào trong watchlist")
                    await asyncio.sleep(60)
                    continue
                
                logger.info(f"Quét {len(symbols)} symbols...")
                
                # Quét từng symbol
                for symbol in symbols:
                    try:
                        # Kiểm tra tín hiệu
                        signal = self.scanner.check_signal(symbol)
                        
                        if signal:
                            # Kiểm tra xem đã gửi chưa bằng signal_id
                            signal_id = signal['signal_id']
                            
                            if not self.db.check_signal_exists(signal_id):
                                # Gửi tín hiệu
                                await self.send_signal_to_channel(signal)
                            else:
                                logger.info(f"Tín hiệu {signal['signal_type']} cho {symbol} đã được gửi trước đó (ID: {signal_id})")
                        
                        # Delay giữa các symbol để tránh rate limit
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Lỗi khi quét {symbol}: {str(e)}")
                        continue
                
                # Chờ trước khi quét lại (mặc định 60 giây)
                logger.info(f"Hoàn thành quét. Chờ {config.SCAN_INTERVAL} giây...")
                await asyncio.sleep(config.SCAN_INTERVAL)
                
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp quét: {str(e)}")
                await asyncio.sleep(60)
    
    async def start_bot(self):
        """Khởi động bot"""
        logger.info("Khởi động bot...")
        
        # Khởi tạo bot
        await self.app.initialize()
        await self.app.start()
        
        # Bắt đầu nhận lệnh
        await self.app.updater.start_polling(drop_pending_updates=True)
        
        logger.info("Bot đã sẵn sàng!")
        
        # Bắt đầu quét tín hiệu
        await self.scan_loop()
    
    async def stop_bot(self):
        """Dừng bot"""
        logger.info("Đang dừng bot...")
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
        self.db.close()
        logger.info("Bot đã dừng")
    
    def run(self):
        """Chạy bot"""
        try:
            asyncio.run(self.start_bot())
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng")
        except Exception as e:
            logger.error(f"Lỗi: {str(e)}")
        finally:
            asyncio.run(self.stop_bot())


if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()