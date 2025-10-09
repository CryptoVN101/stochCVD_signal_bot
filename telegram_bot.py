"""
Bot Telegram - CryptoVN 101
CHỈ BÁO TÍN HIỆU ĐÚNG TIMEFRAME KHI NẾN ĐÓNG
"""

import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

import config
from database import DatabaseManager
from signal_scanner import SignalScanner

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Lớp quản lý Telegram Bot - BÁO TÍN HIỆU ĐÚNG TIMEFRAME"""
    
    def __init__(self):
        """Khởi tạo bot"""
        self.db = DatabaseManager()
        self.scanner = SignalScanner()
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Lưu timestamp nến đã quét
        self.last_scanned_m15 = None
        self.last_scanned_h1 = None
        
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("add", self.cmd_add))
        self.app.add_handler(CommandHandler("remove", self.cmd_remove))
        self.app.add_handler(CommandHandler("list", self.cmd_list))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        
        self._init_default_symbols()
    
    def _init_default_symbols(self):
        """Thêm các symbol mặc định vào database"""
        for symbol in config.DEFAULT_SYMBOLS:
            symbol_clean = symbol.replace('/', '')
            self.db.add_symbol(symbol_clean)
    
    def should_scan_now(self):
        """
        Kiểm tra xem có nên quét không (khi nến M15 hoặc H1 vừa đóng)
        
        Returns:
            tuple: (should_scan, timeframe) - ('m15', 'h1', 'both', hoặc None)
        """
        now = datetime.now(config.TIMEZONE)
        
        # Làm tròn về phút gần nhất
        current_minute = now.replace(second=0, microsecond=0)
        
        # Kiểm tra nến H1 (đóng vào phút :00)
        if current_minute.minute == 0:
            # Nến H1 vừa đóng
            if self.last_scanned_h1 != current_minute:
                self.last_scanned_h1 = current_minute
                self.last_scanned_m15 = current_minute  # M15 cũng đóng lúc :00
                logger.info(f"✓ Nến H1 & M15 vừa đóng: {current_minute.strftime('%H:%M %d-%m-%Y')}")
                return True, 'both'
        
        # Kiểm tra nến M15 (đóng vào phút :15, :30, :45)
        elif current_minute.minute % 15 == 0:
            # Nến M15 vừa đóng (không phải :00)
            if self.last_scanned_m15 != current_minute:
                self.last_scanned_m15 = current_minute
                logger.info(f"✓ Nến M15 vừa đóng: {current_minute.strftime('%H:%M %d-%m-%Y')}")
                return True, 'm15'
        
        return False, None
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /start"""
        welcome_msg = """
🤖 <b>Bot CryptoVN 101 - Tín hiệu Stoch + S/R</b>

Chào mừng! Bot sẽ tự động gửi tín hiệu:

<b>📊 Stoch + S/R</b>
- Stochastic thỏa ngưỡng (H1 & M15)
- Price Action tại vùng Support/Resistance
- Kiểm tra trên cả khung M15 và H1

<b>Các lệnh:</b>
/add BTCUSDT - Thêm coin
/remove BTCUSDT - Xóa coin
/list - Xem danh sách
/help - Hướng dẫn chi tiết
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
            await update.message.reply_text("📋 Danh sách theo dõi đang trống")
            return
        
        msg = f"📋 <b>Danh sách đang theo dõi ({len(watchlist)} coin):</b>\n\n"
        
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

<b>2. Xóa coin:</b>
/remove BTCUSDT

<b>3. Xem danh sách:</b>
/list

<b>4. Tín hiệu Stoch + S/R:</b>

🟢 <b>LONG (MUA):</b>
- Stoch H1 < 25 & M15 < 25
- Nến chạm vùng hỗ trợ trên M15 và/hoặc H1

🔴 <b>SHORT (BÁN):</b>
- Stoch H1 > 75 & M15 > 75
- Nến chạm vùng kháng cự trên M15 và/hoặc H1

⚠️ <b>Lưu ý:</b>
- Đây chỉ là công cụ hỗ trợ
- Luôn sử dụng stop loss
- Không giao dịch toàn bộ vốn
"""
        await update.message.reply_text(help_msg, parse_mode=ParseMode.HTML)
    
    def format_signal_message(self, signal):
        """Format message cho tín hiệu - CHỈ STOCH"""
        symbol = signal['symbol']
        signal_type = signal['signal_type']
        price = signal['price']
    
        icon = "🟢" if signal_type == 'BUY' else "🔴"
        type_text = "BUY/LONG" if signal_type == 'BUY' else "SELL/SHORT"
    
        message = f"🔶 Token: {symbol} (Bybit)\n\n"
        message += f"{icon} Tín hiệu đảo chiều {type_text}\n\n"
        message += f"⏰ Khung thời gian: H1 & M15\n\n"
        message += f"💰 Giá xác nhận: ${price:.4f}\n\n"
        message += f"📊 Stoch %K H1/M15: {signal['stoch_k_h1']:.2f} / {signal['stoch_k_m15']:.2f}\n"
        message += f"📊 Stoch %D H1/M15: {signal['stoch_d_h1']:.2f} / {signal['stoch_d_m15']:.2f}"
    
        return message.strip()
    
    async def send_signal_to_channel(self, signal):
        """Gửi tín hiệu lên channel"""
        try:
            message = self.format_signal_message(signal)
            
            await self.app.bot.send_message(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                text=message
            )
            
            logger.info(f"Đã gửi tín hiệu {signal['signal_type']} cho {signal['symbol']}")
            
            saved = self.db.save_signal(
                signal_id=signal['signal_id'],
                symbol=signal['symbol'],
                signal_type=signal['signal_type'],
                signal_time=signal['signal_time'],
                price=signal['price'],
                stoch_m15=signal['stoch_d_m15'],
                stoch_h1=signal['stoch_d_h1']
            )
            
            if saved:
                logger.info(f"Đã lưu tín hiệu vào database (ID: {signal['signal_id']})")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi tín hiệu: {str(e)}")
    
    def filter_signal_by_timeframe(self, signal, scan_timeframe):
        """
        Lọc tín hiệu theo timeframe đang quét
        
        Args:
            signal: Tín hiệu từ scanner
            scan_timeframe: 'm15', 'h1', hoặc 'both'
            
        Returns:
            bool: True nếu được phép gửi, False nếu bỏ qua
        """
        if not signal:
            return False
        
        timeframes = signal.get('timeframes', '')
        
        # Nếu đang quét H1 (cả H1 và M15 đóng cùng lúc)
        if scan_timeframe == 'both':
            # Gửi tất cả tín hiệu (cả M15 only, H1 only, và M15 & H1)
            return True
        
        # Nếu đang quét M15 (chỉ M15 đóng, H1 chưa đóng)
        elif scan_timeframe == 'm15':
            # CHỈ gửi tín hiệu M15 only (không có H1)
            # Nếu có H1 thì đợi đến khi H1 đóng
            if 'H1' in timeframes:
                logger.debug(f"Bỏ qua tín hiệu {signal['symbol']} (có H1, đợi đến giờ :00)")
                return False
            return True
        
        return False
    
    async def scan_loop(self):
        """Vòng lặp quét tín hiệu - BÁO ĐÚNG TIMEFRAME"""
        logger.info("Bắt đầu vòng lặp quét tín hiệu (báo đúng timeframe khi nến đóng)...")
        
        while True:
            try:
                # Kiểm tra xem có nên quét không
                should_scan, timeframe = self.should_scan_now()
                
                if not should_scan:
                    # Chưa đến lúc quét, đợi 30 giây
                    await asyncio.sleep(30)
                    continue
                
                # Đến lúc quét
                logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.info(f"BẮT ĐẦU QUÉT ({timeframe.upper()})")
                logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                symbols = self.db.get_active_symbols()
                
                if not symbols:
                    logger.warning("Không có symbol nào trong watchlist")
                    await asyncio.sleep(30)
                    continue
                
                logger.info(f"Quét {len(symbols)} symbols...")
                
                signal_count = 0
                for symbol in symbols:
                    try:
                        signal = self.scanner.check_signal(symbol)
                        
                        # Lọc tín hiệu theo timeframe
                        if not self.filter_signal_by_timeframe(signal, timeframe):
                            continue
                        
                        if signal:
                            signal_id = signal['signal_id']
                            
                            if not self.db.check_signal_exists(signal_id):
                                await self.send_signal_to_channel(signal)
                                signal_count += 1
                            else:
                                logger.debug(f"Signal {signal_id} đã tồn tại, skip")
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Lỗi khi quét {symbol}: {str(e)}")
                        continue
                
                logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.info(f"HOÀN THÀNH: Gửi {signal_count} tín hiệu mới")
                logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                # Đợi 30 giây trước khi check lại
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp quét: {str(e)}")
                await asyncio.sleep(60)
    
    async def start_bot(self):
        """Khởi động bot"""
        logger.info("Khởi động bot...")
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        
        logger.info("Bot đã sẵn sàng! Chỉ báo tín hiệu đúng timeframe khi nến đóng")
        
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