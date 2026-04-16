import os
import telebot
from google import genai
import ccxt

# --- 1. CONFIGURACIÓN DE VARIABLES ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
BINGX_KEY = os.getenv('BINGX_KEY')
BINGX_SECRET = os.getenv('BINGX_SECRET')

# Inicialización del cliente de Gemini (v2)
client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TOKEN)

# Configuración de BingX (Modo Demo)
exchange = ccxt.bingx({
    'apiKey': BINGX_KEY,
    'secret': BINGX_SECRET,
})
exchange.set_sandbox_mode(True)

# --- 2. LÓGICA DE INTELIGENCIA ARTIFICIAL ---
def obtener_analisis_gemini(precio):
    # Lista priorizada de modelos estables
    modelos_a_probar = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro']
    
    prompt = f"BTC está a {precio} USDT. ¿Comprar o Esperar? Responde: 'ACCION: [COMPRAR/ESPERAR] - Motivo: [1 frase]'"
    
    ultima_excepcion = ""
    for nombre_modelo in modelos_a_probar:
        try:
            # Intento de conexión con la nueva librería
            response = client.models.generate_content(
                model=nombre_modelo,
                contents=prompt
            )
            return response.text
        except Exception as e:
            ultima_excepcion = str(e)
            print(f"Fallo modelo {nombre_modelo}: {ultima_excepcion}")
            continue 
            
    return f"IA no disponible. Motivo: {ultima_excepcion}"

# --- 3. COMANDOS DE TELEGRAM ---
@bot.message_handler(commands=['analizar'])
def enviar_analisis(message):
    # Seguridad: solo responde a tu ID
    if str(message.chat.id) != str(CHAT_ID): return
    
    bot.send_message(CHAT_ID, "🔎 Consultando precio en BingX y despertando a Gemini...")
    
    try:
        # Obtener precio real de mercado
        exchange.load_markets()
        ticker = exchange.fetch_ticker('BTC-USDT')
        precio = ticker['last']
        
        # Obtener decisión de la IA
        analisis = obtener_analisis_gemini(precio)
        
        # Enviar respuesta final
        mensaje_final = f"📊 **BTC/USDT:** {precio}\n🤖 {analisis}"
        bot.send_message(CHAT_ID, mensaje_final, parse_mode="Markdown")
        
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, "⚠️ Para comprar 0.001 BTC en Demo, escribí **ok**")
            
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error general: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar_compra(message):
    if str(message.chat.id) != str(CHAT_ID): return
    
    bot.send_message(CHAT_ID, "⚙️ Ejecutando orden en BingX Demo...")
    try:
        # Ejecuta compra a precio de mercado
        order = exchange.create_market_buy_order('BTC-USDT', 0.001)
        bot.send_message(CHAT_ID, f"✅ **¡Orden Completada!**\nID: {order['id']}\nEstado: {order['status']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error en BingX: {e}")

# Inicio del bot
if __name__ == "__main__":
    print("🚀 Bot Activo en Railway (Región: Ámsterdam)")
    bot.polling(none_stop=True)
