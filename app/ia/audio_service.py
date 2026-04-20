from logging import info
import os 
from faster_whisper import WhisperModel

#Modelo pequeño para no consumir mucha memoria
_modelo = None 

def get_modelo() : 
    global modelo
    if _modelo is None : 
        print ("Cargando el modelo , es primera vez asi que puede tardar.....")
        _modelo = WhisperModel("base", device =  cpu, compute_type = "int8")
        print("modelo de whisper listo")

def transcribir_audio(ruta_audio: str, idioma: str = "es")->dict: 
    #"transcribe un archivo ede audio texto" , retorna transcripcion y palabras claves detectadas
    try: 
        modelo = get_modelo()
        segmentos,info= modelo.transcribe(
            ruta_audio,
            language = idioma,
            beam_size =  5
        )
        texto_completo = "".join([seg.text for seg in segmentos]).strip()
        #PALABRAS CLAVES IDENTIFICADAD PARA LA CLASIFICACION 
        palabras_clave = extraer_palabras_clave(texto_completo)
        return{
            "ok": True,
            "transcripcion": texto_completo,
            "idioma_detectado": info.language,
            "palabras_clave": palabras_clave
        }
    except Exception as e:
        return{
            "ok": False,
            "transcripcion": "",
            "error": str(e)
        }
def extraer_palabras_clave(texto: str) -> list:
    """Extrae palabras clave relacionadas a emergencias vehiculares"""
    categorias = {
        "bateria": ["batería", "bateria", "arranque", "carga", "alternador",
                    "no enciende", "sin energía", "corriente"],
        "llanta": ["llanta", "neumático", "pinchazo", "rueda", "goma",
                   "desinflado", "ponchado"],
        "motor": ["motor", "aceite", "falla", "ruido", "humo", "sobrecalenta",
                  "temperatura", "mecánico"],
        "choque": ["choque", "accidente", "colisión", "golpe", "impacto",
                   "raspón", "daño"],
        "combustible": ["combustible", "gasolina", "diesel", "sin gasolina",
                        "vacío", "reserva"],
        "cerrajeria": ["llave", "encerré", "adentro", "puerta", "cerradura",
                       "perdí la llave"],
    }

    texto_lower = texto.lower()
    encontradas = []

    for categoria, palabras in categorias.items():
        for palabra in palabras:
            if palabra in texto_lower:
                encontradas.append({"categoria": categoria, "palabra": palabra})

    return encontradas