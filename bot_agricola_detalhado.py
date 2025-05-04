import json
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters

# Configuração do log
logging.basicConfig(level=logging.INFO)

# Carregar dados dos dois JSONs
with open("dados_plantio.json", "r", encoding="utf-8") as f:
    dados_cenoura = json.load(f)

with open("beterraba_plantios_2025.json", "r", encoding="utf-8") as f:
    dados_beterraba = json.load(f)

# Unir todos os dados
dados_plantio = dados_cenoura + dados_beterraba

# Função para formatar resposta por pivô
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
                f"🌾 *Subsafra:* {item.get('subsafra', '-') }\n"
                f"🔀 *População/Ciclo:* {item.get('populacao_ciclo', '-') }\n"
            )
            resultados.append(resultado)
    return "\n---\n".join(resultados) if resultados else "Nenhuma informação encontrada para esse pivô."

# start mostra o menu direto
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Buscar por Pivô", callback_data='buscar_pivo')],
        [InlineKeyboardButton("🌿 Listar Plantios", callback_data='listar')],
        [InlineKeyboardButton("📄 Sobre o Bot", callback_data='sobre')],
        [InlineKeyboardButton("❌ Fechar Menu", callback_data='fechar')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 *Menu de Acesso Rápido:*", reply_markup=reply_markup, parse_mode="Markdown")

# /menu também mostra os mesmos botões
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# Callback dos botões
async def botoes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'buscar_pivo':
        await query.edit_message_text("Digite o pivô que deseja consultar. Ex: Pivô 27")
    elif query.data == 'listar':
        total = len(dados_plantio)
        await query.edit_message_text(f"Temos {total} plantios cadastrados no sistema Cenoura é Beterraba.")
    elif query.data == 'sobre':
        await query.edit_message_text("Bot criado para consulta rápida de dados de plantio por pivô. Desenvolvido por Alisson Costa ✨")
    elif query.data == 'fechar':
        await query.edit_message_text("Menu fechado. Digite /menu para abrir novamente.")

# Handler de mensagens
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
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(botoes_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_plantio))

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"https://{HOSTNAME}/"
    )
