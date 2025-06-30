import json
import logging
import requests
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
        "🌾 Olá, seja bem-vindo ao Bot Agrícola Sekita!\n"
        "Aqui você encontra as informações dos plantios e a localização das áreas.\n"
        "Digite (ex: Pivô 01). 🌱"
    )
    await update.message.reply_text(welcome)

# Buscar informações do pivô
def buscar_info_pivo(pivo_nome):
    return [p for p in dados_plantio if pivo_nome.lower() in p["pivo"].lower()]

# Obter clima com temperatura, umidade e vento
def obter_clima(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    r = requests.get(url).json()
    if "weather" in r and "main" in r and "wind" in r:
        descricao = r['weather'][0]['description'].capitalize()
        temp = r['main']['temp']
        umidade = r['main']['humidity']
        vento = r['wind']['speed']
        return (
            f"🌤️ *Clima agora:* {descricao}\n"
            f"🌡️ Temperatura: {temp}°C\n"
            f"💧 Umidade: {umidade}%\n"
            f"🍃 Vento: {vento} m/s"
        )
    return "❌ Clima indisponível."

# Gerar link da imagem de satélite
def gerar_link_satelite(lat, lon):
    return f"https://apps.sentinel-hub.com/eo-browser/?lat={lat}&lng={lon}&zoom=16&themeId=DEFAULT-THEME&instanceId={SENTINEL_INSTANCE_ID}"

# Resposta automática ao digitar pivô
async def responder_pivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = update.message.text.strip()
    resultados = buscar_info_pivo(consulta)
    if not resultados:
        await update.message.reply_text("❌ Nenhum plantio encontrado para este pivô.")
        return
    for r in resultados:
        lat, lon = r["latitude"], r["longitude"]
        clima = obter_clima(lat, lon)
        img = gerar_link_satelite(lat, lon)
        texto = f"""📍 *Fazenda:* {r['fazenda']}
📅 *Data do Plantio:* {r['data_plantio']}
🥕 *Cultura:* {r['cultura']}
🌀 *Pivô:* {r['pivo']}
📐 *Área:* {r['area']} ha
🌱 *Plantio:* {r['numero_plantio']}
📆 *Subsafra:* {r['subsafra']}
👨‍🌾 *População/Ciclo:* {r['populacao_ciclo']}

{clima}

🛰️ *Imagem Satélite Atualizada:*
{img}"""
        await update.message.reply_text(texto, parse_mode="Markdown")

# Inicializar aplicação
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_pivo))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
