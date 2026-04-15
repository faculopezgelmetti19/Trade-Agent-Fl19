import os
import telebot
from google import genai
import ccxt

# 1. CARGA DE VARIABLES
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BYBIT_KEY = os.getenv('BYBIT_KEY')
BYBIT_SECRET = os.getenv('BYBIT_SECRET')

bot = telebot.TeleBot(TOKEN)
client_gemini = genai.Client(api_key=GEMINI_KEY)

# 2. CONFIGURACIÓN DE BYBIT (No bloquea Railway)
exchange = ccxt.bybit({
    'apiKey': BYBIT_KEY,
    'secret': BYBIT_SECRET,
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(True) # Activa modo Testnet de Bybit

# 3. LÓGICA
def obtener_analisis_gemini(precio):
    prompt = f"BTC está a {precio} USDT. ¿Comprar o Esperar? Responde: 'ACCION: [COMPRAR/ESPERAR] - Motivo: [1 frase]'"
    response = client_gemini.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return response.text

@bot.message_handler(commands=['analizar'])
def enviar_analisis(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "🔎 Consultando mercado en Bybit...")
    try:
        ticker = exchange.fetch_ticker('BTC/USDT')
        precio = ticker['last']
        analisis = obtener_analisis_gemini(precio)
        bot.send_message(CHAT_ID, f"📊 **BTC/USDT:** {precio}\n🤖 {analisis}")
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, "⚠️ Escribí **ok** para comprar en Bybit Testnet.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar(message):
    if str(message.chat.id) != str(CHAT_ID): return
    try:
        # Compra mínima en Bybit
        order = exchange.create_market_buy_order('BTC/USDT', 0.001)
        bot.send_message(CHAT_ID, f"✅ Compra exitosa! ID: {order['id']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

bot.polling()
