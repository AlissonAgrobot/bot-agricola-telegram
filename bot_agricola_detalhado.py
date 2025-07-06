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

        # ========= IMAGENS =========
        await update.message.reply_text("⏳ Baixando imagens atualizadas do Sentinel Hub...")

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

        rgb_path = baixar_imagem(lat, lon, SCRIPT_RGB, "imagem_rgb.png")
        ndvi_path = baixar_imagem(lat, lon, SCRIPT_NDVI, "imagem_ndvi.png")

        if rgb_path:
            await update.message.reply_photo(photo=InputFile(rgb_path), caption="🖼️ Imagem RGB")
        else:
            await update.message.reply_text("⚠️ Não foi possível baixar a imagem RGB.")

        if ndvi_path:
            await update.message.reply_photo(photo=InputFile(ndvi_path), caption="🟢 Imagem NDVI")
        else:
            await update.message.reply_text("⚠️ Não foi possível baixar a imagem NDVI.")

        # ========= LOCALIZAÇÃO =========
        await update.message.reply_location(latitude=lat, longitude=lon)
