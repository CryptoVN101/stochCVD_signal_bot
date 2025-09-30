"""
Main entry point - Khởi chạy bot
"""

import logging
from telegram_bot import TelegramBot

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    logger.info("="*60)
    logger.info("BOT CRYPTOVN 101 - STOCHCVD SIGNAL BOT")
    logger.info("="*60)
    
    try:
        bot = TelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"Lỗi khi chạy bot: {str(e)}")
        raise