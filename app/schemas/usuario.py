import email
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class Rol_base(BaseModel):
    nombre : str 
    
class RolCreate(Rol_base):
    pass

class RolResponse(Rol_base):
    id: int
    
    class Config:
        from_attributes = True

class PermisoBase(BaseModel):
    id :str
    nombre: str
    
class PermisoCreate(PermisoBase):
    pass

class PermisoResponse(PermisoBase):
    id: int
    
    class Config:
        from_attributes = True

class UsuarioCreate(BaseModel):
    codigo: str
    nombre: str
    apellido : str 
    email: EmailStr
    password: str
    telefono :str 
    id_rol : int 
    
class UsuarioResponse(BaseModel):
   codigo : str 
   nombre : str 
   apellido :str 
   email :EmailStr
   telefono : str 
   estado : bool
   fecha_registro : datetime 
   id_rol : int 
   class Config : 
        from_attributes = True

class UsuarioUpdate(BaseModel): 
    nombre : Optional[str] = None
    apellido : Optional[str] = None
    telefono : Optional[str] = None
    email : Optional[EmailStr] = None
    estado : Optional[bool] = None
    id_rol: Optional[int] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel): 
    access_token: str
    token_type: str
    usuario: UsuarioResponse

class RecuperarPasswordRequest(BaseModel): 
    email : EmailStr

class CambiarPasswordRequest(BaseModel): 
    email : EmailStr
    new_password: str
    confirm_password: str