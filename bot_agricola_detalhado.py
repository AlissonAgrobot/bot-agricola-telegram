import json
import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Configuração do log
logging.basicConfig(level=logging.INFO)

# Carregar dados do JSON
with open("dados_plantio.json", "r", encoding="utf-8") as f:
    dados_plantio = json.load(f)

# Função para formatar múltiplos resultados por pivô
def formatar_resposta_por_pivo(pivo):
    resultados = []
    for item in dados_plantio:
        if pivo.lower() in item["pivo"].lower():
            resultado = (
                f"\U0001F4CD *Fazenda:* {item['fazenda']}\n"
                f"🗓️ *Data do plantio:* {item['data_plantio']}\n"
                f"🌿 *Cultura:* {item['cultura']}\n"
                f"🚰 *Pivô:* {item['pivo']}\n"
                f"📊 *Área:* {item['area']:.2f} ha\n"
                f"🌱 *Plantio:* {item['plantio']}\n"
                f"🌾 *Subsafra:* {item['subsafra']}\n"
                f"🔁 *População/Ciclo:* {item['populacao_ciclo']}\n"
            )
            resultados.append(resultado)
    if resultados:
        return "\n".join(resultados)
    else:
        return "Nenhuma informação encontrada para esse pivô."

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot agrícola ativo! Digite algo como 'Pivô 27' para consultar o plantio."
    )

# Handler de mensagem comum
async def responder_plantio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if "pivô" in texto.lower():
        resposta = formatar_resposta_por_pivo(texto)
        await update.message.reply_markdown(resposta)
    else:
        await update.message.reply_text("Por favor, digite algo como 'Pivô 27' para consultar.")

# Main
if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_plantio))

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"https://{HOSTNAME}/"
    )

