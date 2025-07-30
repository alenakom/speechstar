#!/usr/bin/env python3
"""
Simple Flask app for Render - works without dependencies
"""
import os
import json
import logging
from flask import Flask, jsonify
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "render-secret-key")

@app.route('/')
def index():
    """Main page"""
    return jsonify({
        "status": "success",
        "service": "SpeechStar Bot Web Panel",
        "timestamp": datetime.now().isoformat(),
        "message": "🌟 Бот для развития речи детей работает!",
        "bot": "@SpeechStarBot",
        "description": "Развитие речи детей 6-36 месяцев",
        "features": [
            "✅ Ежедневные задания по возрастам",
            "✅ Подписочная модель (150₽/мес, 500₽ навсегда)", 
            "✅ ЮKassa платежи интегрированы",
            "✅ Автоматическая доставка заданий в 9:00 МСК",
            "✅ 100 промокодов для бесплатного доступа"
        ],
        "age_groups": [
            "9-14 месяцев",
            "15-19 месяцев"
        ],
        "endpoints": {
            "health_check": "/health",
            "bot_info": "/bot",
            "user_stats": "/stats"
        }
    })

@app.route('/health')
def health():
    """Health check for monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "speechstar-web",
        "uptime": "24/7"
    })

@app.route('/bot')
def bot_info():
    """Telegram bot information"""
    return jsonify({
        "bot_name": "SpeechStar Bot",
        "bot_username": "@SpeechStarBot",
        "bot_id": "8371213145", 
        "description": "Telegram бот для развития речи детей от 6 месяцев до 3 лет",
        "target_audience": "Родители с детьми 6-36 месяцев",
        "personality": "Теплая мама, делящаяся опытом",
        "subscription_model": {
            "trial": "7 дней бесплатно",
            "monthly": "150₽/месяц",
            "lifetime": "500₽ навсегда"
        },
        "features": {
            "daily_tasks": "Ежедневные задания в 9:00 МСК",
            "age_groups": 2,
            "payment_system": "ЮKassa",
            "promocodes": 100,
            "auto_scheduling": true
        }
    })

@app.route('/stats')
def stats():
    """User statistics"""
    try:
        # Try to load real user data if exists
        with open("users_data.json", "r", encoding="utf-8") as f:
            users = json.load(f)
            total_users = len(users)
            active_users = len([u for u in users.values() if u.get('subscription')])
    except FileNotFoundError:
        total_users = 0
        active_users = 0
        
    return jsonify({
        "total_users": total_users,
        "active_subscriptions": active_users,
        "service_status": "running",
        "deployment": "render.com",
        "timestamp": datetime.now().isoformat(),
        "message": f"Зарегистрировано {total_users} пользователей"
    })

@app.route('/webhook/yookassa', methods=['POST'])
def yookassa_webhook():
    """Simple webhook handler"""
    return jsonify({"status": "webhook_received", "timestamp": datetime.now().isoformat()})

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Page not found",
        "message": "Эта страница не найдена",
        "available_endpoints": ["/", "/health", "/bot", "/stats"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "Внутренняя ошибка сервера"
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting SpeechStar web service on port {port}")
    logger.info(f"🌐 Service will be available at https://speechstar.onrender.com")
    app.run(host='0.0.0.0', port=port, debug=False)
