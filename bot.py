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

# Configuración de BingX
exchange = ccxt.bingx({
    'apiKey': BINGX_KEY,
    'secret': BINGX_SECRET,
})
exchange.set_sandbox_mode(True) # Mantenemos modo Demo (VST)

# --- FUNCIONES IA ---
def obtener_analisis_ia(moneda, precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": f"Analiza {moneda} a {precio}. Responde SOLO: 'COMPRAR' o 'NADA'. Motivo 3 palabras."}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content']
    except: return "NADA"

# --- MOTOR AUTOMÁTICO ---
def loop_trading():
    print("🚀 Motor BingX Automático iniciado...")
    while True:
        try:
            # 1. Consultar saldo
            balance = exchange.fetch_balance()
            # En BingX Demo el saldo es VST, en real es USDT
            moneda_saldo = 'VST' if exchange.set_sandbox_mode else 'USDT'
            saldo_neto = float(balance.get('total', {}).get(moneda_saldo, 0))

            if saldo_neto > 10:
                # 2. Escanear 100 monedas
                tickers = exchange.fetch_tickers()
                candidatos = [t for t in tickers.items() if t[0].endswith('/USDT')]
                top_100 = sorted(candidatos, key=lambda x: x[1]['percentage'] or 0, reverse=True)[:100]

                for simbolo, datos in top_100:
                    precio = datos['last']
                    decision = obtener_analisis_ia(simbolo, precio)

                    if "COMPRAR" in decision.upper():
                        monto_invertir = saldo_neto * 0.20 # 20% del neto
                        cantidad = monto_invertir / precio
                        
                        # Ejecutar compra
                        order = exchange.create_market_buy_order(simbolo, cantidad)
                        
                        bot.send_message(CHAT_ID, f"🎯 **BINGX AUTO-COMPRA**\n💎 Moneda: {simbolo}\n💵 Invertido: ${monto_invertir:.2f}\n🤖 IA: {decision}")
                        break # Una operación por ciclo
            
            time.sleep(60) # Espera 1 minuto
        except Exception as e:
            print(f"Error en loop: {e}")
            time.sleep(30)

# --- COMANDOS ---
@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    try:
        balance = exchange.fetch_balance()
        moneda = 'VST' if exchange.set_sandbox_mode else 'USDT'
        saldo = balance.get('total', {}).get(moneda, 0)
        bot.send_message(CHAT_ID, f"💰 **Saldo en BingX ({moneda}):** {saldo:.2f}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

if __name__ == "__main__":
    bot.send_message(CHAT_ID, "🔌 Bot de vuelta en BingX. ¡Modo Auto Activo!")
    threading.Thread(target=loop_trading, daemon=True).start()
    bot.polling(none_stop=True)
