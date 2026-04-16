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
    balance = exchange.fetch_balance()
    return float(balance['total']['USDT'])

def obtener_analisis_ia(moneda, precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": f"Analiza {moneda} a {precio} USDT. Responde SOLO: 'COMPRAR' si es muy alcista o 'NADA' si no. Motivo en 5 palabras."}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        return response.json()['choices'][0]['message']['content']
    except: return "NADA"

# --- LÓGICA DE TRADING AUTOMÁTICO ---

def loop_busqueda():
    while True:
        try:
            print("🔄 Iniciando escaneo de mercado...")
            # 1. Monitorear Stop Loss de posiciones abiertas
            posiciones = exchange.fetch_balance()['info']['data']['balances'] # Simplificado para Demo
            # (Aquí iría la lógica de monitoreo de pérdida del 60% para vender)
            
            # 2. Buscar las 100 mejores monedas por volumen
            mercados = exchange.fetch_tickers()
            # Ordenamos por cambio porcentual de las últimas 24h para buscar "profit"
            top_monedas = sorted(mercados.items(), key=lambda x: x[1]['percentage'] or 0, reverse=True)[:100]

            for simbolo, datos in top_monedas:
                if not simbolo.endswith('/USDT'): continue
                
                precio = datos['last']
                analisis = obtener_analisis_ia(simbolo, precio)

                if "COMPRAR" in analisis.upper():
                    saldo_actual = obtener_saldo_usdt()
                    monto_usdt = saldo_actual * 0.20 # 20% del neto
                    
                    if monto_usdt > 5: # Mínimo para operar
                        # Convertimos USDT a cantidad de la moneda
                        cantidad = monto_usdt / precio
                        order = exchange.create_market_buy_order(simbolo, cantidad)
                        bot.send_message(CHAT_ID, f"🚀 **COMPRA AUTO**\nMoneda: {simbolo}\nPrecio: {precio}\nInvertido: ${monto_usdt:.2f}\nIA: {analisis}")
            
            print("✅ Escaneo finalizado. Esperando 1 minuto...")
            time.sleep(60)
        except Exception as e:
            print(f"❌ Error en loop: {e}")
            time.sleep(30)

# --- COMANDOS TELEGRAM ---

@bot.message_handler(commands=['saldo'])
def enviar_saldo(message):
    try:
        saldo = obtener_saldo_usdt()
        bot.send_message(CHAT_ID, f"💰 **Saldo Neto Actual:** ${saldo:.2f} USDT")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al obtener saldo: {e}")

# Iniciar el hilo de búsqueda automática para que no bloquee los comandos de Telegram
threading.Thread(target=loop_busqueda, daemon=True).start()

if __name__ == "__main__":
    print("🤖 Bot Pro-Trader Iniciado...")
    bot.polling(none_stop=True)
