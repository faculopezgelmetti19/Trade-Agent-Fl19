import os
import telebot
import requests
import ccxt
import time
import threading

# --- 1. CARGA DE CONFIGURACIÓN ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')
BX_KEY = os.getenv('BINGX_KEY')
BX_SECRET = os.getenv('BINGX_SECRET')

bot = telebot.TeleBot(TOKEN)

# --- 2. CONEXIÓN A BINGX ---
# Usamos un bloque try para evitar que el bot muera si las keys están mal
try:
    if not BX_KEY or not BX_SECRET:
        raise ValueError("No se encontraron las credenciales BINGX_KEY o BINGX_SECRET en Railway")
    
    exchange = ccxt.bingx({
        'apiKey': BX_KEY,
        'secret': BX_SECRET,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True) # MODO DEMO (VST)
    print("✅ Conexión con BingX establecida")
except Exception as e:
    print(f"❌ Error de configuración: {e}")
    exchange = None

# --- 3. LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def obtener_analisis_ia(moneda, precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{
            "role": "user", 
            "content": f"BTC/USDT está a {precio}. Analiza tendencia 1min. Responde SOLO: 'COMPRAR' si es muy alcista o 'NADA'. Motivo 3 palabras."
        }]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content']
    except:
        return "NADA"

# --- 4. MOTOR DE TRADING AUTOMÁTICO ---
def motor_trading():
    print("🤖 Motor Automático Encendido...")
    while True:
        try:
            if exchange is None:
                time.sleep(10)
                continue

            # 1. Obtener saldo (VST en Demo)
            balance = exchange.fetch_balance()
            moneda_vst = 'VST' # Cambiar a 'USDT' si pasas a real
            saldo_total = float(balance.get('total', {}).get(moneda_vst, 0))

            # Solo operamos si tenemos más de 10 VST
            if saldo_total > 10:
                # 2. Escaneo de 100 monedas por volumen
                tickers = exchange.fetch_tickers()
                candidatos = [t for t in tickers.items() if t[0].endswith('/USDT')]
                top_100 = sorted(candidatos, key=lambda x: x[1]['percentage'] or 0, reverse=True)[:100]

                for simbolo, datos in top_100:
                    precio = datos['last']
                    analisis = obtener_analisis_ia(simbolo, precio)

                    if "COMPRAR" in analisis.upper():
                        monto_invertir = saldo_total * 0.20 # 20% del neto
                        cantidad = monto_invertir / precio
                        
                        # Ejecutar orden de mercado
                        order = exchange.create_market_buy_order(simbolo, cantidad)
                        
                        msg = (f"🎯 **COMPRA EJECUTADA**\n"
                               f"💎 Moneda: {simbolo}\n"
                               f"💵 Inversión: ${monto_invertir:.2f}\n"
                               f"🤖 IA: {analisis}")
                        bot.send_message(CHAT_ID, msg)
                        break # Un trade por minuto para evitar spam
            
            time.sleep(60) # Pausa de 1 minuto entre escaneos
        except Exception as e:
            print(f"Error en el motor: {e}")
            time.sleep(30)

# --- 5. COMANDOS TELEGRAM ---
@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    try:
        balance = exchange.fetch_balance()
        vst = balance.get('total', {}).get('VST', 0)
        bot.send_message(CHAT_ID, f"💰 **Saldo Demo (VST):** {vst:.2f}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ No pude leer el saldo: {e}")

# --- INICIO ---
if __name__ == "__main__":
    # Mensaje de arranque
    try:
        bot.send_message(CHAT_ID, "🔌 Bot reconectado a BingX. Analizando mercado cada 1 min...")
    except:
        pass

    # Hilo para el motor de trading
    threading.Thread(target=motor_trading, daemon=True).start()
    
    # Hilo para Telegram
    bot.polling(none_stop=True)
