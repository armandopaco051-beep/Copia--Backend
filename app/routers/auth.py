from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.seguridad import Usuario
from app.schemas.usuario import (
    UsuarioCreate, UsuarioResponse, LoginRequest,
    Token, RecuperarPasswordRequest, CambiarPasswordRequest

)

from app.services.auth_service import (
    hash_password, verify_password, create_access_token , get_permisos_usuario, registrar_bitacora
    )

from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Autenticación - CU01 al CU04"])



def build_usuario_response(usuario : Usuario, db :Session) -> dict : 
    "Construye la respuesta del usuario con rol y permisos "
    permisos  = get_permisos_usuario(db,usuario.id_rol)
    nombre_rol = usuario.rol.nombre if usuario.rol else ""
    return {
        "codigo": usuario.codigo,
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "email": usuario.email,
        "telefono": usuario.telefono,
        "fecha_registro": usuario.fecha_registro,
        "id_rol": usuario.id_rol,
        "estado": usuario.estado,
        "nombre_rol": nombre_rol,
        "permisos": permisos

    }

# CU-01 Registrar usuario

@router.post("/registro", response_model=UsuarioResponse, status_code=201)
def registrar_usuario(datos: UsuarioCreate,request : Request ,db: Session = Depends(get_db)):
      # Verificar CI único
    if db.query(Usuario).filter(Usuario.codigo == datos.codigo).first():
        raise HTTPException(status_code=400, detail="El CI ya está registrado")
    # Verificar email único
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    # Regla: admin_taller debe tener taller asignado
    if datos.id_rol == 2 and not datos.codigo_taller:
        raise HTTPException(
            status_code=400,
            detail="El Admin Taller debe estar vinculado a un taller")
    nuevo = Usuario(
        codigo=datos.codigo,
        nombre=datos.nombre,
        apellido=datos.apellido,
        email=datos.email,
        password=hash_password(datos.password),
        telefono=datos.telefono,
        id_rol=datos.id_rol,
        estado=True,
        fecha_registro=datetime.now()
    )
    db.add(nuevo)
    db.flush()
    # Si es admin_taller vincular al taller
    if datos.id_rol == 2 and datos.codigo_taller:
        asignacion = TallerUsuario(
            id_usuario=datos.codigo,
            codigo_taller=datos.codigo_taller,
            fecha_asignacion=datetime.now()
        )
        db.add(asignacion)
    db.commit()
    db.refresh(nuevo)
    registrar_bitacora(
        db, datos.codigo, "REGISTRO_USUARIO",
        "AUTH", f"Usuario {datos.email} registrado con rol {datos.id_rol}",
        request.client.host if request.client else None

    )
    return build_usuario_response(nuevo, db)



# CU-02 Login

@router.post("/login", response_model=Token)
def login(datos: LoginRequest, request: Request, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario or not verify_password(datos.password, usuario.password):
        raise HTTPException(status_code=401, detail="Email o password incorrectos")
    if not usuario.estado:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    if usuario.id_rol == 4:
        user_agent = request.headers.get("user-agent", "").lower()
        if "flutter" in user_agent or "dart" in user_agent:
            pass  # Permitir acceso desde Flutter
        else:
            raise HTTPException(status_code=403, detail="Usuario no autorizado entrar desde el movil")
    permisos = get_permisos_usuario(db,usuario.id_rol)
    token = create_access_token({"sub": str(usuario.codigo), "rol": usuario.id_rol , "permisos": permisos})
    registrar_bitacora(
        db , usuario.codigo, "LOGIN", "AUTH", "Login exitoso", request.client.host
         if request.client else None
    )
    return {"access_token": token, "token_type": "bearer", "usuario": build_usuario_response(usuario, db)}





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
    if datos.new_password != datos.confirm_password:
        raise HTTPException(status_code=400, detail="Las contraseñas no coinciden")
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.password = hash_password(datos.new_password)
    db.commit()
    db.refresh(usuario)
    return {"mensaje": "Password actualizada correctamente"}





# CU-04 Cerrar sesión

@router.post("/logout")
def logout():
    return {"mensaje": "Sesión cerrada correctamente"}

    