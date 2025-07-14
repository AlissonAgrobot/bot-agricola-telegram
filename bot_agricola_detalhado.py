def numero_para_emoji(numero):
    # Converte um número inteiro em string com emojis (ex: 12 -> "1️⃣2️⃣")
    emoji_numeros = {
        "0": "0️⃣",
        "1": "1️⃣",
        "2": "2️⃣",
        "3": "3️⃣",
        "4": "4️⃣",
        "5": "5️⃣",
        "6": "6️⃣",
        "7": "7️⃣",
        "8": "8️⃣",
        "9": "9️⃣"
}
    return ''.join(emoji_numeros.get(d, d) for d in str(numero))

import json
import logging
import requests
import base64
import os
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,  # ✅ Agora incluído corretamente
    ContextTypes,
    filters,
)


# ============ CONFIG ============ 
load_dotenv()
TOKEN = "8006515043:AAFapaNdYxv1sfgH126gxuBx3vAASAz-UF4"
OPENWEATHER_API_KEY = "a633bcced8f4d4eb76047d2a4981e252"
client = OpenAI()  # AQUI ESTÁ CORRETO AGORA

# ============ LOG ============ 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ DADOS ============ 
with open("dados_plantio.json", encoding="utf-8") as f:
    dados_plantio = json.load(f)

# ============ SCRIPTS SENTINEL ============ 
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

def gerar_links_sentinel(lat, lon):
    base_url = "https://apps.sentinel-hub.com/eo-browser/"
    from_date = "2024-06-01"
    to_date = datetime.now().strftime("%Y-%m-%d")
    script_rgb_b64 = base64.b64encode(SCRIPT_RGB.encode("utf-8")).decode("utf-8")
    script_ndvi_b64 = base64.b64encode(SCRIPT_NDVI.encode("utf-8")).decode("utf-8")

    link_rgb = (
        f"{base_url}?lat={lat}&lng={lon}&zoom=16"
        f"&evalscript={script_rgb_b64}"
        f"&datasetId=S2L2A&fromTime={from_date}&toTime={to_date}"
    )
    link_ndvi = (
        f"{base_url}?lat={lat}&lng={lon}&zoom=16"
        f"&evalscript={script_ndvi_b64}"
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

        alerta = "🔴 *ALERTA: Alta probabilidade de chuva nos próximos períodos!*\n" if chuva_prob >= 70 else ""

        if chuva_prob > 0:
            chuva_texto = (
                f"🌧️ Previsão de chuva: {chuva_prob:.0f}%\n"
                f"📏 Estimativa: {chuva_mm:.1f} mm nas próximas 3h"
            )
        else:
            chuva_texto = "🌧️ Previsão de chuva: 0%"

        return (
            f"{alerta}"
            f"🌤️ *Clima agora:* {descricao}\n"
            f"🌡️ Temperatura: {temp:.1f}°C\n"
            f"💧 Umidade: {umidade}%\n"
            f"🍃 Vento: {vento:.2f} m/s\n"
            f"{chuva_texto}"
        )

    return "❌ Clima indisponível."

# ============ COMANDO /start ============ 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌾 Olá! Este é o Bot Agrícola Sekita.\n"
        "Digite o pivô desejado (ex: *Pivô 01*) para consultar:\n"
        "📌 Dados da área\n🌧️ Clima\n🖼️ Imagens RGB e NDVI\n📍 Localização no mapa\n\n"
        "Ou use: /perguntar [sua dúvida] para falar com a IA"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ============ COMANDO /perguntar ============ 
async def perguntar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pergunta = ' '.join(context.args)
    if not pergunta:
        await update.message.reply_text("❓ Use assim: /perguntar [sua dúvida]")
        return
    await update.message.reply_text("🤖 Pensando...")
    try:
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente técnico agrícola, especialista em clima, irrigação, solo e drones agrícolas."},
                {"role": "user", "content": pergunta}
            ],
            temperature=0.6,
            max_tokens=500,
        )
        texto = resposta.choices[0].message.content
        await update.message.reply_text(f"💡 {texto}")
    except Exception as e:
        await update.message.reply_text("❌ Ocorreu um erro ao consultar a IA.")
        logger.error(f"Erro IA: {e}")

# ============ COMANDO PRINCIPAL DO BOT ============ 
# Função para converter número para emoji (até 99)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# === Novo handler interativo ===
async def responder_pivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = update.message.text.strip().lower()
    resultados = [p for p in dados_plantio if consulta in p["Pivô"].lower()]

    if not resultados:
        await update.message.reply_text("❌ Nenhum plantio encontrado para este pivô.")
        return

    fazendas_unicas = list(set(p["Fazenda"] for p in resultados))

    # ✅ Se houver mais de uma fazenda com esse pivô, perguntar qual o usuário deseja
    if len(fazendas_unicas) > 1:
        botoes = [
            [InlineKeyboardButton(f"{p['Pivô']} - {p['Fazenda']}", callback_data=f"{p['Pivô']}|{p['Fazenda']}")]
            for p in resultados
        ]
        await update.message.reply_text(
            "🔎 Foram encontrados vários pivôs com esse nome. Qual você quer consultar?",
            reply_markup=InlineKeyboardMarkup(botoes)
        )
        return

    # ✅ Se só tem um, responde direto
    await exibir_dados_pivo(update, context, resultados)


# === Função auxiliar para exibir os dados formatados ===
async def exibir_dados_pivo(update_or_callback, context, resultados):
    dados_pivo = resultados[0]
    lat, lon = float(dados_pivo["Latitude"]), float(dados_pivo["Longitude"])
    clima = obter_clima(lat, lon)
    link_rgb, link_ndvi = gerar_links_sentinel(lat, lon)

    plantios_formatados = ""
    for r in resultados:
        emoji_plantio = numero_para_emoji(r["Plantio"])
        plantios_formatados += (
            f"{emoji_plantio} Data: {r['Data Plantio']} | Área: {r['Área']} ha | "
            f"População: {r['População']} | Ciclo: {r['Ciclo']} | Colheita: {r['Previsão de colheita']}\n"
        )

    texto = (
        f"📍 *Fazenda:* {dados_pivo['Fazenda']}\n"
        f"💧 *Pivô:* {dados_pivo['Pivô']}\n"
        f"📐 *Área total:* {sum(float(p['Área']) for p in resultados):.2f} ha\n"
        f"🌾 *Cultura:* Alho 2025\n\n"
        f"🧑‍🌾 *Plantios neste pivô:*\n{plantios_formatados}\n"
        f"{clima}\n\n"
        f"🖼️ [Imagem RGB]({link_rgb}) | [Imagem NDVI]({link_ndvi})"
    )

    await update_or_callback.message.reply_text(texto, parse_mode="Markdown", disable_web_page_preview=True)
    await update_or_callback.message.reply_location(latitude=lat, longitude=lon)


# === Novo handler para o clique nos botões ===
async def tratar_callback_pivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pivô, fazenda = query.data.split("|")
    resultados_filtrados = [
        p for p in dados_plantio if p["Pivô"] == pivô and p["Fazenda"] == fazenda
    ]
    await exibir_dados_pivo(query, context, resultados_filtrados)






# ============ MAIN ============ 
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("perguntar", perguntar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_pivo))
    app.add_handler(CallbackQueryHandler(tratar_callback_pivo))  # <- Corrigido aqui
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
