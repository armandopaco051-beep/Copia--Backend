from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AsignacionCreate(BaseModel):
    id_incidente: int
    id_taller: int
    id_tecnico: str
    fecha_asignacion: datetime
    estado: str
    observaciones: Optional[str] = None

class ResponderAsignacion(BaseModel):
    aceptada: bool
    observacion: str = ""

class AsignarTecnicoRequest(BaseModel):
    codigo_tecnico: str
    observacion : Optional[str] = None 