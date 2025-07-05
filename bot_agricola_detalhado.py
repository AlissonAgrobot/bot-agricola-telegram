import json
import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ============ CONFIGURAÇÕES ============
TOKEN = "8006515043:AAFapaNdYxv1sfgH126gxuBx3vAASAz-UF4"
OPENWEATHER_API_KEY = "a633bcced8f4d4eb76047d2a4981e252"
SENTINEL_CLIENT_ID = "91639194-75b7-4fd5-862a-55f3ce60b58b"
SENTINEL_CLIENT_SECRET = "XrBXCRahvPprZjZ1xkKNgqLr6IbVpJm1"

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

# ============ OAUTH2 ============
def obter_token_sentinel():
    url = "https://services.sentinel-hub.com/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": SENTINEL_CLIENT_ID,
        "client_secret": SENTINEL_CLIENT_SECRET
    }
    r = requests.post(url, data=data)
    return r.json().get("access_token")

# ============ IMAGENS ============
def baixar_imagem(lat, lon, script, nome_arquivo):
    token = obter_token_sentinel()
    url = "https://services.sentinel-hub.com/api/v1/process"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "input": {
            "bounds": {
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            },
            "data": [{"type": "sentinel-2-l2a"}]
        },
        "output": {
            "width": 512,
            "height": 512,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}]
        },
        "evalscript": script
    }
    r = requests.post(url, headers=headers, json=payload)
    if r.ok:
        with open(nome_arquivo, "wb") as f:
            f.write(r.content)
        return nome_arquivo
    return None

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

        rgb_path = baixar_imagem(lat, lon, SCRIPT_RGB, "imagem_rgb.png")
        ndvi_path = baixar_imagem(lat, lon, SCRIPT_NDVI, "imagem_ndvi.png")

        if rgb_path:
            await update.message.reply_photo(photo=InputFile(rgb_path), caption="🖼️ Imagem RGB")
        if ndvi_path:
            await update.message.reply_photo(photo=InputFile(ndvi_path), caption="🟢 Imagem NDVI")

        await update.message.reply_location(latitude=lat, longitude=lon)

# ============ MAIN ============
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_pivo))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
