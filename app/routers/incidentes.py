from tokenize import String
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.operaciones import Incidente , Asignacion
from app.schemas.incidente import IncidenteCreate, IncidenteUpdate, IncidenteResponse
from app.models.talleres import Taller
from app.routers.asignacion import crear_asignacion_automatica
from fastapi import Request

router = APIRouter(prefix="/incidentes", tags=["Incidentes - CU10"])


# CU-10 — Crear incidente (reporte de emergencia)
@router.post("/", response_model=IncidenteResponse, status_code=201)
def crear_incidente(datos: IncidenteCreate, db: Session = Depends(get_db), request: Request = None):
    # 1. Crear el incidente
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

    # ✅ CAMBIO: genera el código del incidente antes del commit
    db.flush()

    # ✅ CAMBIO: envía la emergencia al taller más cercano
    asignacion = crear_asignacion_automatica(id_incidente=nuevo.codigo, request=request, db= db)

    if asignacion:
        # ✅ Opcional: cambiar estado del incidente si tienes estado "en búsqueda/asignado"
        nuevo.id_estado_incidente = 2
    else:
        # ✅ Opcional: si no hay talleres disponibles
        # nuevo.id_estado_incidente = 1
        pass

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

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db


@router.get("/{id_incidente}/seguimiento")
def obtener_seguimiento_incidente(
    id_incidente: int,
    db: Session = Depends(get_db)
):
    sql = text("""
        SELECT 
            i.codigo AS id_incidente,
            COALESCE(ei.nombre, 'Reporte recibido') AS estado_incidente,

            a.id_estado_asignacion,
            ea.nombre AS estado_asignacion,

            ta.nombre AS taller_nombre,

            a.id_tecnico AS tecnico_codigo,
            CONCAT(COALESCE(u.nombre, ''), ' ', COALESCE(u.apellido, '')) AS tecnico_nombre,
            COALESCE(te.telefono, u.telefono) AS tecnico_telefono,
            te.latitud AS tecnico_latitud,
            te.longitud AS tecnico_longitud

        FROM operaciones.incidente i

        LEFT JOIN catalogo.estado_incidente ei 
            ON ei.id = i.id_estado_incidente

        LEFT JOIN operaciones.asignacion a 
            ON a.id_incidente = i.codigo

        LEFT JOIN catalogo.estado_asignacion ea 
            ON ea.id = a.id_estado_asignacion

        LEFT JOIN talleres.tecnico te 
            ON te.codigo::text = a.id_tecnico::text

        LEFT JOIN seguridad.usuario u 
            ON u.codigo::text = a.id_tecnico::text

        LEFT JOIN talleres.taller ta 
            ON ta.codigo = a.id_taller

        WHERE i.codigo = :id_incidente

        ORDER BY a.fecha_asignacion DESC NULLS LAST
        LIMIT 1
    """)

    row = db.execute(sql, {"id_incidente": id_incidente}).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Incidente no encontrado"
        )

    return {
        "id_incidente": row["id_incidente"],
        "estado_incidente": row["estado_incidente"],
        "id_estado_asignacion": row["id_estado_asignacion"],
        "estado_asignacion": row["estado_asignacion"],
        "taller_nombre": row["taller_nombre"],
        "tecnico": {
            "codigo": row["tecnico_codigo"],
            "nombre": row["tecnico_nombre"],
            "telefono": row["tecnico_telefono"],
            "latitud": float(row["tecnico_latitud"]) if row["tecnico_latitud"] is not None else None,
            "longitud": float(row["tecnico_longitud"]) if row["tecnico_longitud"] is not None else None,
        }
    }