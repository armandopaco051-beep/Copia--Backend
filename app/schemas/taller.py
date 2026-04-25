from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, time


class TallerCreate(BaseModel):
    nombre: str
    telefono: str
    direccion: str
    latitud: float
    longitud: float
    horario_inicio: Optional[str] = "08:00"
    horario_fin: Optional[str] = "18:00"


class TallerUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: Optional[bool] = None
    horario_inicio: Optional[str] = None
    horario_fin: Optional[str] = None
    usuario_id: Optional[str] = None


class TallerResponse(BaseModel):
    codigo: int
    nombre: str
    telefono: str
    direccion: str
    latitud: float
    longitud: float
    activo: bool
    estado_registro: str
    observacion_admin: Optional[str] = None
    fecha_solicitud: Optional[datetime] = None
    fecha_respuesta: Optional[datetime] = None
    horario_inicio: Optional[time] = None
    horario_fin: Optional[time] = None
    usuario_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)