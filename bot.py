import os
import telebot
from google import genai
import ccxt

# 1. VARIABLES
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BINGX_KEY = os.getenv('BINGX_KEY')
BINGX_SECRET = os.getenv('BINGX_SECRET')

bot = telebot.TeleBot(TOKEN)
client_gemini = genai.Client(api_key=GEMINI_KEY)

# 2. CONFIGURACIÓN BINGX
exchange = ccxt.bingx({
    'apiKey': BINGX_KEY,
    'secret': BINGX_SECRET,
})
exchange.set_sandbox_mode(True)

def obtener_analisis_gemini(precio):
    prompt = f"BTC está a {precio} USDT. ¿Comprar o Esperar? Responde: 'ACCION: [COMPRAR/ESPERAR] - Motivo: [1 frase]'"
    response = client_gemini.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return response.text

@bot.message_handler(commands=['analizar'])
def enviar_analisis(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "🔎 Consultando mercado en BingX...")
    try:
        # Cargamos los mercados para que CCXT sepa los nombres exactos
        exchange.load_markets()
        
        # En BingX el par suele ser BTC-USDT
        simbolo = 'BTC-USDT' 
        ticker = exchange.fetch_ticker(simbolo)
        precio = ticker['last']
        
        analisis = obtener_analisis_gemini(precio)
        bot.send_message(CHAT_ID, f"📊 **BTC/USDT:** {precio}\n🤖 {analisis}")
        
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, f"⚠️ Escribí **ok** para comprar 0.0001 BTC en BingX Demo.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "⚙️ Procesando orden...")
    try:
        # Intentamos una compra pequeña
        order = exchange.create_market_buy_order('BTC-USDT', 0.0001)
        bot.send_message(CHAT_ID, f"✅ ¡Compra exitosa! ID: {order['id']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al ejecutar: {e}")

bot.polling()
