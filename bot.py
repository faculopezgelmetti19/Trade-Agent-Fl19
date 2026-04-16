import os
import telebot
import requests
import ccxt
import time
import threading

# --- 1. CONFIGURACIÓN ---
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
        'options': {'defaultType': 'spot'}
    })
    exchange.set_sandbox_mode(True) 
    print("✅ Configuración de Binance Testnet cargada")
except Exception as e:
    print(f"❌ Error inicial: {e}")

# --- 2. LÓGICA DE IA ---
def obtener_analisis_ia(moneda, precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": f"Analiza {moneda} a {precio}. Responde SOLO: 'COMPRAR' o 'NADA'. Motivo 3 palabras."}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content']
    except: return "NADA"

# --- 3. COMANDOS TELEGRAM ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(CHAT_ID, "🚀 Bot Binance Testnet Online.\nComandos: /saldo, /analizar")

@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "⏳ Consultando a Binance Testnet...")
    try:
        balance = exchange.fetch_balance()
        # Buscamos USDT en el diccionario de totales
        saldo = balance.get('total', {}).get('USDT', 0)
        bot.send_message(CHAT_ID, f"💰 **Saldo en Testnet:** {saldo:.2f} USDT")
    except Exception as e:
        # Esto te va a escupir el error real en Telegram
        error_msg = str(e)
        bot.send_message(CHAT_ID, f"❌ Error de Conexión:\n`{error_msg[:150]}`", parse_mode="Markdown")

# --- 4. MOTOR AUTOMÁTICO (Loop de búsqueda) ---
def loop_trading():
    print("🤖 Motor automático encendido...")
    while True:
        try:
            # Escaneo de mercado cada 60 segundos
            tickers = exchange.fetch_tickers()
            candidatos = [t for t in tickers.items() if t[0].endswith('/USDT')]
            top_10 = sorted(candidatos, key=lambda x: x[1]['percentage'] or 0, reverse=True)[:10]

            for simbolo, datos in top_10:
                precio = datos['last']
                analisis = obtener_analisis_ia(simbolo, precio)

                if "COMPRAR" in analisis.upper():
                    # Aquí iría la ejecución de compra automática
                    print(f"Oportunidad detectada en {simbolo}")
            
            time.sleep(60)
        except Exception as e:
            print(f"Error en loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    # Mensaje de vida al arrancar
    try:
        bot.send_message(CHAT_ID, "🔌 Bot encendido en Railway. Probá /saldo")
    except: pass

    threading.Thread(target=loop_trading, daemon=True).start()
    bot.polling(none_stop=True)
