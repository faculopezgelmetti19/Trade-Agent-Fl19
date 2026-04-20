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
BX_KEY = os.getenv('BINGX_KEY')
BX_SECRET = os.getenv('BINGX_SECRET')

bot = telebot.TeleBot(TOKEN)

# --- 2. CONEXIÓN BINGX (ESTÁNDAR) ---
def conectar_exchange():
    return ccxt.bingx({
        'apiKey': BX_KEY,
        'secret': BX_SECRET,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap', # CCXT usa 'swap' internamente para BingX
        }
    })

exchange = conectar_exchange()
exchange.set_sandbox_mode(True)

# --- 3. LÓGICA IA ---
def consultar_ia(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content'].upper()
    except: return "NADA"

# --- 4. MOTOR AUTOMÁTICO ---
def motor_trading():
    while True:
        try:
            # Monitoreo de activos y trades
            balance = exchange.fetch_balance()
            vst_saldo = float(balance.get('total', {}).get('VST', 0))

            if vst_saldo > 20:
                # Escaneo simple
                ticker = exchange.fetch_ticker('BTC-USDT')
                if "COMPRAR" in consultar_ia("BTC está subiendo. ¿Comprar? SOLO 'COMPRAR' o 'NADA'"):
                    params = {'positionSide': 'LONG'}
                    exchange.create_market_buy_order('BTC-USDT', 0.001, params)
                    bot.send_message(CHAT_ID, "🎯 Compra automática realizada en Estándar.")
            
            time.sleep(60)
        except Exception as e:
            print(f"Error motor: {e}")
            time.sleep(30)

# --- 5. COMANDOS ---

@bot.message_handler(commands=['activos'])
def cmd_activos(message):
    try:
        # En BingX, fetch_balance suele traer todo el balance de la cuenta
        balance = exchange.fetch_balance()
        reporte = "🏦 **BILLETERA ACTUAL:**\n"
        hay_datos = False

        # Buscamos VST y otras monedas
        for asset, total in balance.get('total', {}).items():
            if float(total) > 0:
                reporte += f"• **{asset}:** {total}\n"
                hay_datos = True

        # Posiciones
        posiciones = exchange.fetch_positions()
        activas = [p for p in posiciones if float(p.get('contracts', 0)) > 0]
        
        if activas:
            reporte += "\n📊 **POSICIONES:**\n"
            for p in activas:
                reporte += f"🔹 {p['symbol']} | PNL: {p['unrealizedPnl']} VST\n"
        
        if not hay_datos and not activas:
            reporte = "📭 No se detectaron activos. Asegúrate de tener VST en la cuenta de Futuros."

        bot.send_message(CHAT_ID, reporte)
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al leer activos: {e}")

@bot.message_handler(commands=['test_volatil'])
def cmd_test_volatil(message):
    bot.send_message(CHAT_ID, "🧪 Intentando compra de prueba en DOGE-USDT...")
    try:
        # Eliminamos el parámetro 'type': 'standard' que causaba el error
        # Usamos el formato que funcionó antes
        params = {'positionSide': 'LONG'}
        ticker = exchange.fetch_ticker('DOGE-USDT')
        cantidad = 20 / ticker['last']
        
        order = exchange.create_market_buy_order('DOGE-USDT', cantidad, params)
        bot.send_message(CHAT_ID, f"✅ **TEST OK**\nOrden ID: {order['id']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=motor_trading, daemon=True).start()
    bot.polling(none_stop=True)
