from ast import List
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.utils import deep_dict_update
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from app.database import get_db
from app.models.multimedia import Evidencia
from app.models.operaciones import Incidente
from app.ia.audio_service import transcribir_audio
from app.ia.imagen_service import analizar_imagen
from app.ia.fusion_service import fusionar_resultados
from app.schemas import incidente

router = APIRouter(prefix="/evidencias", tags=["Evidencias"])

UPLOAD_DIR  = "uploads"
os.makedirs(f"{UPLOAD_DIR}/audios", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/imagenes", exist_ok=True)

@router.post("/imagen/{id_incidente}")
async def subir_imagen(
    id_incidente : int ,
    archivo: List[UploadFile] = File(...),
    db :Session = Depends(get_db)
):
  "CU11 + CU12 + CU13 : SUBE IMAGEN Y ANALIZA CON LA IA"
  incidente = db.query(Incidente).filter(
    Incidente.codigo  == id_incidente
  ).first()
  if not incidente:
    raise HTTPException(status_code=404, detail="Incidente no encontrado")
  #guarda archivo 
  ext = os.path.splitext(archivo.filename)[1]
  nombre  = f"{uuid.uuid4()}{ext}"
  ruta = f"{UPLOAD_DIR}/imagenes/{nombre}"
  with open(ruta, "wb") as f: 
    shutil.copyfileobj(archivo.file, f)

    #analizar con ia 
    analisis = analizar_imagen(ruta)
    #guardar evidencia en la base 
    evidencia =  Evidencia(
        url_archivo =ruta,
        id_tipo_evidencia = 1 , 
        id_incidente= id_incidente,
        transcripcion= analisis.get("transcripcion", "")
    )
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)
    return {
        "mensaje": "Imagen subida y analizada correctamente",
        "archivo" : ruta,
        "analisis_ia": analisis
    }

@router.post("/audio/{id_cliente}") 
async def subir_audio(
    id_incidente : int,
    archivo :list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    CU11 + CU12 + CU13 : SUBE AUDIO Y ANALIZA CON LA IA
    """
    incidente = db.query(Incidente).filter(
        Incidente.codigo == id_incidente
    ).first()
    if not incidente :
        raise HTTPException(status_code = 404, detail = "incidente no encontrado")
    #guardar archivo 
    ext = os.path.splitext(archivo.filename)[1] or ".m4a"
    nombre = f"{uuid.uuid4()}{ext}"
    ruta = f"{UPLOAD_DIR}/audios/{nombre}"
    with open(ruta, "wb") as f:
        shutil.copyfileobj(archivo.file, f)
    #transcribir mediante ia 
    resultado = transcribir_audio(ruta)

    #guardar evidencia con transcripcion

    evidencia = Evidencia(
        url_archivo = ruta,
        id_tipo_evidencia = 2,
        id_incidente = id_incidente,
        transcripcion=  resultado.get("transcripcion", "")
    )
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)
    return {
        "mensaje": "Audio subido y analizado correctamente",
        "archivo" : ruta,
        "transcripcion" : resultado.get("transcripcion", ""),
        "palabras_clave" : resultado.get("palabras_clave",[])
    }


@router.post("/texto/{id_incidente}")
async def subir_texto(
    id_incidente: int,
    descripcion: str = Form(...),
    db: Session = Depends(get_db)
):
    """CU-11: Guarda descripción de texto"""
    incidente = db.query(Incidente).filter(
        Incidente.codigo == id_incidente).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    evidencia = Evidencia(
        url_archivo=None,
        id_tipo_evidencia=3,  # texto
        id_incidente=id_incidente,
        transcripcion=descripcion
    )
    db.add(evidencia)
    db.commit()

    return {"mensaje": "Descripción guardada", "descripcion": descripcion}


@router.get("/{id_incidente}")
def listar_evidencias(id_incidente: int, db: Session = Depends(get_db)):
    """Lista todas las evidencias de un incidente"""
    evidencias = db.query(Evidencia).filter(
        Evidencia.id_incidente == id_incidente).all()
    return [{
        "codigo": e.codigo,
        "url_archivo": e.url_archivo,
        "transcripcion": e.transcripcion,
        "id_tipo_evidencia": e.id_tipo_evidencia,
        "fecha_subida": e.fecha_subida
    } for e in evidencias]


