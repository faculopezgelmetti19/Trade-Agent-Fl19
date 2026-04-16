import os
import telebot
import requests
import ccxt

# --- 1. CONFIGURACIÓN ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')
BINGX_KEY = os.getenv('BINGX_KEY')
BINGX_SECRET = os.getenv('BINGX_SECRET')

bot = telebot.TeleBot(TOKEN)

# Configuración de BingX (Modo Demo)
exchange = ccxt.bingx({
    'apiKey': BINGX_KEY,
    'secret': BINGX_SECRET,
})
exchange.set_sandbox_mode(True)

# --- 2. LÓGICA DE IA (USANDO GROQ) ---
def obtener_analisis_ia(precio):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user", 
                "content": f"BTC está a {precio} USDT. Responde corto y directo: 'ACCION: [COMPRAR/ESPERAR] - Motivo: [1 frase en español]'"
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        return f"Error en IA (Groq): {e}"

# --- 3. COMANDOS TELEGRAM ---
@bot.message_handler(commands=['analizar'])
def enviar_analisis(message):
    if str(message.chat.id) != str(CHAT_ID): return
    
    bot.send_message(CHAT_ID, "🔎 Consultando mercado y analizando con Groq Cloud...")
    
    try:
        # Obtener precio de BingX
        exchange.load_markets()
        ticker = exchange.fetch_ticker('BTC-USDT')
        precio = ticker['last']
        
        # Obtener decisión de la IA
        analisis = obtener_analisis_ia(precio)
        
        # Enviar respuesta
        bot.send_message(CHAT_ID, f"📊 **BTC/USDT:** {precio}\n🤖 {analisis}")
        
        if "COMPRAR" in analisis.upper():
            bot.send_message(CHAT_ID, "⚠️ Escribí **ok** para comprar 0.001 BTC en Demo.")
            
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "ok")
def ejecutar(message):
    if str(message.chat.id) != str(CHAT_ID): return
    
    bot.send_message(CHAT_ID, "⚙️ Ejecutando orden en BingX Demo...")
    try:
        order = exchange.create_market_buy_order('BTC-USDT', 0.001)
        bot.send_message(CHAT_ID, f"✅ ¡Compra exitosa!\nID: {order['id']}")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error en BingX: {e}")

# Inicio
if __name__ == "__main__":
    print("🚀 Bot iniciado con Groq y BingX")
    bot.polling(none_stop=True)
