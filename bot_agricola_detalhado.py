import json
import logging
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Tokens
TOKEN = "8006515043:AAFapaNdYxv1sfgH126gxuBx3vAASAz-UF4"
OPENWEATHER_API_KEY = "a633bcced8f4d4eb76047d2a4981e252"
SENTINEL_INSTANCE_ID = "1b9f5321-056a-4a9e-beaa-954934167ba0"

# Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar dados dos plantios
with open("dados_plantio.json", encoding="utf-8") as f:
    dados_plantio = json.load(f)

# Mensagem de boas-vindas
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🌾 Olá! Este é o Bot Agrícola Sekita.\n"
        "Consulte informações dos pivôs: cultura, data de plantio, população, clima e imagem de satélite.\n"
        "Digite (ex: Pivô 01) para começar. 🌱"
    )
    await update.message.reply_text(welcome)

# Buscar informações do pivô
def buscar_info_pivo(pivo_nome):
    return [p for p in dados_plantio if pivo_nome.lower() in p["pivo"].lower()]

# Obter clima atual + previsão de chuva
def obter_clima(lat, lon):
    url = (
        f"https://api.openweathermap.org/data/2.5/forecast?"
        f"lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    )
    r = requests.get(url).json()
    if "list" in r and len(r["list"]) > 0:
        atual = r["list"][0]
        descricao = atual["weather"][0]["description"].capitalize()
        temp = atual["main"]["temp"]
        umidade = atual["main"]["humidity"]
        vento = atual["wind"]["speed"]
        chuva = atual.get("pop", 0) * 100

        if chuva > 0:
            chuva_texto = f"🌧️ Previsão de chuva: {chuva:.0f}%"
        else:
            chuva_texto = "🌧️ Previsão de chuva: 0%"

        return (
            f"🌤️ *Clima agora:* {descricao}\n"
            f"🌡️ Temperatura: {temp}°C\n"
            f"💧 Umidade: {umidade}%\n"
            f"🍃 Vento: {vento:.2f} m/s\n"
            f"{chuva_texto}"
        )
    return "❌ Clima indisponível."

# Link satélite com data automática dos últimos 7 dias
def gerar_link_satelite(lat, lon):
    hoje = datetime.utcnow()
    inicio = hoje - timedelta(days=7)
    data_inicio = inicio.strftime("%Y-%m-%d")
    data_fim = hoje.strftime("%Y-%m-%d")

    return (
        f"https://apps.sentinel-hub.com/eo-browser/?"
        f"lat={lat}&lng={lon}&zoom=16&themeId=AGRICULTURE-NORMAL-MODE"
        f"&datasetId=S2L2A&fromTime={data_inicio}&toTime={data_fim}"
        f"&instanceId={SENTINEL_INSTANCE_ID}"
    )

# Resposta automática do bot
async def responder_pivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = update.message.text.strip()
    resultados = buscar_info_pivo(consulta)
    if not resultados:
        await update.message.reply_text("❌ Nenhum plantio encontrado para este pivô.")
        return

    for r in resultados:
        lat, lon = r["latitude"], r["longitude"]
        clima = obter_clima(lat, lon)
        link = gerar_link_satelite(lat, lon)

        texto = f"""📍 *Fazenda:* {r['fazenda']}
📅 *Data do Plantio:* {r['data_plantio']}
🥕 *Cultura:* {r['cultura']}
🌀 *Pivô:* {r['pivo']}
📐 *Área:* {r['area']} ha
🌱 *Plantio:* {r['numero_plantio']}
📆 *Subsafra:* {r['subsafra']}
👨‍🌾 *População/Ciclo:* {r['populacao_ciclo']}

{clima}

🛰️ *Imagem do Pivô Atualizada no Mapa:* [Clique aqui]({link})
"""

        await update.message.reply_text(texto, parse_mode="Markdown")
        await update.message.reply_location(latitude=lat, longitude=lon)

# Iniciar app
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_pivo))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
