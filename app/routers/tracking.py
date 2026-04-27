from datetime import datetime, timedelta 
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from pydantic import BaseModel
from app.models.operaciones import Asignacion


router = APIRouter(prefix="/tracking", tags=["Tracking"])

# Memoria Temporal 
# No se guarda en base de datos

ubicaciones_en_vivo = {}

#si pasa mas de 900 segundos sin actualizar, se considera offline
TTL_segundos =  900 

class UbicacionTecnicoRequest(BaseModel):
    id_asignacion: int 
    latitud: float
    longitud: float

@router.post("/ubicacion")
def actualizar_ubicacion_tecnico(
    datos: UbicacionTecnicoRequest,
    db: Session = Depends(get_db)
):
    asignacion = db.query(Asignacion).filter(
        Asignacion.id == datos.id_asignacion
    ).first()

    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    if not asignacion.id_tecnico:
        raise HTTPException(
            status_code=400,
            detail="La asignación no tiene técnico asignado"
        )

    if asignacion.id_estado_asignacion != 5:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede enviar ubicación cuando el técnico está en camino"
        )

    ubicacion = {
        "id_asignacion": asignacion.id,
        "id_incidente": asignacion.id_incidente,
        "codigo_tecnico": asignacion.id_tecnico,
        "latitud": datos.latitud,
        "longitud": datos.longitud,
        "estado": "En camino",
        "fecha": datetime.now().isoformat()
    }

    # ✅ Guardamos solo la última ubicación por incidente
    ubicaciones_en_vivo[asignacion.id_incidente] = ubicacion

    return {
        "mensaje": "Ubicación actualizada correctamente",
        "ubicacion": ubicacion
    }


@router.get("/incidente/{id_incidente}/ultima")
def obtener_ultima_ubicacion_tecnico(id_incidente: int):
    ubicacion = ubicaciones_en_vivo.get(id_incidente)

    if not ubicacion:
        raise HTTPException(
            status_code=404,
            detail="Aún no hay ubicación del técnico para este incidente"
        )

    fecha = datetime.fromisoformat(ubicacion["fecha"])

    if datetime.now() - fecha > timedelta(seconds=TTL_SEGUNDOS):
        raise HTTPException(
            status_code=404,
            detail="La ubicación del técnico ya no está actualizada"
        )

    return ubicacion