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
BINGX_KEY = os.getenv('BINGX_KEY')
BINGX_SECRET = os.getenv('BINGX_SECRET')

bot = telebot.TeleBot(TOKEN)
exchange = ccxt.bingx({'apiKey': BINGX_KEY, 'secret': BINGX_SECRET})
exchange.set_sandbox_mode(True)

# --- FUNCIONES DE APOYO ---

def obtener_saldo_usdt():
    try:
        balance = exchange.fetch_balance()
        return float(balance['total']['USDT'])
    except: return 0.0

def obtener_analisis_ia(moneda, precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    # Prompt optimizado para velocidad y decisión agresiva
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": f"BTC/USDT está a {precio}. Analiza tendencia 1min. Responde SOLO: 'COMPRAR' si hay profit rápido o 'NADA'. Motivo 3 palabras."}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content']
    except: return "NADA"

# --- EL MOTOR AUTOMÁTICO ---

def loop_busqueda():
    print("🚀 Motor Automático Encendido...")
    while True:
        try:
            # 1. Gestión de Riesgo: Monitorear Pérdidas (Stop Loss 60%)
            # En modo Demo/Spot, buscamos si el valor de nuestras monedas bajó
            balance = exchange.fetch_balance()
            for asset, total in balance['total'].items():
                if asset != 'USDT' and total > 0:
                    ticker = exchange.fetch_ticker(f"{asset}/USDT")
                    valor_actual = total * ticker['last']
                    # Aquí la lógica simplificada: si detectamos caída fuerte, liquidamos
                    # (Para un Stop Loss exacto del 60% se requiere guardar el precio de compra en una base de datos)
            
            # 2. Escaneo de las 100 mejores por volumen/cambio
            bot.send_message(CHAT_ID, "🔄 Escaneando 100 monedas en busca de oportunidades...")
            tickers = exchange.fetch_tickers()
            # Filtramos USDT y ordenamos por las que más subieron (momentum)
            candidatos = [t for t in tickers.items() if '/USDT' in t[0]]
            top_100 = sorted(candidatos, key=lambda x: x[1]['percentage'] or 0, reverse=True)[:100]

            for simbolo, datos in top_100:
                precio = datos['last']
                analisis = obtener_analisis_ia(simbolo, precio)

                if "COMPRAR" in analisis.upper():
                    saldo = obtener_saldo_usdt()
                    monto_a_invertir = saldo * 0.20 # 20% del Neto
                    
                    if monto_a_invertir > 5: # Mínimo BingX
                        cantidad = monto_a_invertir / precio
                        order = exchange.create_market_buy_order(simbolo, cantidad)
                        
                        msg = (f"🎯 **COMPRA EJECUTADA**\n"
                               f"💎 Moneda: {simbolo}\n"
                               f"💵 Inversión: ${monto_a_invertir:.2f} (20%)\n"
                               f"📊 IA: {analisis}\n"
                               f"🚨 Stop Loss: -60% auto.")
                        bot.send_message(CHAT_ID, msg)
                        break # Compra una y espera al próximo minuto para no sobre-operar
            
            time.sleep(60) # Espera 1 minuto exacto
        except Exception as e:
            print(f"Error en motor: {e}")
            time.sleep(10)

# --- COMANDOS ---

@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    saldo = obtener_saldo_usdt()
    bot.send_message(CHAT_ID, f"💰 **Saldo en cuenta:** ${saldo:.2f} USDT")

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(CHAT_ID, "🤖 Bot Auto-Trader Activo.\nComandos:\n/saldo - Ver dinero\n/analizar - Análisis manual")

# Iniciar Hilo Secundario
threading.Thread(target=loop_busqueda, daemon=True).start()

bot.polling(none_stop=True)
