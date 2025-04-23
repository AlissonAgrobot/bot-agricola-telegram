
import json
import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Configuração do log
logging.basicConfig(level=logging.INFO)

# Carrega os dados do JSON
with open("dados_plantio.json", "r", encoding="utf-8") as f:
    dados_plantio = json.load(f)

# Formatar a resposta baseada no pivô
def buscar_por_pivo(pivo_consultado):
    resposta = ""
    for item in dados_plantio:
        if pivo_consultado.lower() in item["pivo"].lower():
            resposta += (
                f"📍 *Fazenda:* {item['fazenda']}\n"
                f"📅 *Data do plantio:* {item['data_plantio']}\n"
                f"🌱 *Cultura:* {item['cultura']}\n"
                f"💧 *Pivô:* {item['pivo']}\n"
                f"📊 *Área:* {item['area']:.2f} ha\n\n"
            )
    if not resposta:
        resposta = "❌ Nenhum plantio encontrado para esse pivô."
    return resposta

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot agrícola ativo! Digite algo como 'Pivô 90' para consultar o plantio.")

# Tratamento de mensagens comuns (ex: "Pivô 90")
async def mensagem_pivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if "pivô" in texto.lower():
        resposta = buscar_por_pivo(texto)
        await update.message.reply_markdown(resposta)

# Execução principal
if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mensagem_pivo))

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"https://{HOSTNAME}/"
    )
