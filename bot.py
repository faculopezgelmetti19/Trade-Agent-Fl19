import os
import telebot
import google.generativeai as genai  # Cambiamos la forma de importar Gemini
import ccxt

# 1. VARIABLES
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BINGX_KEY = os.getenv('BINGX_KEY')
BINGX_SECRET = os.getenv('BINGX_SECRET')

# Configuración de Gemini (Versión estable)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TOKEN)

# 2. CONFIGURACIÓN BINGX
exchange = ccxt.bingx({
    'apiKey': BINGX_KEY,
    'secret': BINGX_SECRET,
})
exchange.set_sandbox_mode(True)

def obtener_analisis_gemini(precio):
    prompt = f"BTC está a {precio} USDT. ¿Comprar o Esperar? Responde: 'ACCION: [COMPRAR/ESPERAR] - Motivo: [1 frase]'"
    # Cambiamos la forma de generar contenido
    response = model.generate_content(prompt)
    return response.text

@bot.message_handler(commands=['analizar'])
def enviar_analisis(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "🔎 Consultando mercado en BingX...")
    try:
        exchange.load_markets()
        simbolo = 'BTC-USDT' 
        ticker = exchange.fetch_ticker(simbolo)
        precio = ticker['last']
        
        analisis = obtener_analisis_gemini(precio)
        bot.send_message(CHAT_ID, f"📊 **BTC/USDT:** {precio}\n🤖 {analisis}")
        
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, f"⚠️ Escribí **ok** para comprar.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "⚙️ Procesando orden en BingX...")
    try:
        order = exchange.create_market_buy_order('BTC-USDT', 0.0001)
        bot.send_message(CHAT_ID, f"✅ ¡Compra exitosa! ID: {order['id']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al ejecutar: {e}")

bot.polling()
