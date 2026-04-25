from pydantic import BaseModel, EmailStr
from typing import Optional
from decimal import Decimal
from datetime import datetime, time

class RegistroAdminTallerCreate(BaseModel):
    codigo_usuario: str
    nombre: str
    apellido: str
    email: EmailStr
    password: str
    telefono: str
    nombre_taller: str
    telefono_taller: str
    direccion_taller: str
    latitud_taller: Decimal
    longitud_taller: Decimal
    horario_inicio: Optional[time] = time(8, 0)
    horario_fin: Optional[time] = time(18, 0)


class ResponderSolicitudRequest(BaseModel):
    aceptada: bool
    observacion: Optional[str] = None


class SolicitudAdminTallerResponse(BaseModel):
    codigo_usuario: str
    nombre: str
    apellido: str
    email: str
    telefono: str

    codigo_taller: int
    nombre_taller: str
    telefono_taller: str
    direccion_taller: str
    latitud_taller: Decimal
    longitud_taller: Decimal
    horario_inicio: Optional[time] = None
    horario_fin: Optional[time] = None

    estado_registro: str
    observacion_admin: Optional[str] = None
    fecha_solicitud: datetime
    fecha_respuesta: Optional[datetime] = None

    class Config:
        from_attributes = True