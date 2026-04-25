from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.seguridad import Usuario
from app.schemas.usuario import (
    UsuarioCreate, UsuarioResponse, LoginRequest,
    Token, RecuperarPasswordRequest, CambiarPasswordRequest

)
from app.schemas.taller import TallerCreate
from app.models.talleres import Taller

from app.services.auth_service import (
    hash_password, verify_password, create_access_token , get_permisos_usuario, registrar_bitacora
    )

from datetime import datetime
from fastapi.security import OAuth2PasswordRequestForm

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
    id_taller_bitacora = None
    accion_bitacora = "LOGIN_USUARIO"
    modulo_bitacora = "USUARIOS"

    if usuario.id_rol == 1:
        accion_bitacora = "LOGIN_ADMIN_PLATAFORMA"
        modulo_bitacora = "USUARIOS"

    elif usuario.id_rol == 2:
        accion_bitacora = "LOGIN_ADMIN_TALLER"
        modulo_bitacora = "TALLERES"
    elif usuario.id_rol == 4:
        accion_bitacora = "LOGIN_CLIENTE"
        modulo_bitacora = "CLIENTES"
    print(Taller.__table__.columns.keys())
    taller = db.query(Taller).filter(Taller.usuario_id == usuario.codigo).first()
    if taller:
        id_taller_bitacora = taller.codigo

    registrar_bitacora(
    db=db,
    codigo_usuario=usuario.codigo,
    accion=accion_bitacora,
    modulo=modulo_bitacora,
    descripcion=f"Inicio de sesión del usuario {usuario.codigo}",
    ip_address=request.client.host if request.client else None,
    id_taller=id_taller_bitacora
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

 # el admin_crea un usuario en gestion de usuario 
@router.post("/registro-admin-taller/usuario")
def registrar_usuario_admin_taller(datos: dict, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.codigo == datos["codigo"]).first()
    if existe:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    nuevo_usuario = Usuario(
        codigo=datos["codigo"],
        nombre=datos["nombre"],
        apellido=datos["apellido"],
        email=datos["email"],
        password=hash_password(datos["password"]),
        telefono=datos["telefono"],
        id_rol=2,   # admin_taller
        estado=True,
        fecha_registro=datetime.now()
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {
        "mensaje": "Usuario admin_taller creado",
        "codigo_usuario": nuevo_usuario.codigo
    }
    
# el admin_crea un taller en gestion de taller 
@router.post("/registro-admin-taller/taller/{codigo_usuario}")
def registrar_taller_para_admin(
    codigo_usuario: str,
    datos: TallerCreate,
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.codigo == codigo_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    nuevo_taller = Taller(
        nombre=datos.nombre,
        telefono=datos.telefono,
        direccion=datos.direccion,
        latitud=datos.latitud,
        longitud=datos.longitud,
        activo=True,
        estado_registro="aprobado",
        horario_inicio=datos.horario_inicio,
        horario_fin=datos.horario_fin,
        usuario_id=usuario.codigo
    )

    db.add(nuevo_taller)
    db.commit()
    db.refresh(nuevo_taller)

    return {
        "mensaje": "Taller creado correctamente",
        "codigo_taller": nuevo_taller.codigo,
        "codigo_usuario": codigo_usuario
    }

# LOGIN PARA ANGULAR / FRONTEND
@router.post("/token", response_model=Token)
def login_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()

    if not usuario or not verify_password(form_data.password, usuario.password):
        raise HTTPException(status_code=401, detail="Email o password incorrectos")

    return _hacer_login(usuario, request, db)
