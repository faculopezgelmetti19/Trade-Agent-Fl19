import os
import telebot
import google.generativeai as genai
from binance.client import Client

# 1. CARGA DE VARIABLES DESDE RAILWAY
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

# 2. CONFIGURACIÓN DE LOS SERVICIOS
bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Conectamos a la Testnet de Binance
client = Client(BINANCE_KEY, BINANCE_SECRET, testnet=True)

# 3. FUNCIONES DE APOYO
def obtener_analisis_gemini(precio):
    prompt = (f"El precio actual de Bitcoin es {precio} USDT. "
              f"Analiza si es buen momento para comprar. "
              f"Responde corto: primero la palabra COMPRAR o ESPERAR, "
              f"y luego una sola frase de por qué.")
    response = gemini_model.generate_content(prompt)
    return response.text

# 4. COMANDOS DE TELEGRAM
@bot.message_handler(commands=['start', 'analizar'])
def enviar_analisis(message):
    # Verificación de seguridad: solo te responde a vos
    if str(message.chat.id) != str(CHAT_ID):
        return

    bot.send_message(CHAT_ID, "🔎 Consultando al mercado y a Gemini...")
    
    try:
        avg_price = client.get_avg_price(symbol='BTCUSDT')['price']
        analisis = obtener_analisis_gemini(avg_price)
        
        bot.send_message(CHAT_ID, f"📊 **BTC/USDT:** {avg_price}\n\n🤖 **Gemini dice:** {analisis}")
        
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, "⚠️ Para ejecutar la compra de 0.001 BTC, responde: **ok**")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar_compra(message):
    if str(message.chat.id) != str(CHAT_ID):
        return

    bot.send_message(CHAT_ID, "⚙️ Procesando orden en Binance Testnet...")
    try:
        # Ejecuta una compra a precio de mercado
        order = client.create_order(
            symbol='BTCUSDT',
            side='BUY',
            type='MARKET',
            quantity=0.001  # Cantidad de prueba
        )
        bot.send_message(CHAT_ID, f"✅ **¡COMPRA REALIZADA!**\nID de Orden: {order['orderId']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al comprar: {e}")

# 5. ENCENDER EL BOT
print("TradeAgent encendido...")
bot.polling()
