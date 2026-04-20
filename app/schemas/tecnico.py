from pydantic import BaseModel, EmailStr
from typing import Optional
from decimal import Decimal
from datetime import datetime
import email

# tenemos que modificar lo que es la creacion de la base de datos de la parte de tecnico.
class TecnicoCreate(BaseModel):
    codigo : str 
    nombre : str 
    telefono: str
    email : EmailStr
    password :str 
    latidud: Decimal
    longitud: Decimal
    id_taller :int 

class TecnicoUpdate(BaseModel):
    telefono: Optional[str] = None
    latidud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    disponibilidad: Optional[bool] = None

class TecnicoResponse(BaseModel):
    codigo: int
    nombre :Optional[str] = None
    disponibilidad: bool
    email: EmailStr
    latitud: Decimal
    longitud: Decimal
    telefono : str
    id_taller :int 
    class Config:
        from_attributes = True
