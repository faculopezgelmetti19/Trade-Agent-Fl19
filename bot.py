import os
import telebot
from google import genai
from binance.client import Client

# 1. CARGA DE VARIABLES
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

# 2. CONFIGURACIÓN
bot = telebot.TeleBot(TOKEN)
# Nueva forma de configurar Gemini (2026)
client_gemini = genai.Client(api_key=GEMINI_KEY)

# Intentamos conectar a Binance forzando el servidor global
try:
    client_binance = Client(BINANCE_KEY, BINANCE_SECRET, testnet=True)
    # Cambiamos la URL de la API por si Railway está en zona restringida
    client_binance.API_URL = 'https://testnet.binance.vision/api' 
except Exception as e:
    print(f"Error inicial de Binance: {e}")

# 3. LÓGICA
def obtener_analisis_gemini(precio):
    prompt = f"El precio de BTC es {precio}. ¿Comprar o Esperar? Responde: 'ACCION: [COMPRAR/ESPERAR] - Motivo: [1 frase]'"
    response = client_gemini.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return response.text

@bot.message_handler(commands=['analizar'])
def enviar_analisis(message):
    if str(message.chat.id) != str(CHAT_ID): return
    bot.send_message(CHAT_ID, "🔎 Analizando...")
    try:
        precio = client_binance.get_symbol_ticker(symbol="BTCUSDT")['price']
        analisis = obtener_analisis_gemini(precio)
        bot.send_message(CHAT_ID, f"📊 Precio: {precio}\n🤖 {analisis}")
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, "⚠️ Responde 'ok' para ejecutar.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error de conexión con el Broker: {e}\n(Es probable que la ubicación del servidor de Railway esté bloqueada por Binance)")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar(message):
    if str(message.chat.id) != str(CHAT_ID): return
    try:
        order = client_binance.create_order(symbol='BTCUSDT', side='BUY', type='MARKET', quantity=0.001)
        bot.send_message(CHAT_ID, f"✅ Comprado! ID: {order['orderId']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error en la orden: {e}")

print("Bot activo...")
bot.polling()
