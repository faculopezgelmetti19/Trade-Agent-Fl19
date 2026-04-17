import os
import telebot
import requests
import ccxt
import time
import threading

# --- 1. CONFIGURACIÓN ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')
BX_KEY = os.getenv('BINGX_KEY')
BX_SECRET = os.getenv('BINGX_SECRET')

bot = telebot.TeleBot(TOKEN)

try:
    exchange = ccxt.bingx({
        'apiKey': BX_KEY,
        'secret': BX_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'} # Mercado de Futuros Perpetuos
    })
    exchange.set_sandbox_mode(True) # MODO DEMO
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    exchange = None

# --- 2. LÓGICA IA (GROQ) ---
def consultar_ia(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        return response.json()['choices'][0]['message']['content'].upper()
    except: return "NADA"

# --- 3. MOTOR AUTOMÁTICO (COMPRA Y VENTA) ---
def motor_trading():
    print("🤖 Motor Auto-Trader Activo...")
    while True:
        try:
            if not exchange: time.sleep(10); continue

            # --- A: MONITOREO PARA VENTA ---
            posiciones = exchange.fetch_positions()
            activas = [p for p in posiciones if float(p.get('contracts', 0)) > 0]
            
            for p in activas:
                simbolo = p['symbol']
                pnl = p['unrealizedPnl']
                prompt_v = f"Tengo un LONG en {simbolo} con PNL: {pnl}. ¿Cerrar posición? Responde SOLO: 'CERRAR' o 'NADA'. Motivo 3 palabras."
                
                if "CERRAR" in consultar_ia(prompt_v):
                    params = {'positionSide': 'LONG'}
                    exchange.create_market_sell_order(simbolo, p['contracts'], params)
                    bot.send_message(CHAT_ID, f"💰 **VENTA AUTO**\n💎 {simbolo}\n💵 PNL Final: {pnl} VST\n✅ Posición cerrada por la IA.")

            # --- B: BUSQUEDA PARA COMPRA ---
            balance = exchange.fetch_balance()
            saldo_disponible = float(balance.get('total', {}).get('VST', 0))

            if saldo_disponible > 20:
                tickers = exchange.fetch_tickers()
                # Filtramos los pares con más volumen
                top_mercado = sorted([t for t in tickers.items() if '-USDT' in t[0]], 
                                    key=lambda x: x[1]['percentage'] or 0, reverse=True)[:15]

                for simbolo, datos in top_mercado:
                    precio = datos['last']
                    prompt_c = f"Analiza {simbolo} a {precio}. ¿Comprar ahora? Responde SOLO: 'COMPRAR' o 'NADA'. Motivo 3 palabras."
                    
                    if "COMPRAR" in consultar_ia(prompt_c):
                        monto = saldo_disponible * 0.15 # Usamos el 15% para diversificar más
                        cantidad = monto / precio
                        params = {'positionSide': 'LONG'}
                        
                        exchange.create_market_buy_order(simbolo, cantidad, params)
                        bot.send_message(CHAT_ID, f"🎯 **COMPRA AUTO**\n💎 {simbolo}\n💵 Inversión: ${monto:.2f}\n🤖 IA: {prompt_c[:30]}...")
                        break # Un trade por ciclo

            time.sleep(60) # Espera 1 minuto antes de re-escanear
        except Exception as e:
            print(f"Error motor: {e}"); time.sleep(30)

# --- 4. COMANDOS ---

@bot.message_handler(commands=['activos'])
def cmd_activos(message):
    try:
        # 1. Obtenemos balance general
        balance = exchange.fetch_balance()
        reporte = "🏦 **MIS ACTIVOS (SPOT/BALANCE):**\n"
        hay_activos = False

        # 2. Listar monedas con saldo (VST, BTC, ETH, DOGE, etc.)
        for asset, totals in balance.get('total', {}).items():
            if float(totals) > 0:
                reporte += f"• **{asset}:** {totals}\n"
                hay_activos = True

        # 3. Sumar posiciones abiertas de Futuros
        posiciones = exchange.fetch_positions()
        activas = [p for p in posiciones if float(p.get('contracts', 0)) > 0]
        
        if activas:
            reporte += "\n📊 **TRADES EN CURSO:**\n"
            for p in activas:
                pnl = float(p['unrealizedPnl'])
                emoji = "🟢" if pnl >= 0 else "🔴"
                reporte += f"{emoji} {p['symbol']} | PNL: {pnl:.2f} VST\n"
        
        if not hay_activos and not activas:
            bot.send_message(CHAT_ID, "📭 Tu cuenta está vacía.")
        else:
            bot.send_message(CHAT_ID, reporte)
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error al leer activos: {e}")

@bot.message_handler(commands=['saldo'])
def cmd_saldo(message):
    balance = exchange.fetch_balance()
    vst = balance.get('total', {}).get('VST', 0)
    bot.send_message(CHAT_ID, f"💰 **Dinero Disponible:** {vst:.2f} VST")

if __name__ == "__main__":
    try:
        bot.send_message(CHAT_ID, "🚀 **SISTEMA TOTAL ACTIVO**\n- Compra/Venta IA: ON\n- Comando: /activos para ver todo.")
    except: pass
    
    threading.Thread(target=motor_trading, daemon=True).start()
    bot.polling(none_stop=True)
