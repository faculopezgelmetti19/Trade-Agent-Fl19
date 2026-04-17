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

try:
    exchange = ccxt.bingx({
        'apiKey': BX_KEY,
        'secret': BX_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
    exchange.set_sandbox_mode(True)
except Exception as e:
    print(f"❌ Error conexión: {e}")
    exchange = None

# --- 2. LÓGICA IA ---
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

# --- 3. MOTOR AUTOMÁTICO ---
def motor_trading():
    while True:
        try:
            if not exchange: time.sleep(10); continue

            # VENTA AUTO
            posiciones = exchange.fetch_positions()
            activas = [p for p in posiciones if float(p.get('contracts', 0)) > 0]
            for p in activas:
                if "CERRAR" in consultar_ia(f"PNL {p['unrealizedPnl']} en {p['symbol']}. ¿Cerrar? Responde SOLO: 'CERRAR' o 'NADA'"):
                    exchange.create_market_sell_order(p['symbol'], p['contracts'], {'positionSide': 'LONG'})
                    bot.send_message(CHAT_ID, f"💰 **VENTA AUTO:** {p['symbol']} cerrada.")

            # COMPRA AUTO
            balance = exchange.fetch_balance()
            saldo = float(balance.get('total', {}).get('VST', 0))
            if saldo > 20:
                tickers = exchange.fetch_tickers()
                top = sorted([t for t in tickers.items() if '-USDT' in t[0]], key=lambda x: x[1]['percentage'] or 0, reverse=True)[:10]
                for simbolo, datos in top:
                    if "COMPRAR" in consultar_ia(f"Comprar {simbolo}? Responde SOLO: 'COMPRAR' o 'NADA'"):
                        monto = saldo * 0.15
                        exchange.create_market_buy_order(simbolo, monto / datos['last'], {'positionSide': 'LONG'})
                        bot.send_message(CHAT_ID, f"🎯 **COMPRA AUTO:** {simbolo}")
                        break
            time.sleep(60)
        except Exception as e: print(f"Error: {e}"); time.sleep(30)

# --- 4. COMANDOS ---

@bot.message_handler(commands=['activos'])
def cmd_activos(message):
    try:
        balance = exchange.fetch_balance()
        reporte = "🏦 **ACTIVOS:**\n"
        for asset, total in balance.get('total', {}).items():
            if float(total) > 0: reporte += f"• {asset}: {total}\n"
        
        pos = exchange.fetch_positions()
        activas = [p for p in pos if float(p.get('contracts', 0)) > 0]
        if activas:
            reporte += "\n📊 **POSICIONES:**\n"
            for p in activas:
                reporte += f"🔹 {p['symbol']} | PNL: {p['unrealizedPnl']} VST\n"
        bot.send_message(CHAT_ID, reporte)
    except: bot.send_message(CHAT_ID, "❌ Error al leer activos.")

@bot.message_handler(commands=['test_volatil'])
def cmd_test_volatil(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "🧪 Iniciando test de 20 USD en DOGE-USDT...")
    try:
        simbolo = 'DOGE-USDT'
        ticker = exchange.fetch_ticker(simbolo)
        precio = ticker['last']
        
        # Calculamos cantidad para que sean exactamente 20 USD
        monto_usd = 20
        cantidad = monto_usd / precio
        
        params = {'positionSide': 'LONG'}
        order = exchange.create_market_buy_order(simbolo, cantidad, params)
        
        bot.send_message(CHAT_ID, f"✅ **TEST EXITOSO**\n💎 Moneda: {simbolo}\n💵 Invertido: ${monto_usd}\n📦 Cantidad: {cantidad:.2f} DOGE\n🚀 Ya la podés ver en /activos")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error en test: {e}")

if __name__ == "__main__":
    bot.send_message(CHAT_ID, "🚀 Bot iniciado. Probá el comando /test_volatil")
    threading.Thread(target=motor_trading, daemon=True).start()
    bot.polling(none_stop=True)
