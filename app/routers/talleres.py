from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.talleres import Taller
from app.schemas.taller import TallerCreate, TallerUpdate, TallerResponse

router = APIRouter(prefix="/talleres", tags=["Talleres"])


@router.post("", response_model=TallerResponse, status_code=201)
def crear_taller(datos: TallerCreate, db: Session = Depends(get_db)):
    nuevo = Taller(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("", response_model=List[TallerResponse])
def listar_talleres(db: Session = Depends(get_db)):
    return db.query(Taller).filter(Taller.activo == True).all()


@router.get("/{codigo}", response_model=TallerResponse)
def obtener_taller(codigo: int, db: Session = Depends(get_db)):
    t = db.query(Taller).filter(Taller.codigo == codigo).first()
    if not t:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    return t


@router.put("/{codigo}", response_model=TallerResponse)
def actualizar_taller(codigo: int, datos: TallerUpdate, db: Session = Depends(get_db)):
    t = db.query(Taller).filter(Taller.codigo == codigo).first()
    if not t:
        raise HTTPException(status_code=404, detail="Taller no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(t, campo, valor)

    db.commit()
    db.refresh(t)
    return t


@router.delete("/{codigo}")
def desactivar_taller(codigo: int, db: Session = Depends(get_db)):
    t = db.query(Taller).filter(Taller.codigo == codigo).first()
    if not t:
        raise HTTPException(status_code=404, detail="Taller no encontrado")

    t.activo = False
    db.commit()
    db.refresh(t)

    return {"mensaje": "Taller desactivado"}