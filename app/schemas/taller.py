import string
from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import datetime


class TallerCreate(BaseModel):
    nombre: str
    telefono: str
    direccion: str
    latitud: float
    longitud: float

class TallerUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: Optional[bool] = None

class TallerResponse(BaseModel):
    codigo: int
    nombre: str
    telefono: str
    direccion: str
    latitud: float
    longitud: float
    activo: bool
    model_config = ConfigDict(from_attributes=True)

class TallerUsuarioCreate(BaseModel):
    id_usuario: str
    codigo_taller: int
    fecha_asignacion: datetime  

class TallerUsuarioResponse(TallerUsuarioCreate):
    class Config:
        from_attributes = True