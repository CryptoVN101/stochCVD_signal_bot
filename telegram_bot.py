"""
Bot Telegram - CryptoVN 101
Chỉ gửi tín hiệu Stoch + S/R
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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Lớp quản lý Telegram Bot - CHỈ STOCH + S/R"""
    
    def __init__(self):
        """Khởi tạo bot"""
        self.db = DatabaseManager()
        self.scanner = SignalScanner()
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
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
        """Format message cho tín hiệu"""
        symbol = signal['symbol']
        signal_type = signal['signal_type']
        price = signal['price']
    
        icon = "🟢" if signal_type == 'BUY' else "🔴"
        type_text = "BUY/LONG" if signal_type == 'BUY' else "SELL/SHORT"
    
        sr_type = signal.get('sr_type', 'support/resistance')
        timeframes = signal.get('timeframes', 'H1')
        sr_name = "hỗ trợ" if sr_type == 'support' else "kháng cự"
    
        message = f"🔶 Token: {symbol} (Bybit)\n\n"
        message += f"{icon} Tín hiệu đảo chiều {type_text}\n\n"
        message += f"⏰ Phản ứng với {sr_name} khung {timeframes}\n\n"
        message += f"💰 Giá xác nhận: ${price:.4f}"
        
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
                stoch_m15=signal['stoch_m15'],
                stoch_h1=signal['stoch_h1']
            )
            
            if saved:
                logger.info(f"Đã lưu tín hiệu vào database (ID: {signal['signal_id']})")
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi tín hiệu: {str(e)}")
    
    async def scan_loop(self):
        """Vòng lặp quét tín hiệu liên tục"""
        logger.info("Bắt đầu quét tín hiệu...")
        
        while True:
            try:
                symbols = self.db.get_active_symbols()
                
                if not symbols:
                    logger.warning("Không có symbol nào trong watchlist")
                    await asyncio.sleep(60)
                    continue
                
                logger.info(f"Quét {len(symbols)} symbols...")
                
                for symbol in symbols:
                    try:
                        signal = self.scanner.check_signal(symbol)
                        
                        if signal:
                            signal_id = signal['signal_id']
                            
                            if not self.db.check_signal_exists(signal_id):
                                await self.send_signal_to_channel(signal)
                            else:
                                logger.info(f"Tín hiệu {signal['signal_type']} cho {symbol} đã được gửi trước đó")
                        
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Lỗi khi quét {symbol}: {str(e)}")
                        continue
                
                logger.info(f"Hoàn thành quét. Chờ {config.SCAN_INTERVAL} giây...")
                await asyncio.sleep(config.SCAN_INTERVAL)
                
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp quét: {str(e)}")
                await asyncio.sleep(60)
    
    async def start_bot(self):
        """Khởi động bot"""
        logger.info("Khởi động bot...")
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        
        logger.info("Bot đã sẵn sàng! Chỉ gửi tín hiệu Stoch + S/R")
        
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