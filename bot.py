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

# --- 2. CONEXIÓN BINGX (SWAP) ---
try:
    exchange = ccxt.bingx({
        'apiKey': BX_KEY,
        'secret': BX_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
    exchange.set_sandbox_mode(True)
    print("✅ Conectado a BingX Futuros (Hedge Mode compatible)")
except Exception as e:
    print(f"❌ Error: {e}")
    exchange = None

# --- 3. LÓGICA IA ---
def obtener_analisis_ia(moneda, precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": f"El par {moneda} está a {precio}. Responde SOLO: 'COMPRAR' o 'NADA'. Motivo 3 palabras."}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content']
    except: return "NADA"

# --- 4. MOTOR AUTOMÁTICO ---
def motor_trading():
    print("🤖 Motor Automático Iniciado...")
    while True:
        try:
            if not exchange:
                time.sleep(10); continue

            balance = exchange.fetch_balance()
            saldo = float(balance.get('total', {}).get('VST', balance.get('VST', {}).get('total', 0)))

            if saldo > 10:
                tickers = exchange.fetch_tickers()
                candidatos = [t for t in tickers.items() if '-USDT' in t[0]]
                top_100 = sorted(candidatos, key=lambda x: x[1]['percentage'] or 0, reverse=True)[:100]

                for simbolo, datos in top_100:
                    precio = datos['last']
                    decision = obtener_analisis_ia(simbolo, precio)

                    if "COMPRAR" in decision.upper():
                        monto = saldo * 0.20
                        cantidad = monto / precio
                        
                        # AGREGAMOS POSITION SIDE PARA MODO COBERTURA
                        params = {'positionSide': 'LONG'}
                        exchange.create_market_buy_order(simbolo, cantidad, params)
                        
                        bot.send_message(CHAT_ID, f"🎯 **COMPRA AUTO (LONG)**\n💎 {simbolo}\n💵 ${monto:.2f}\n🤖 IA: {decision}")
                        break 
            time.sleep(60)
        except Exception as e:
            print(f"Error motor: {e}"); time.sleep(30)

# --- 5. COMANDOS ---
@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    try:
        balance = exchange.fetch_balance()
        vst = balance.get('total', {}).get('VST', balance.get('VST', {}).get('total', 0))
        bot.send_message(CHAT_ID, f"💰 **Saldo VST:** {vst:.2f}")
    except Exception as e: bot.send_message(CHAT_ID, f"❌ Error: {e}")

@bot.message_handler(commands=['test'])
def cmd_test(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "🧪 Probando compra LONG con PositionSide...")
    try:
        # PARÁMETRO CLAVE: positionSide LONG
        params = {'positionSide': 'LONG'}
        order = exchange.create_market_buy_order('BTC-USDT', 0.001, params)
        bot.send_message(CHAT_ID, f"✅ **¡PRUEBA EXITOSA!**\nID: {order['id']}\nPrecio: {order['price']}\nPosición abierta en LONG.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=motor_trading, daemon=True).start()
    bot.polling(none_stop=True)
