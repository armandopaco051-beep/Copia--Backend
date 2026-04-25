from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class TecnicoCreate(BaseModel):
    codigo: str
    nombre: str
    telefono: str
    disponibilidad: bool = True
    latitud: Decimal
    longitud: Decimal
    id_taller: int


class TecnicoUpdate(BaseModel):
    nombre: Optional[str] = None
    disponibilidad: Optional[bool] = None
    telefono: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    id_taller: Optional[int] = None


class TecnicoResponse(BaseModel):
    codigo: str
    nombre: str
    email: str
    disponibilidad: bool
    latitud: Decimal
    longitud: Decimal
    telefono: str
    id_taller: int
    id_rol: int

    class Config:
        from_attributes = True


class TecnicoLoginRequest(BaseModel):
    email: str
    password: str


class TecnicoCreateAdminTaller(BaseModel):
    codigo: str
    nombre: str
    telefono: str
    disponibilidad: bool = True

