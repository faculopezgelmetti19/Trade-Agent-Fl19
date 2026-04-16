import os
import telebot
import requests
import ccxt
import time
import threading

# --- 1. CONFIGURACIÓN DE VARIABLES ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')
BX_KEY = os.getenv('BINGX_KEY')
BX_SECRET = os.getenv('BINGX_SECRET')

bot = telebot.TeleBot(TOKEN)

# --- 2. CONEXIÓN A BINGX (FUTUROS PERPETUOS) ---
try:
    if not BX_KEY or not BX_SECRET:
        print("❌ Error: Faltan credenciales BINGX_KEY o BINGX_SECRET en Railway.")
        exchange = None
    else:
        exchange = ccxt.bingx({
            'apiKey': BX_KEY,
            'secret': BX_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # Configurado para Futuros Perpetuos
            }
        })
        exchange.set_sandbox_mode(True)  # MODO DEMO (VST)
        print("✅ Conectado a BingX Futuros Perpetuos (Demo)")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    exchange = None

# --- 3. LÓGICA DE INTELIGENCIA ARTIFICIAL (GROQ) ---
def obtener_analisis_ia(moneda, precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{
            "role": "user", 
            "content": f"El par {moneda} está a {precio}. Analiza tendencia rápida. Responde SOLO: 'COMPRAR' si es muy alcista o 'NADA'. Motivo 3 palabras."
        }]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content']
    except:
        return "NADA"

# --- 4. MOTOR DE TRADING AUTOMÁTICO ---
def motor_trading():
    print("🤖 Motor Automático en Futuros Encendido...")
    while True:
        try:
            if not exchange:
                time.sleep(10)
                continue

            # 1. Obtener saldo de la cuenta de Futuros (VST)
            balance = exchange.fetch_balance()
            saldo_total = float(balance.get('total', {}).get('VST', balance.get('VST', {}).get('total', 0)))

            # Solo operamos si el saldo es mayor a 10 VST
            if saldo_total > 10:
                # 2. Escaneo de las 100 con más volumen
                tickers = exchange.fetch_tickers()
                candidatos = [t for t in tickers.items() if 'USDT' in t[0]]
                top_100 = sorted(candidatos, key=lambda x: x[1]['percentage'] or 0, reverse=True)[:100]

                for simbolo, datos in top_100:
                    precio = datos['last']
                    decision = obtener_analisis_ia(simbolo, precio)

                    if "COMPRAR" in decision.upper():
                        monto_a_invertir = saldo_total * 0.20 # 20% del neto
                        cantidad = monto_a_invertir / precio
                        
                        # Ejecutar Long en Futuros
                        order = exchange.create_market_buy_order(simbolo, cantidad)
                        
                        bot.send_message(CHAT_ID, f"🎯 **COMPRA AUTO (LONG)**\n💎 Moneda: {simbolo}\n💵 Inversión: ${monto_a_invertir:.2f}\n🤖 IA: {decision}")
                        break # Un trade por ciclo para control de riesgo
            
            time.sleep(60) # Pausa de 1 minuto
        except Exception as e:
            print(f"Error en motor: {e}")
            time.sleep(30)

# --- 5. COMANDOS TELEGRAM ---

@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    try:
        balance = exchange.fetch_balance()
        vst = balance.get('total', {}).get('VST', balance.get('VST', {}).get('total', 0))
        bot.send_message(CHAT_ID, f"💰 **Saldo Futuros Perpetuo (VST):** {vst:.2f}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al leer saldo: {e}")

@bot.message_handler(commands=['test'])
def cmd_test(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "🧪 Ejecutando compra de prueba (0.001 BTC)...")
    try:
        # Intenta abrir un Long mínimo en BTC
        order = exchange.create_market_buy_order('BTC/USDT', 0.001)
        bot.send_message(CHAT_ID, f"✅ **¡PRUEBA EXITOSA!**\nID: {order['id']}\nPrecio: {order['price']}\nRevisá tus posiciones en BingX.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Falló la prueba: {e}")

# --- 6. INICIO DEL SISTEMA ---
if __name__ == "__main__":
    try:
        bot.send_message(CHAT_ID, "🔌 Bot Online en BingX Futuros.\n- Escaneo: Activo (100 monedas)\n- Riesgo: 20% del neto\n- Comandos: /saldo, /test")
    except:
        pass

    # Iniciar motor en segundo plano
    threading.Thread(target=motor_trading, daemon=True).start()
    
    # Iniciar escucha de Telegram
    bot.polling(none_stop=True)
    
