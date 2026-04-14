import OpenAI from "openai";
import TelegramBot from "node-telegram-bot-api";

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

if (!OPENAI_API_KEY || !TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
  throw new Error("Faltan variables de entorno obligatorias");
}

const openai = new OpenAI({ apiKey: OPENAI_API_KEY });
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

const state = {
  pendingTrades: new Map(),
  positions: [],
  account: {
    equity: 10000,
    availableBalance: 10000,
    realizedPnlToday: -35
  }
};

function getMarketSnapshot(symbol = "BTCUSDT", timeframe = "15m") {
  const lastPrice = 65000 + Math.floor(Math.random() * 3000 - 1500);
  return {
    symbol,
    timeframe,
    timestamp: new Date().toISOString(),
    last_price: lastPrice,
    change_24h_pct: Number((Math.random() * 8 - 4).toFixed(2)),
    volume_vs_avg: Number((0.8 + Math.random() * 1.5).toFixed(2)),
    ema_20: Number((lastPrice * (0.995 + Math.random() * 0.01)).toFixed(2)),
    ema_50: Number((lastPrice * (0.99 + Math.random() * 0.02)).toFixed(2)),
    rsi_14: Number((28 + Math.random() * 46).toFixed(1)),
    market_regime_hint: ["trend_up", "trend_down", "range"][Math.floor(Math.random() * 3)]
  };
}

function getAccountStatus() {
  return {
    equity: state.account.equity,
    available_balance: state.account.availableBalance,
    realized_pnl_today: state.account.realizedPnlToday,
    paper_mode: true,
    max_daily_loss_pct: 2.0,
    max_risk_pct: 0.5
  };
}

function getOpenPositions() {
  return state.positions;
}

function validateRisk({ side, entry_price, stop_loss, take_profit, confidence }) {
  if (state.positions.length >= 1) {
    return { approved: false, reason: "Ya hay una posición abierta" };
  }

  if (confidence < 70) {
    return { approved: false, reason: "Confidence menor a 70" };
  }

  if (side !== "LONG" && side !== "SHORT") {
    return { approved: false, reason: "Side inválido" };
  }

  if (side === "LONG" && !(stop_loss < entry_price && entry_price < take_profit)) {
    return { approved: false, reason: "Estructura LONG inválida" };
  }

  if (side === "SHORT" && !(take_profit < entry_price && entry_price < stop_loss)) {
    return { approved: false, reason: "Estructura SHORT inválida" };
  }

  const stopDistance = Math.abs(entry_price - stop_loss);
  if (stopDistance <= 0) {
    return { approved: false, reason: "Stop inválido" };
  }

  const riskAmount = state.account.equity * 0.005;
  const quantity = Number((riskAmount / stopDistance).toFixed(6));
  const rr = Number((Math.abs(take_profit - entry_price) / stopDistance).toFixed(2));

  if (rr < 1.2) {
    return { approved: false, reason: "Risk reward bajo" };
  }

  return {
    approved: true,
    quantity,
    risk_pct: 0.5,
    risk_reward: rr
  };
}

function buildTradeMessage(trade) {
  return `📈 Trade pendiente de aprobación

ID: ${trade.trade_id}
Símbolo: ${trade.symbol}
Dirección: ${trade.side}
Entry: ${trade.entry_price}
SL: ${trade.stop_loss}
TP: ${trade.take_profit}
Cantidad: ${trade.quantity}
Confidence: ${trade.confidence}
Riesgo: ${trade.risk_pct}%
R/R: ${trade.risk_reward}

Motivo: ${trade.rationale}`;
}

async function runAnalysis(chatId) {
  const market = getMarketSnapshot("BTCUSDT", "15m");
  const account = getAccountStatus();
  const positions = getOpenPositions();

  const prompt = `
Sos un trade agent conservador.
Analizá este mercado y decidí si hay trade o no.

Market snapshot:
${JSON.stringify(market, null, 2)}

Account:
${JSON.stringify(account, null, 2)}

Open positions:
${JSON.stringify(positions, null, 2)}

Respondé SOLO en JSON válido con este formato:
{
  "has_trade": true o false,
  "symbol": "BTCUSDT",
  "side": "LONG o SHORT",
  "entry_price": numero,
  "stop_loss": numero,
  "take_profit": numero,
  "confidence": numero,
  "rationale": "texto"
}

Si no hay trade:
{
  "has_trade": false,
  "rationale": "texto"
}
`;

  const response = await openai.responses.create({
    model: "gpt-5",
    input: prompt
  });

  const text = response.output_text?.trim() || "";
  let parsed;

  try {
    parsed = JSON.parse(text);
  } catch {
    await bot.sendMessage(chatId, `El modelo respondió algo no parseable:\n\n${text}`);
    return;
  }

  if (!parsed.has_trade) {
    await bot.sendMessage(chatId, `No hay trade.\n\nMotivo: ${parsed.rationale}`);
    return;
  }

  const risk = validateRisk(parsed);
  if (!risk.approved) {
    await bot.sendMessage(chatId, `Trade bloqueado por riesgo.\n\nMotivo: ${risk.reason}`);
    return;
  }

  const tradeId = `trd_${Date.now()}`;
  const trade = {
    trade_id: tradeId,
    symbol: parsed.symbol,
    side: parsed.side,
    entry_price: parsed.entry_price,
    stop_loss: parsed.stop_loss,
    take_profit: parsed.take_profit,
    confidence: parsed.confidence,
    rationale: parsed.rationale,
    quantity: risk.quantity,
    risk_pct: risk.risk_pct,
    risk_reward: risk.risk_reward,
    status: "PENDING_APPROVAL"
  };

  state.pendingTrades.set(tradeId, trade);

  await bot.sendMessage(chatId, buildTradeMessage(trade), {
    reply_markup: {
      inline_keyboard: [
        [
          { text: "✅ Aprobar", callback_data: `approve:${tradeId}` },
          { text: "❌ Rechazar", callback_data: `reject:${tradeId}` }
        ]
      ]
    }
  });
}

bot.onText(/\/start/, async (msg) => {
  await bot.sendMessage(msg.chat.id, "Bot activo. Usá /scan para buscar oportunidades.");
});

bot.onText(/\/scan/, async (msg) => {
  await bot.sendMessage(msg.chat.id, "Escaneando mercado...");
  await runAnalysis(msg.chat.id);
});

bot.on("callback_query", async (query) => {
  const [action, tradeId] = query.data.split(":");
  const trade = state.pendingTrades.get(tradeId);

  if (!trade) {
    await bot.answerCallbackQuery(query.id, { text: "Trade no encontrado" });
    return;
  }

  if (action === "approve") {
    trade.status = "APPROVED_EXECUTED";
    state.positions.push({
      position_id: `pos_${Date.now()}`,
      ...trade,
      opened_at: new Date().toISOString()
    });

    await bot.editMessageReplyMarkup(
      { inline_keyboard: [] },
      {
        chat_id: query.message.chat.id,
        message_id: query.message.message_id
      }
    );

    await bot.sendMessage(query.message.chat.id, `✅ Operación aprobada y ejecutada en paper mode.\n\nTrade ID: ${tradeId}`);
  }

  if (action === "reject") {
    trade.status = "REJECTED";

    await bot.editMessageReplyMarkup(
      { inline_keyboard: [] },
      {
        chat_id: query.message.chat.id,
        message_id: query.message.message_id
      }
    );

    await bot.sendMessage(query.message.chat.id, `❌ Operación rechazada.\n\nTrade ID: ${tradeId}`);
  }

  await bot.answerCallbackQuery(query.id);
});

bot.sendMessage(TELEGRAM_CHAT_ID, "Bot iniciado correctamente.");
console.log("Bot corriendo...");
