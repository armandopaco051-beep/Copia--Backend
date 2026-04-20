import cv2 
import numpy as np 
from PIL import Image
import os


# INTENTAR CARGAR YOLO SI NO ESTA DISPONIBLE  USAR OPEN CTIY 
try :
    from ultralytics import YOLO
    _yolo_disponible = True 
    _modelo_yolo = None
except ImportError:
    _yolo_disponible = False
    
def get_yolo(): 
    global _modelo_yolo 
    if _modelo_yolo is None and _yolo_disponible:
        # el modelo nano es mas ligero 
        _modelo_yolo=  YOLO("yolov8n.pt") 
    return _modelo_yolo

#esta parte del codigo es de chat gpt 
def analizar_imagen(rutas_imagenes: list[str]) -> dict:
    resultados = []
    danos_totales = []
    mejor_categoria = "otros"
    mejor_confianza = 0.0
    descripciones = []

    for ruta in rutas_imagenes:
        r = analizar_imagen(ruta)
        resultados.append(r)

        if r.get("ok"):
            danos_totales.extend(r.get("daños_detectados", []))
            if r.get("descripcion"):
                descripciones.append(r["descripcion"])

            if r.get("confianza", 0) > mejor_confianza:
                mejor_confianza = r["confianza"]
                mejor_categoria = r["categoria_detectada"]

    return {
        "ok": True,
        "cantidad_imagenes": len(rutas_imagenes),
        "categoria_detectada": mejor_categoria,
        "confianza": mejor_confianza,
        "daños_detectados": danos_totales,
        "descripcion": " | ".join(descripciones),
        "resultados_por_imagen": resultados
    }

def analizar_con_opencv(ruta_imagen: str) -> dict:
    """Análisis básico con OpenCV — detecta daños por color y forma"""
    img = cv2.imread(ruta_imagen)
    if img is None:
        return {"categoria_detectada": "otros", "confianza": 0.1}

    # Convertir a HSV para análisis de color
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    alto, ancho = img.shape[:2]
    total_pixeles = alto * ancho

    resultados = {}

    # Detectar zona de motor: humo (colores grises/blancos)
    mask_humo = cv2.inRange(hsv,
        np.array([0, 0, 180]),
        np.array([180, 30, 255]))
    porcentaje_humo = cv2.countNonZero(mask_humo) / total_pixeles

    # Detectar manchas de aceite (colores muy oscuros)
    mask_oscuro = cv2.inRange(hsv,
        np.array([0, 0, 0]),
        np.array([180, 255, 50]))
    porcentaje_oscuro = cv2.countNonZero(mask_oscuro) / total_pixeles

    # Detectar daños estructurales: buscar contornos irregulares
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bordes = cv2.Canny(gris, 100, 200)
    contornos, _ = cv2.findContours(
        bordes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    contornos_grandes = [c for c in contornos
                         if cv2.contourArea(c) > total_pixeles * 0.01]
    tiene_daño_estructural = len(contornos_grandes) > 5

    # Clasificación basada en análisis
    if porcentaje_humo > 0.15:
        return {
            "categoria_detectada": "motor",
            "confianza": min(0.7, porcentaje_humo * 2),
            "descripcion": "Se detectó posible humo o vapor en la imagen",
            "daños_detectados": ["humo_detectado"]
        }
    elif porcentaje_oscuro > 0.2:
        return {
            "categoria_detectada": "motor",
            "confianza": 0.55,
            "descripcion": "Se detectaron manchas oscuras, posible derrame de aceite",
            "daños_detectados": ["mancha_aceite"]
        }
    elif tiene_daño_estructural:
        return {
            "categoria_detectada": "choque",
            "confianza": 0.6,
            "descripcion": "Se detectaron irregularidades estructurales en el vehículo",
            "daños_detectados": ["daño_estructural"]
        }
    else:
        return {
            "categoria_detectada": "otros",
            "confianza": 0.3,
            "descripcion": "No se detectaron patrones específicos",
            "daños_detectados": []
        }


def analizar_con_yolo(ruta_imagen: str) -> dict:
    """Análisis con YOLO para detección de objetos"""
    try:
        modelo = get_yolo()
        resultados = modelo(ruta_imagen, conf=0.25, verbose=False)

        objetos_detectados = []
        categoria = "otros"
        confianza_max = 0.0

        # Mapeo de clases YOLO a categorías del sistema
        mapeo_clases = {
            "car": "vehiculo", "truck": "vehiculo",
            "tire": "llanta", "wheel": "llanta",
            "fire": "motor", "smoke": "motor",
            "person": "asistencia",
        }

        for resultado in resultados:
            for box in resultado.boxes:
                clase = resultado.names[int(box.cls)]
                confianza = float(box.conf)
                objetos_detectados.append({
                    "objeto": clase,
                    "confianza": round(confianza, 3)
                })
                if confianza > confianza_max:
                    confianza_max = confianza
                    categoria = mapeo_clases.get(clase, "otros")

        return {
            "categoria_detectada": categoria,
            "confianza": confianza_max,
            "objetos": objetos_detectados
        }
    except Exception as e:
        return {
            "categoria_detectada": "otros",
            "confianza": 0.0,
            "objetos": [],
            "error": str(e)
        }