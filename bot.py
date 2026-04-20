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

# --- 2. CONEXIÓN BINGX (FORZANDO ESTÁNDAR) ---
try:
    exchange = ccxt.bingx({
        'apiKey': BX_KEY,
        'secret': BX_SECRET,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'standard', # Intentamos estándar de nuevo
        }
    })
    exchange.set_sandbox_mode(True)
    print("✅ Conectado a BingX Futuros Estándar")
except Exception as e:
    print(f"❌ Error conexión: {e}")
    exchange = None

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
    print("🤖 Motor en marcha...")
    while True:
        try:
            if not exchange: time.sleep(10); continue
            
            # Limpiamos caché de balance para forzar lectura fresca
            balance = exchange.fetch_balance({'type': 'standard'})
            saldo = float(balance.get('total', {}).get('VST', 0))

            # Lógica de Venta
            posiciones = exchange.fetch_positions(None, {'type': 'standard'})
            activas = [p for p in posiciones if float(p.get('contracts', 0)) > 0]
            
            for p in activas:
                if "CERRAR" in consultar_ia(f"Cerrar {p['symbol']} PNL {p['unrealizedPnl']}? SOLO 'CERRAR' o 'NADA'"):
                    exchange.create_market_sell_order(p['symbol'], p['contracts'], {'positionSide': 'LONG'})
                    bot.send_message(CHAT_ID, f"💰 **VENTA AUTO:** {p['symbol']} cerrada en Estándar.")

            # Lógica de Compra
            if saldo > 20:
                tickers = exchange.fetch_tickers()
                top = sorted([t for t in tickers.items() if '-USDT' in t[0]], key=lambda x: x[1]['percentage'] or 0, reverse=True)[:10]
                for simbolo, datos in top:
                    if "COMPRAR" in consultar_ia(f"Comprar {simbolo}? SOLO 'COMPRAR' o 'NADA'"):
                        exchange.create_market_buy_order(simbolo, (saldo * 0.15) / datos['last'], {'positionSide': 'LONG'})
                        bot.send_message(CHAT_ID, f"🎯 **COMPRA AUTO:** {simbolo}")
                        break
            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}"); time.sleep(30)

# --- 5. COMANDOS ---

@bot.message_handler(commands=['activos'])
def cmd_activos(message):
    try:
        # Forzamos a la API a que nos dé los datos de 'standard' explícitamente
        balance = exchange.fetch_balance({'type': 'standard'})
        reporte = "🏦 **ACTIVOS (BILLETERA ESTÁNDAR):**\n"
        
        # En Estándar, los activos a veces vienen dentro de 'info' -> 'data'
        encontrado = False
        
        # Primero revisamos el formato estándar de la librería
        for asset, total in balance.get('total', {}).items():
            if float(total) > 0:
                reporte += f"• **{asset}:** {total}\n"
                encontrado = True

        # Si no encontró nada, buscamos en los datos crudos que manda BingX
        if not encontrado and 'info' in balance:
            assets = balance['info'].get('data', [])
            for a in assets:
                balance_val = float(a.get('balance', 0))
                if balance_val > 0:
                    reporte += f"• **{a.get('asset')}:** {balance_val}\n"
                    encontrado = True

        # Posiciones abiertas
        pos = exchange.fetch_positions(None, {'type': 'standard'})
        activas = [p for p in pos if float(p.get('contracts', 0)) > 0]
        if activas:
            reporte += "\n📊 **POSICIONES EN CURSO:**\n"
            for p in activas:
                reporte += f"🔹 {p['symbol']} | PNL: {p['unrealizedPnl']} VST\n"
        
        if not encontrado and not activas:
            reporte = "📭 No se detectaron activos en la cuenta Estándar. Verifica que tus VST estén en 'Futuros Estándar'."
            
        bot.send_message(CHAT_ID, reporte)
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

@bot.message_handler(commands=['test_volatil'])
def cmd_test_volatil(message):
    bot.send_message(CHAT_ID, "🧪 Probando compra en Estándar...")
    try:
        # Forzamos tipo standard en la orden
        ticker = exchange.fetch_ticker('DOGE-USDT')
        params = {'positionSide': 'LONG', 'type': 'standard'}
        exchange.create_market_buy_order('DOGE-USDT', 20 / ticker['last'], params)
        bot.send_message(CHAT_ID, "✅ Test enviado a Estándar.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

if __name__ == "__main__":
    bot.send_message(CHAT_ID, "🚀 Bot forzado a FUTUROS ESTÁNDAR.")
    threading.Thread(target=motor_trading, daemon=True).start()
    bot.polling(none_stop=True)
