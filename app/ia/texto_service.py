import numpy as np
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# Ruta donde se guarda el modelo entrenado
RUTA_MODELO = "app/ia/modelo_clasificador.joblib"


# Datos de entrenamiento con ejemplos en español
DATOS_ENTRENAMIENTO = {
    "textos": [
        # BATERÍA
        "el auto no enciende nada", "batería descargada", "no arranca el motor",
        "se quedó sin batería", "luces no funcionan", "no tiene corriente",
        "alternador dañado", "batería muerta", "no prende el carro",
        "el motor no responde al girar la llave",

        # LLANTA
        "llanta pinchada", "goma desinflada", "rueda ponchada",
        "llanta baja de presión", "se reventó la llanta", "rueda dañada",
        "neumático desinflado", "pinchazo en la carretera", "llanta tronada",
        "rueda sin aire",

        # MOTOR
        "motor recalentado", "humo del motor", "falla mecánica",
        "ruido extraño en el motor", "pierde aceite", "luz del motor encendida",
        "sobrecalentamiento", "mancha de aceite", "golpeteo en el motor",
        "temperatura muy alta",

        # CHOQUE
        "tuve un accidente", "choqué con otro vehículo", "golpe en la carrocería",
        "colisión leve", "raspón en la puerta", "daño en el parachoques",
        "impacto frontal", "accidente de tráfico", "daño visible en carrocería",
        "choque trasero",

        # COMBUSTIBLE
        "me quedé sin gasolina", "sin combustible", "tanque vacío",
        "reserva de combustible", "sin diesel", "gasolina agotada",
        "indicador de combustible en cero", "me quedé varado sin gasolina",

        # CERRAJERÍA
        "dejé las llaves adentro", "perdí la llave del carro",
        "llave atrapada en el vehículo", "no puedo abrir el carro",
        "cerradura trabada", "llave dentro del auto cerrado",
        "encerré las llaves", "perdí el control remoto del carro",
    ],
    "categorias": [
        *["bateria"] * 10,
        *["llanta"] * 10,
        *["motor"] * 10,
        *["choque"] * 10,
        *["combustible"] * 8,
        *["cerrajeria"] * 8,
    ]
}

# Mapeo a IDs de categoría en la BD
CATEGORIA_A_ID = {
    "bateria": 1,
    "llanta": 2,
    "motor": 3,
    "choque": 4,
    "combustible": 5,
    "cerrajeria": 5,
    "otros": 5,
}

CATEGORIA_A_PRIORIDAD = {
    "bateria": 2,    # media
    "llanta": 2,     # media
    "motor": 1,      # alta
    "choque": 1,     # alta
    "combustible": 2,
    "cerrajeria": 3, # baja
    "otros": 3,
}

_pipeline = None


def get_modelo():
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    # Si existe el modelo guardado, cargarlo
    if os.path.exists(RUTA_MODELO):
        _pipeline = joblib.load(RUTA_MODELO)
        print("✅ Modelo de texto cargado desde archivo")
        return _pipeline

    # Si no existe, entrenar uno nuevo
    print("⏳ Entrenando modelo de clasificación de texto...")
    _pipeline = Pipeline([
        ('vectorizer', TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            analyzer='word'
        )),
        ('classifier', MultinomialNB(alpha=0.1))
    ])

    _pipeline.fit(
        DATOS_ENTRENAMIENTO["textos"],
        DATOS_ENTRENAMIENTO["categorias"]
    )

    joblib.dump(_pipeline, RUTA_MODELO)
    print("✅ Modelo entrenado y guardado")
    return _pipeline


def clasificar_texto(texto: str) -> dict:
    """Clasifica el texto del incidente en una categoría"""
    if not texto or len(texto.strip()) < 3:
        return {
            "categoria": "otros",
            "id_categoria": 5,
            "id_prioridad": 3,
            "confianza": 0.0,
            "incertidumbre": True
        }

    try:
        modelo = get_modelo()
        categoria = modelo.predict([texto])[0]
        probabilidades = modelo.predict_proba([texto])[0]
        confianza = float(np.max(probabilidades))

        return {
            "categoria": categoria,
            "id_categoria": CATEGORIA_A_ID.get(categoria, 5),
            "id_prioridad": CATEGORIA_A_PRIORIDAD.get(categoria, 3),
            "confianza": round(confianza, 3),
            "incertidumbre": confianza < 0.5
        }
    except Exception as e:
        return {
            "categoria": "otros",
            "id_categoria": 5,
            "id_prioridad": 3,
            "confianza": 0.0,
            "incertidumbre": True,
            "error": str(e)
        }