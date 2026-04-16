import os
import telebot
from google import genai
import ccxt

# --- CONFIGURACIÓN DE VARIABLES ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BINGX_KEY = os.getenv('BINGX_KEY')
BINGX_SECRET = os.getenv('BINGX_SECRET')

# Inicialización de clientes
client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TOKEN)

# Configuración de BingX (Modo Demo)
exchange = ccxt.bingx({
    'apiKey': BINGX_KEY,
    'secret': BINGX_SECRET,
})
exchange.set_sandbox_mode(True)

# --- FUNCIÓN CON LOOP DE MODELOS ---
def obtener_analisis_gemini(precio):
    # Probamos diferentes identificadores para evitar el error 404 de Google
    modelos_a_probar = ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.0-pro']
    
    prompt = f"BTC está a {precio} USDT. ¿Comprar o Esperar? Responde: 'ACCION: [COMPRAR/ESPERAR] - Motivo: [1 frase]'"
    
    ultima_excepcion = ""
    for nombre_modelo in modelos_a_probar:
        try:
            response = client.models.generate_content(
                model=nombre_modelo,
                contents=prompt
            )
            return response.text
        except Exception as e:
            ultima_excepcion = str(e)
            print(f"Fallo modelo {nombre_modelo}: {ultima_excepcion}")
            continue 
            
    return f"Error en todos los modelos. Último error: {ultima_excepcion}"

# --- COMANDOS TELEGRAM ---
@bot.message_handler(commands=['analizar'])
def enviar_analisis(message):
    if str(message.chat.id) != str(CHAT_ID): return
    
    bot.send_message(CHAT_ID, "🔎 Consultando mercado y probando modelos de IA...")
    
    try:
        # 1. Obtener precio de BingX
        exchange.load_markets()
        ticker = exchange.fetch_ticker('BTC-USDT')
        precio = ticker['last']
        
        # 2. Obtener respuesta de la IA (con el loop)
        analisis = obtener_analisis_gemini(precio)
        
        # 3. Enviar respuesta al usuario
        bot.send_message(CHAT_ID, f"📊 **BTC/USDT:** {precio}\n🤖 {analisis}")
        
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, "⚠️ Escribí **ok** para ejecutar la compra de prueba.")
            
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error general: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar_compra(message):
    if str(message.chat.id) != str(CHAT_ID): return
    
    bot.send_message(CHAT_ID, "⚙️ Enviando orden a BingX Demo...")
    try:
        order = exchange.create_market_buy_order('BTC-USDT', 0.0001)
        bot.send_message(CHAT_ID, f"✅ ¡Compra exitosa!\nID: {order['id']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error en la orden: {e}")

# Inicio
print("🚀 TradeAgent con Loop de IA iniciado...")
bot.polling()
