from re import S
from pydantic import BaseModel
from typing import Optional


class VehiculoCreate(BaseModel):
    modelo :str
    placa :str
    marca : str
    año : str
    id_usuario : str 

class VehiculoUpdate(BaseModel): 
    modelo : Optional[str] = None
    placa : Optional[str] = None
    marca : Optional[str] = None
    año : Optional[str] = None
    activo : Optional[bool] = None

class VehiculoResponse(BaseModel):
    codigo: int
    modelo: str
    placa: str
    marca: str
    año: str
    activo: bool
    id_usuario: str
    class Config: 
        from_attributes = True

