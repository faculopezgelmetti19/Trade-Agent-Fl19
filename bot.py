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

# Configuración de Binance para TESTNET (Demo)
exchange = ccxt.binance({
    'apiKey': BINANCE_KEY,
    'secret': BINANCE_SECRET,
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(True) # OBLIGATORIO para usar Testnet

# --- 2. LÓGICA DE IA (GROQ) ---
def obtener_analisis_ia(moneda, precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{
            "role": "user", 
            "content": f"Analiza {moneda} a {precio} USDT. Responde SOLO: 'COMPRAR' o 'NADA'. Motivo 3 palabras."
        }]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content']
    except: return "NADA"

# --- 3. MOTOR DE TRADING AUTOMÁTICO ---
def loop_busqueda():
    print("🚀 Motor Binance TESTNET iniciado...")
    while True:
        try:
            # 1. Obtener saldo de la cuenta Demo
            balance = exchange.fetch_balance()
            saldo_usdt = float(balance['total'].get('USDT', 0))
            
            # 2. Escaneo de las 100 con más volumen/subida
            tickers = exchange.fetch_tickers()
            candidatos = [t for t in tickers.items() if t[0].endswith('/USDT')]
            top_100 = sorted(candidatos, key=lambda x: x[1]['percentage'] or 0, reverse=True)[:100]

            for simbolo, datos in top_100:
                precio = datos['last']
                analisis = obtener_analisis_ia(simbolo, precio)

                if "COMPRAR" in analisis.upper():
                    monto_usdt = saldo_usdt * 0.20 # Usamos el 20% del neto
                    
                    if monto_usdt >= 10: # Mínimo de Binance
                        # En Binance Testnet usamos quoteOrderQty para comprar una cantidad exacta de USDT
                        params = {'quoteOrderQty': exchange.cost_to_precision(simbolo, monto_usdt)}
                        order = exchange.create_market_buy_order(simbolo, None, params)
                        
                        msg = (f"🎯 **BINANCE DEMO: COMPRA**\n"
                               f"💎 Moneda: {simbolo}\n"
                               f"💵 Inversión: ${monto_usdt:.2f}\n"
                               f"📊 IA: {analisis}")
                        bot.send_message(CHAT_ID, msg)
                        
                        # Stop Loss del 60% (Lógica de monitoreo simplificada)
                        # Nota: En un bot pro, aquí guardaríamos el precio de compra en una DB
                        break 
            
            time.sleep(60) # Escanea cada 1 minuto
        except Exception as e:
            print(f"Error en loop: {e}")
            time.sleep(30)

# --- 4. COMANDOS TELEGRAM ---
@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    try:
        balance = exchange.fetch_balance()
        saldo = balance['total'].get('USDT', 0)
        bot.send_message(CHAT_ID, f"💰 **Saldo Testnet:** {saldo:.2f} USDT")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

# Iniciar hilo automático
threading.Thread(target=loop_busqueda, daemon=True).start()

if __name__ == "__main__":
    bot.polling(none_stop=True)
