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

# --- 2. CONEXIÓN A BINGX (MODO FUTUROS PERPETUOS) ---
try:
    exchange = ccxt.bingx({
        'apiKey': BX_KEY,
        'secret': BX_SECRET,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',  # Crucial: apunta a Futuros Perpetuos
        }
    })
    exchange.set_sandbox_mode(True)  # Mantenemos modo Demo (VST)
    print("✅ Conectado a BingX Futuros Perpetuos")
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
            "content": f"BTC/USDT está a {precio}. Analiza tendencia rápida. Responde SOLO: 'COMPRAR' si es muy alcista o 'NADA'. Motivo 3 palabras."
        }]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content']
    except:
        return "NADA"

# --- 4. MOTOR AUTOMÁTICO (LOOP DE TRADING) ---
def motor_trading():
    print("🤖 Motor Automático en Futuros Encendido...")
    while True:
        try:
            if not exchange:
                time.sleep(10)
                continue

            # 1. Obtener saldo de la cuenta de Futuros
            balance = exchange.fetch_balance()
            # En BingX Perpetuo Demo, el saldo total suele venir en 'VST'
            saldo_neto = float(balance.get('VST', {}).get('total', 0))
            
            # Si el saldo neto sigue marcando 0, intentamos rastrear en el total general
            if saldo_neto == 0:
                saldo_neto = float(balance.get('total', {}).get('VST', 0))

            if saldo_neto > 10:
                # 2. Escaneo de las 100 con más volumen
                tickers = exchange.fetch_tickers()
                # Filtramos pares que terminen en USDT o que sean swaps
                candidatos = [t for t in tickers.items() if 'USDT' in t[0]]
                top_100 = sorted(candidatos, key=lambda x: x[1]['percentage'] or 0, reverse=True)[:100]

                for simbolo, datos in top_100:
                    precio = datos['last']
                    decision = obtener_analisis_ia(simbolo, precio)

                    if "COMPRAR" in decision.upper():
                        monto_a_invertir = saldo_neto * 0.20 # 20% del neto
                        
                        # Calculamos cantidad (simplificado para el ejemplo)
                        cantidad = monto_a_invertir / precio
                        
                        # Ejecutar orden de mercado en Futuros (Abre un LONG)
                        order = exchange.create_market_buy_order(simbolo, cantidad)
                        
                        bot.send_message(CHAT_ID, f"🎯 **COMPRA FUTUROS (LONG)**\n💎 Moneda: {simbolo}\n💵 Inversión: ${monto_a_invertir:.2f}\n🤖 IA: {decision}")
                        break # Un trade por ciclo para no saturar
            
            time.sleep(60) # Revisar cada 1 minuto
        except Exception as e:
            print(f"Error en motor: {e}")
            time.sleep(30)

# --- 5. COMANDOS TELEGRAM ---
@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    try:
        balance = exchange.fetch_balance()
        # Intentamos obtener VST de varias formas por si la API cambia el formato
        vst = balance.get('VST', {}).get('total', balance.get('total', {}).get('VST', 0))
        
        bot.send_message(CHAT_ID, f"💰 **Saldo Futuros Perpetuo (VST):** {vst:.2f}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al leer saldo de Futuros: {e}")

# --- INICIO ---
if __name__ == "__main__":
    try:
        bot.send_message(CHAT_ID, "🔌 Bot Activo en BingX Futuros Perpetuos.\nModo automático: ENCENDIDO (20% por trade).")
    except:
        pass

    threading.Thread(target=motor_trading, daemon=True).start()
    bot.polling(none_stop=True)
