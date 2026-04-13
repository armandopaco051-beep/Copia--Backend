from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime


class TecnicoCreate(BaseModel):
    telefono: str
    direccion: str
    latidud: Decimal
    longitud: Decimal

class TecnicoUpdate(BaseModel):
    telefono: Optional[str] = None
    latidud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    disponibilidad: Optional[bool] = None

class TecnicoResponse(BaseModel):
    codigo: int
    disponibilidad: bool
    latitud: Decimal
    longitud: Decimal
    telefono : str
    id_taller :int 
    id_usuario : str 
    class Config:
        from_attributes = True
