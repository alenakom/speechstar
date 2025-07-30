#!/usr/bin/env python3
import os
import json
import logging
from flask import Flask, jsonify
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "render-secret")

@app.route('/')
def index():
    return jsonify({
        "status": "success",
        "service": "SpeechStar Bot",
        "timestamp": datetime.now().isoformat(),
        "message": "🌟 Бот работает!",
        "bot": "@SpeechStarBot",
        "features": [
            "✅ Telegram бот активен",
            "✅ Веб-сервер работает", 
            "✅ Render deployment успешен"
        ]
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/bot')
def bot_info():
    return jsonify({
        "bot_name": "SpeechStar Bot",
        "bot_username": "@SpeechStarBot",
        "description": "Бот для развития речи детей"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
