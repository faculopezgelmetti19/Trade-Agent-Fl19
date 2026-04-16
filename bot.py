import os
import telebot
import requests
import ccxt
import time
import threading

# --- CONFIGURACIÓN ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')
BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

bot = telebot.TeleBot(TOKEN)

# Conexión a Binance Testnet
try:
    exchange = ccxt.binance({
        'apiKey': BINANCE_KEY,
        'secret': BINANCE_SECRET,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True) 
    print("✅ Conectado a Binance Testnet")
except Exception as e:
    print(f"❌ Error al conectar con Binance: {e}")

# --- COMANDOS TELEGRAM ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(CHAT_ID, "🚀 Bot de Binance iniciado correctamente.")

@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    try:
        balance = exchange.fetch_balance()
        saldo = balance['total'].get('USDT', 0)
        bot.send_message(CHAT_ID, f"💰 **Saldo en Binance Testnet:** {saldo:.2f} USDT")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al consultar saldo: {e}")

# --- LOOP AUTOMÁTICO ---
def loop_trading():
    print("🤖 Motor automático encendido...")
    while True:
        try:
            # Escaneo simple cada 60 segundos
            tickers = exchange.fetch_tickers()
            # ... (tu lógica de trading aquí)
            time.sleep(60)
        except Exception as e:
            print(f"Error en loop: {e}")
            time.sleep(30)

# Iniciamos los procesos
if __name__ == "__main__":
    # Intentar mandar un mensaje al prenderse
    try:
        bot.send_message(CHAT_ID, "🔌 Bot encendido y conectado a Railway.")
    except:
        pass
        
    threading.Thread(target=loop_trading, daemon=True).start()
    print("🛰️ Bot esperando mensajes...")
    bot.polling(none_stop=True)
