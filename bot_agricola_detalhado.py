import json
import logging
import urllib.parse
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ============ CONFIG ============
TOKEN = "8006515043:AAFapaNdYxv1sfgH126gxuBx3vAASAz-UF4"
OPENWEATHER_API_KEY = "a633bcced8f4d4eb76047d2a4981e252"

# ============ LOG ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ DADOS ============
with open("dados_plantio.json", encoding="utf-8") as f:
    dados_plantio = json.load(f)

# ============ SCRIPTS ============
SCRIPT_RGB = """//VERSION=3
function setup() {
  return {
    input: ["B04", "B03", "B02", "dataMask"],
    output: { bands: 4 }
  };
}
function evaluatePixel(samples) {
  let gain = 3.0;
  let gamma = 0.85;
  let boost = 0.05;
  let r = Math.pow(samples.B04 * gain + boost, gamma);
  let g = Math.pow(samples.B03 * gain + boost, gamma);
  let b = Math.pow(samples.B02 * gain + boost, gamma);
  return [Math.min(1, r), Math.min(1, g), Math.min(1, b), samples.dataMask];
}
"""

SCRIPT_NDVI = """//VERSION=3
function setup() {
  return {
    input: ["B08", "B04", "dataMask"],
    output: { bands: 4 }
  };
}
function evaluatePixel(samples) {
  let ndvi = index(samples.B08, samples.B04);
  let color = colorBlend(ndvi,
    [-0.2, 0.0, 0.2, 0.4, 0.6, 0.75, 0.85, 1.0],
    [
      [0.4, 0.0, 0.4],
      [0.6, 0.0, 0.0],
      [1.0, 0.4, 0.0],
      [1.0, 1.0, 0.0],
      [0.6, 1.0, 0.2],
      [0.2, 0.8, 0.2],
      [0.0, 0.5, 0.0],
      [0.0, 0.3, 0.0]
    ]
  );
  return [...color, samples.dataMask];
}
"""

# ============ LINKS SENTINEL ============
def gerar_links_sentinel(lat, lon):
    base_url = "https://apps.sentinel-hub.com/eo-browser/"
    from_date = "2024-06-01"
    to_date = datetime.now().strftime("%Y-%m-%d")

    script_rgb = urllib.parse.quote(SCRIPT_RGB)
    script_ndvi = urllib.parse.quote(SCRIPT_NDVI)

    link_rgb = (
        f"{base_url}?lat={lat}&lng={lon}&zoom=16"
        f"&evalscript={script_rgb}"
        f"&datasetId=S2L2A&fromTime={from_date}&toTime={to_date}"
    )

    link_ndvi = (
        f"{base_url}?lat={lat}&lng={lon}&zoom=16"
        f"&evalscript={script_ndvi}"
        f"&datasetId=S2L2A&fromTime={from_date}&toTime={to_date}"
    )

    return link_rgb, link_ndvi

# ============ CLIMA ============
def obter_clima(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    r = requests.get(url).json()
    if "list" in r and len(r["list"]) > 0:
        atual = r["list"][0]
        descricao = atual["weather"][0]["description"].capitalize()
        temp = atual["main"]["temp"]
        umidade = atual["main"]["humidity"]
        vento = atual["wind"]["speed"]
        chuva_prob = atual.get("pop", 0) * 100
        chuva_mm = atual.get("rain", {}).get("3h", 0)
        chuva_texto = (
            f"🌧️ Previsão de chuva: {chuva_prob:.0f}%\n"
            f"📏 Estimativa: {chuva_mm:.1f} mm nas próximas 3h"
            if chuva_prob > 0 else "🌧️ Previsão de chuva: 0%"
        )
        return (
            f"🌤️ *Clima agora:* {descricao}\n"
            f"🌡️ Temperatura: {temp}°C\n"
            f"💧 Umidade: {umidade}%\n"
            f"🍃 Vento: {vento:.2f} m/s\n"
            f"{chuva_texto}"
        )
    return "❌ Clima indisponível."

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌾 Olá! Este é o Bot Agrícola Sekita.\n"
        "Digite o pivô desejado (ex: *Pivô 01*) para consultar:\n"
        "📌 Dados da área\n🌧️ Clima\n🖼️ Imagens RGB e NDVI\n📍 Localização no mapa"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ============ RESPOSTA ============
async def responder_pivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = update.message.text.strip()
    resultados = [p for p in dados_plantio if consulta.lower() in p["pivo"].lower()]

    if not resultados:
        await update.message.reply_text("❌ Nenhum plantio encontrado para este pivô.")
        return

    for r in resultados:
        lat, lon = r["latitude"], r["longitude"]
        clima = obter_clima(lat, lon)
        link_rgb, link_ndvi = gerar_links_sentinel(lat, lon)

        texto = (
            f"📍 *Fazenda:* {r['fazenda']}\n"
            f"📅 *Data do Plantio:* {r['data_plantio']}\n"
            f"🥕 *Cultura:* {r['cultura']}\n"
            f"🌀 *Pivô:* {r['pivo']}\n"
            f"📐 *Área:* {r['area']} ha\n"
            f"🌱 *Plantio:* {r['numero_plantio']}\n"
            f"📆 *Subsafra:* {r['subsafra']}\n"
            f"👨‍🌾 *População/Ciclo:* {r['populacao_ciclo']}\n\n"
            f"{clima}\n\n"
            f"🖼️ [Abrir imagem RGB no Sentinel Hub]({link_rgb})\n"
            f"🟢 [Abrir imagem NDVI no Sentinel Hub]({link_ndvi})"
        )

        await update.message.reply_text(texto, parse_mode="Markdown", disable_web_page_preview=True)
        await update.message.reply_location(latitude=lat, longitude=lon)

# ============ MAIN ============
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_pivo))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
