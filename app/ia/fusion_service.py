from app.ia.texto_service import clasificar_texto, CATEGORIA_A_ID, CATEGORIA_A_PRIORIDAD


def fusionar_resultados(
    resultado_audio: dict = None,
    resultado_imagen: dict = None,
    resultado_texto: dict = None,
    descripcion_manual: str = ""
) -> dict:
    """
    Fusiona los resultados de audio, imagen y texto
    para determinar la categoría y prioridad final del incidente.
    Usa votación ponderada con renormalización.
    """

    votos = {}
    detalle_fuentes = {}
    peso_total_activo = 0.0

    # Peso de cada fuente
    PESO_IMAGEN = 0.40
    PESO_AUDIO = 0.35
    PESO_TEXTO = 0.25

    def registrar_voto(nombre_fuente: str, categoria: str, confianza: float, peso: float):
        nonlocal peso_total_activo

        if not categoria:
            categoria = "otros"

        if confianza is None:
            confianza = 0.0

        puntaje = confianza * peso
        votos[categoria] = votos.get(categoria, 0.0) + puntaje
        peso_total_activo += peso

        detalle_fuentes[nombre_fuente] = {
            "categoria": categoria,
            "confianza": round(confianza, 3),
            "peso": peso,
            "aporte": round(puntaje, 3)
        }

    # 1) Imagen
    if resultado_imagen and resultado_imagen.get("ok"):
        categoria_img = resultado_imagen.get("categoria_detectada", "otros")
        confianza_img = float(resultado_imagen.get("confianza", 0.0))
        registrar_voto("imagen", categoria_img, confianza_img, PESO_IMAGEN)

    # 2) Audio -> se toma la transcripción y se clasifica como texto
    if resultado_audio and resultado_audio.get("ok"):
        transcripcion = resultado_audio.get("transcripcion", "").strip()
        if transcripcion:
            res_audio_texto = clasificar_texto(transcripcion)
            categoria_audio = res_audio_texto.get("categoria", "otros")
            confianza_audio = float(res_audio_texto.get("confianza", 0.0))
            registrar_voto("audio", categoria_audio, confianza_audio, PESO_AUDIO)

    # 3) Texto ya clasificado
    if resultado_texto and resultado_texto.get("categoria"):
        categoria_txt = resultado_texto.get("categoria", "otros")
        confianza_txt = float(resultado_texto.get("confianza", 0.0))
        registrar_voto("texto", categoria_txt, confianza_txt, PESO_TEXTO)

    # 4) Si no vino resultado_texto pero sí descripción manual, clasificarla
    elif descripcion_manual and descripcion_manual.strip():
        res_texto = clasificar_texto(descripcion_manual)
        categoria_txt = res_texto.get("categoria", "otros")
        confianza_txt = float(res_texto.get("confianza", 0.0))
        registrar_voto("texto", categoria_txt, confianza_txt, PESO_TEXTO)

    # Si no hubo ninguna fuente útil
    if not votos or peso_total_activo == 0:
        categoria_final = "otros"
        confianza_normalizada = 0.0
    else:
        categoria_final = max(votos, key=votos.get)
        confianza_bruta = votos[categoria_final]
        confianza_normalizada = confianza_bruta / peso_total_activo

    # Medida de incertidumbre
    incertidumbre = confianza_normalizada < 0.55

    return {
        "categoria_final": categoria_final,
        "id_categoria": CATEGORIA_A_ID.get(categoria_final, 5),
        "id_prioridad": CATEGORIA_A_PRIORIDAD.get(categoria_final, 3),
        "confianza": round(confianza_normalizada, 3),
        "incertidumbre": incertidumbre,
        "requiere_revision": incertidumbre,
        "votos": {k: round(v, 3) for k, v in votos.items()},
        "detalle_fuentes": detalle_fuentes,
        "resumen": generar_resumen(
            categoria_final=categoria_final,
            confianza=confianza_normalizada,
            resultado_audio=resultado_audio,
            resultado_imagen=resultado_imagen,
            descripcion_manual=descripcion_manual
        )
    }


def generar_resumen(
    categoria_final: str,
    confianza: float,
    resultado_audio: dict = None,
    resultado_imagen: dict = None,
    descripcion_manual: str = ""
) -> str:
    """
    Genera una ficha técnica resumida del incidente.
    """
    partes = []
    partes.append("📋 FICHA TÉCNICA DEL INCIDENTE")
    partes.append(f"Categoría detectada: {categoria_final.upper()}")
    partes.append(f"Nivel de confianza: {round(confianza * 100)}%")
    partes.append("")

    if resultado_audio and resultado_audio.get("transcripcion"):
        partes.append("📢 Reporte por voz:")
        partes.append(resultado_audio["transcripcion"])
        partes.append("")

    if resultado_imagen and resultado_imagen.get("daños_detectados"):
        danos = resultado_imagen.get("daños_detectados", [])
        if danos:
            partes.append("📷 Daños detectados en imagen:")
            partes.append(", ".join(map(str, danos)))
            partes.append("")

    if descripcion_manual and descripcion_manual.strip():
        partes.append("📝 Descripción del cliente:")
        partes.append(descripcion_manual.strip())
        partes.append("")

    if confianza < 0.55:
        partes.append("⚠️ REQUIERE REVISIÓN MANUAL")
    else:
        partes.append("✅ CLASIFICADO AUTOMÁTICAMENTE")

    return "\n".join(partes)