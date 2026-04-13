from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.clientes import Vehiculo
from app.schemas.vehiculos import (VehiculoCreate, VehiculoUpdate, VehiculoResponse)

router = APIRouter(prefix="/vehiculos", tags=["Vehiculos"])

@router.post("/", response_model=VehiculoResponse, status_code=201)
def crear_vehiculo(datos: VehiculoCreate, db: Session = Depends(get_db)):
    if db.query(Vehiculo).filter(Vehiculo.placa == datos.placa).first():
        raise HTTPException(status_code=400, detail="Placa ya registrada")
    nuevo = Vehiculo(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/usuario/{id_usuario}", response_model=List[VehiculoResponse])
def listar_por_usuario(id_usuario: str, db: Session = Depends(get_db)):
    return db.query(Vehiculo).filter(Vehiculo.id_usuario == id_usuario).all()


@router.get("/{codigo}", response_model=VehiculoResponse)
def obtener_vehiculo(codigo: int, db: Session = Depends(get_db)):
    v = db.query(Vehiculo).filter(Vehiculo.codigo == codigo).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return v


@router.put("/{codigo}", response_model=VehiculoResponse)
def actualizar_vehiculo(codigo: int, datos: VehiculoUpdate, db: Session = Depends(get_db)):
    v = db.query(Vehiculo).filter(Vehiculo.codigo == codigo).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(v, campo, valor)
    db.commit()
    db.refresh(v)
    return v


@router.delete("/{codigo}")
def desactivar_vehiculo(codigo: int, db: Session = Depends(get_db)):
    v = db.query(Vehiculo).filter(Vehiculo.codigo == codigo).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    v.activo = False
    db.commit()
    return {"mensaje": "Vehículo desactivado"}