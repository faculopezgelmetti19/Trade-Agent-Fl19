import os
import telebot
import requests
import ccxt

# 1. VARIABLES
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BINGX_KEY = os.getenv('BINGX_KEY')
BINGX_SECRET = os.getenv('BINGX_SECRET')

bot = telebot.TeleBot(TOKEN)

# Configuración de BingX
exchange = ccxt.bingx({
    'apiKey': BINGX_KEY,
    'secret': BINGX_SECRET,
})
exchange.set_sandbox_mode(True)

def obtener_analisis_gemini(precio):
    # CONEXIÓN MANUAL POR HTTP (Sin librerías que fallen)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": f"BTC está a {precio} USDT. Responde corto: 'ACCION: [COMPRAR/ESPERAR] - Motivo: [1 frase]'"}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        # Extraemos el texto de la respuesta de Google
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Error en conexión manual: {e} - Detalle: {response.text if 'response' in locals() else 'No hay respuesta'}"

@bot.message_handler(commands=['analizar'])
def enviar_analisis(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "🔎 Consultando mercado y saltando bloqueos de API...")
    try:
        exchange.load_markets()
        ticker = exchange.fetch_ticker('BTC-USDT')
        precio = ticker['last']
        
        analisis = obtener_analisis_gemini(precio)
        bot.send_message(CHAT_ID, f"📊 **BTC/USDT:** {precio}\n🤖 {analisis}")
        
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, "⚠️ Escribí **ok** para comprar.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar(message):
    if str(message.chat.id) != str(CHAT_ID): return
    try:
        order = exchange.create_market_buy_order('BTC-USDT', 0.0001)
        bot.send_message(CHAT_ID, f"✅ Compra exitosa! ID: {order['id']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

bot.polling()
