from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.seguridad import Bitacora, Usuario
from app.schemas.usuario import BitacoraResponse

router = APIRouter(prefix="/bitacora", tags=["Bitácora"])


@router.get("", response_model=List[BitacoraResponse])
def listar_bitacora(
    modulo: Optional[str] = None,
    codigo_usuario: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Bitacora)
    if modulo:
        query = query.filter(Bitacora.modulo == modulo)
    if codigo_usuario:
        query = query.filter(Bitacora.codigo_usuario == codigo_usuario)

    registros = query.order_by(Bitacora.fecha.desc()).limit(200).all()

    resultado = []
    for r in registros:
        u = db.query(Usuario).filter(Usuario.codigo == r.codigo_usuario).first()
        resultado.append({
            "id": r.id,
            "codigo_usuario": r.codigo_usuario,
            "accion": r.accion,
            "modulo": r.modulo,
            "descripcion": r.descripcion,
            "ip_address": r.ip_address,
            "fecha": r.fecha,
            "nombre_usuario": f"{u.nombre} {u.apellido}" if u else "Desconocido"
        })
    return resultado