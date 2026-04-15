import os
import telebot
from google import genai
import ccxt
# 1. CARGA DE VARIABLES DESDE RAILWAY
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BINANCE_KEY = os.getenv('BINANCE_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

# 2. CONFIGURACIÓN DE SERVICIOS
bot = telebot.TeleBot(TOKEN)
client_gemini = genai.Client(api_key=GEMINI_KEY)

# Configuramos Binance con CCXT (Modo Testnet/Sandbox)
exchange = ccxt.binance({
    'apiKey': BINANCE_KEY,
    'secret': BINANCE_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})
exchange.set_sandbox_mode(True)  # IMPORTANTE: Esto le dice que use la red de prueba

# 3. FUNCIONES DE ANÁLISIS
def obtener_analisis_gemini(precio):
    prompt = (f"El precio actual de Bitcoin es {precio} USDT. "
              f"Analiza si es buen momento para comprar basándote solo en este precio. "
              f"Responde empezando con la palabra COMPRAR o ESPERAR, "
              f"y luego una sola frase corta de por qué.")
    
    response = client_gemini.models.generate_content(
        model="gemini-1.5-flash", 
        contents=prompt
    )
    return response.text

# 4. COMANDOS DE TELEGRAM
@bot.message_handler(commands=['start', 'analizar'])
def enviar_analisis(message):
    # Seguridad: solo responde a tu ID
    if str(message.chat.id) != str(CHAT_ID):
        return

    bot.send_message(CHAT_ID, "🔎 Consultando mercado y pidiendo opinión a Gemini...")
    
    try:
        # Obtenemos el precio actual
        ticker = exchange.fetch_ticker('BTC/USDT')
        precio = ticker['last']
        
        # Le pedimos el análisis a Gemini
        analisis = obtener_analisis_gemini(precio)
        
        mensaje_respuesta = f"📊 **BTC/USDT:** {precio}\n\n🤖 **Gemini:** {analisis}"
        bot.send_message(CHAT_ID, mensaje_respuesta)
        
        # Si Gemini sugiere comprar, habilitamos el OK
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, "⚠️ Para ejecutar la compra de prueba (0.001 BTC), responde: **ok**")
            
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error de conexión: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar_compra(message):
    if str(message.chat.id) != str(CHAT_ID):
        return

    bot.send_message(CHAT_ID, "⚙️ Enviando orden de compra a Binance Testnet...")
    
    try:
        # Ejecuta una compra a mercado de 0.001 BTC
        order = exchange.create_market_buy_order('BTC/USDT', 0.001)
        bot.send_message(CHAT_ID, f"✅ **¡COMPRA REALIZADA!**\nID de Orden: {order['id']}\nEstado: {order['status']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al ejecutar orden: {e}")

# 5. INICIO DEL BOT
print("🚀 TradeAgent Online...")
bot.polling()
