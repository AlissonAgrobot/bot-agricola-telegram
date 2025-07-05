import json
import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ======================== CONFIGURAÇÕES ========================
TOKEN = "8006515043:AAFapaNdYxv1sfgH126gxuBx3vAASAz-UF4"
OPENWEATHER_API_KEY = "a633bcced8f4d4eb76047d2a4981e252"
SENTINEL_INSTANCE_ID = "1b9f5321-056a-4a9e-beaa-954934167ba0"

# ======================== LOG ========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================== DADOS ========================
with open("dados_plantio.json", encoding="utf-8") as f:
    dados_plantio = json.load(f)

# ======================== SCRIPTS PERSONALIZADOS ========================
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

# ======================== CLIMA ========================
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

        chuva = f"🌧️ Previsão de chuva: {chuva_prob:.0f}%\n📏 Estimativa: {chuva_mm:.1f} mm nas próximas 3h" if chuva_prob > 0 else "🌧️ Previsão de chuva: 0%"
        return f"🌤️ *Clima agora:* {descricao}\n🌡️ Temperatura: {temp}°C\n💧 Umidade: {umidade}%\n🍃 Vento: {vento:.2f} m/s\n{chuva}"
    return "❌ Clima indisponível."

# ======================== BAIXAR IMAGENS SENTINEL ========================
def baixar_imagem_sentinel(lat, lon, script, nome):
    url = "https://services.sentinel-hub.com/api/v1/process"
    headers = {"Authorization": f"Bearer {SENTINEL_INSTANCE_ID}"}
    payload = {
        "input": {
            "bounds": {"geometry": {"type": "Point", "coordinates": [lon, lat]}},
            "data": [{"type": "sentinel-2-l2a"}]
        },
        "output": {"width": 512, "height": 512, "responses": [{"identifier": "default", "format": {"type": "image/png"}}]},
        "evalscript": script
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.ok:
        with open(nome, "wb") as f:
            f.write(response.content)
        return nome
    return None

# ======================== START ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌾 Olá! Este é o Bot Agrícola Sekita.\n"
        "Digite o pivô desejado (ex: *Pivô 01*) para consultar:\n"
        "📌 Dados da área\n🌧️ Clima\n🖼️ Imagens RGB e NDVI\n📍 Localização no mapa"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ======================== RESPOSTA ========================
async def responder_pivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = update.message.text.strip()
    resultados = [p for p in dados_plantio if consulta.lower() in p["pivo"].lower()]

    if not resultados:
        await update.message.reply_text("❌ Nenhum plantio encontrado para este pivô.")
        return

    for r in resultados:
        lat, lon = r["latitude"], r["longitude"]
        clima = obter_clima(lat, lon)

        texto = (
            f"📍 *Fazenda:* {r['fazenda']}\n"
            f"📅 *Data do Plantio:* {r['data_plantio']}\n"
            f"🥕 *Cultura:* {r['cultura']}\n"
            f"🌀 *Pivô:* {r['pivo']}\n"
            f"📐 *Área:* {r['area']} ha\n"
            f"🌱 *Plantio:* {r['numero_plantio']}\n"
            f"📆 *Subsafra:* {r['subsafra']}\n"
            f"👨‍🌾 *População/Ciclo:* {r['populacao_ciclo']}\n\n"
            f"{clima}"
        )

        await update.message.reply_text(texto, parse_mode="Markdown")

        rgb = baixar_imagem_sentinel(lat, lon, SCRIPT_RGB, "rgb.png")
        ndvi = baixar_imagem_sentinel(lat, lon, SCRIPT_NDVI, "ndvi.png")

        if rgb:
            await update.message.reply_photo(photo=InputFile(rgb), caption="🖼️ Imagem RGB")
        if ndvi:
            await update.message.reply_photo(photo=InputFile(ndvi), caption="🟢 Imagem NDVI")

        await update.message.reply_location(latitude=lat, longitude=lon)

# ======================== MAIN ========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_pivo))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
