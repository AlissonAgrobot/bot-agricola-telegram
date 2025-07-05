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

# ============ SCRIPTS DE IMAGEM ============
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

# ============ TOKEN OAUTH2 ============
def obter_token_sentinel():
    url = "https://services.sentinel-hub.com/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": SENTINEL
