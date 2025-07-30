#!/usr/bin/env python3
"""
Main entry point - Flask web + embedded Telegram bot
"""
import os
import sys
import logging
import threading
import asyncio
from datetime import datetime

# Добавляем путь
sys.path.insert(0, os.getcwd())

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('main')

# Flask приложение
from app import app

# Статус бота
bot_status = {"running": False, "started_at": None}

@app.route('/bot-status')
def bot_status_endpoint():
    """API для проверки статуса бота"""
    from flask import jsonify
    return jsonify(bot_status)

@app.route('/uptime')
def uptime_endpoint():
    """Uptime endpoint для внешних мониторингов"""
    from flask import jsonify
    import os
    return jsonify({
        "status": "alive",
        "bot_running": bot_status["running"],
        "timestamp": datetime.now().isoformat(),
        "uptime_url": f"https://{os.environ.get('REPL_SLUG', 'unknown')}.{os.environ.get('REPL_OWNER', 'unknown')}.repl.co/uptime"
    })

def run_telegram_bot():
    """Запуск Telegram бота в отдельном потоке"""
    global bot_status
    
    try:
        logger.info("🤖 Запуск встроенного Telegram бота")
        
        # Проверяем токен
        if not os.environ.get("BOT_TOKEN"):
            logger.error("❌ BOT_TOKEN не найден")
            return
        
        # Проверяем другие экземпляры
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'python.*bot'], capture_output=True)
        if result.returncode == 0:
            logger.warning("⚠️ Другие экземпляры бота уже запущены, пропускаем")
            return
            
        bot_status["running"] = True
        bot_status["started_at"] = datetime.now().isoformat()
        
        # Импортируем и запускаем обновленного бота
        from new_bot import main as bot_main
        
        # Создаем event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем бота
        loop.run_until_complete(bot_main())
        
    except Exception as e:
        bot_status["running"] = False
        logger.error(f"❌ Ошибка встроенного бота: {e}")

# Запускаем бота в фоновом потоке при импорте
try:
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    logger.info("✅ Telegram бот запущен в фоновом потоке")
except Exception as e:
    logger.error(f"❌ Ошибка запуска бота: {e}")

# This is the entry point for gunicorn
# Use: gunicorn --bind 0.0.0.0:5000 main:app
