from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.seguridad import Usuario
from app.schemas.usuario import (
    UsuarioCreate, UsuarioResponse, LoginRequest,
    Token, RecuperarPasswordRequest, CambiarPasswordRequest
)
from app.services.auth_service import (hash_password, verify_password, create_access_token)
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Autenticación - CU01 al CU04"])


# CU-01 Registrar usuario
@router.post("/registro", response_model=UsuarioResponse, status_code=201)
def registrar_usuario(datos: UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    nuevo = Usuario(
        codigo = datos.codigo,
        nombre=datos.nombre,
        apellido=datos.apellido,
        email=datos.email,
        password=hash_password(datos.password),
        telefono=datos.telefono,
        fecha_registro=datetime.now(),
        id_rol=datos.id_rol,
        estado=True
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


# CU-02 Login
@router.post("/login", response_model=Token)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario or not verify_password(datos.password, usuario.password):
        raise HTTPException(status_code=401, detail="Email o password incorrectos")
    if not usuario.estado:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    token = create_access_token({"sub": str(usuario.codigo), "rol": usuario.id_rol})
    return {"access_token": token, "token_type": "bearer", "usuario": usuario}


# CU-03 Recuperar contraseña
@router.post("/recuperar-password")
def recuperar_password(datos: RecuperarPasswordRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="No existe cuenta con ese email")
    return {"mensaje": f"Correo de recuperación enviado a {datos.email}"}


# CU-03 Cambiar contraseña
@router.put("/cambiar-password")
def cambiar_password(datos: CambiarPasswordRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.password = hash_password(datos.new_password)
    db.commit()
    return {"mensaje": "Password actualizada correctamente"}


# CU-04 Cerrar sesión
@router.post("/logout")
def logout():
    return {"mensaje": "Sesión cerrada correctamente"}
    