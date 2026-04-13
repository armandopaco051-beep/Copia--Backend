from tokenize import String
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.operaciones import Incidente
from app.schemas.incidente import IncidenteCreate, IncidenteUpdate, IncidenteResponse

router = APIRouter(prefix="/incidentes", tags=["Incidentes - CU10"])


# CU-10 — Crear incidente (reporte de emergencia)
@router.post("/", response_model=IncidenteResponse, status_code=201)
def crear_incidente(datos: IncidenteCreate, db: Session = Depends(get_db)):
    nuevo = Incidente(
        descripcion=datos.descripcion,
        latitud=datos.latitud,
        longitud=datos.longitud,
        fecha_reporte=datos.fecha_reporte,
        id_prioridad=datos.id_prioridad,
        id_categoria_problema=datos.id_categoria_problema,
        id_estado_incidente=datos.id_estado_incidente,
        id_vehiculo=datos.id_vehiculo,
        codigo_usuario=datos.codigo_usuario,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


# Obtener incidente por código
@router.get("/{codigo}", response_model=IncidenteResponse)
def obtener_incidente(codigo: int, db: Session = Depends(get_db)):
    inc = db.query(Incidente).filter(Incidente.codigo == codigo).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    return inc


# Historial de incidentes por usuario
@router.get("/usuario/{codigo_usuario}", response_model=List[IncidenteResponse])
def historial_usuario(codigo_usuario: str, db: Session = Depends(get_db)):
    return db.query(Incidente).filter(
        Incidente.codigo_usuario == codigo_usuario
    ).order_by(Incidente.fecha_reporte.desc()).all()


# Actualizar estado del incidente
@router.put("/{codigo}", response_model=IncidenteResponse)
def actualizar_incidente(
    codigo: int,
    datos: IncidenteUpdate,
    db: Session = Depends(get_db)
):
    inc = db.query(Incidente).filter(Incidente.codigo == codigo).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(inc, campo, valor)
    db.commit()
    db.refresh(inc)
    return inc


# CU — Cancelar incidente
@router.put("/{codigo}/cancelar", response_model=IncidenteResponse)
def cancelar_incidente(codigo: int, db: Session = Depends(get_db)):
    inc = db.query(Incidente).filter(Incidente.codigo == codigo).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    inc.id_estado_incidente = 4  # 4 = cancelado
    inc.fecha_cierre = datetime.now()
    db.commit()
    db.refresh(inc)
    return inc


# Listar todos los incidentes (para admin/taller)
@router.get("/", response_model=List[IncidenteResponse])
def listar_incidentes(db: Session = Depends(get_db)):
    return db.query(Incidente).order_by(
        Incidente.fecha_reporte.desc()
    ).all()