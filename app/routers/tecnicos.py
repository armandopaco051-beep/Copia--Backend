from fastapi import APIRouter, Depends, HTTPException, status , Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from jose import jwt, JWTError
from app.services.auth_service import registrar_bitacora
from app.database import get_db
from app.models.talleres import Tecnico, Taller
from app.models.seguridad import Usuario
from app.schemas.tecnico import (
    TecnicoCreate,
    TecnicoUpdate,
    TecnicoResponse,
    TecnicoLoginRequest ,
    TecnicoCreateAdminTaller
)
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.config import settings

router = APIRouter(prefix="/tecnicos", tags=["Técnicos"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_usuario(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido"
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        codigo: str = payload.get("sub")
        if codigo is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    usuario = db.query(Usuario).filter(Usuario.codigo == codigo).first()
    if not usuario:
        raise credentials_exception

    return usuario


def get_taller_admin(usuario: Usuario, db: Session):
    taller = db.query(Taller).filter(Taller.usuario_id == usuario.codigo).first()
    if not taller:
        raise HTTPException(status_code=404, detail="No tienes un taller asociado")
    return taller


# =========================
# LOGIN TÉCNICO
# =========================

@router.post("/login")
def login_tecnico(datos: TecnicoLoginRequest, db: Session = Depends(get_db)):
    tecnico = db.query(Tecnico).filter(Tecnico.email == datos.email).first()

    if not tecnico or not verify_password(datos.password, tecnico.password):
        raise HTTPException(status_code=401, detail="CI o contraseña incorrectos")

    token = create_access_token({
        "sub": tecnico.codigo,
        "tipo": "tecnico",
        "rol": tecnico.id_rol
    })
    registrar_bitacora(
    db=db,
    codigo_usuario=None,
    codigo_tecnico=tecnico.codigo,
    id_taller=tecnico.id_taller,
    accion="LOGIN_TECNICO",
    modulo="TECNICOS",
    descripcion=f"Inicio de sesión del técnico {tecnico.codigo}",
    ip_address=request.client.host if request.client else None
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "tecnico": {
            "codigo": tecnico.codigo,
            "nombre": tecnico.nombre,
            "email": tecnico.email,
            "id_taller": tecnico.id_taller,
            "id_rol": tecnico.id_rol
        }
    }


# =========================
# ADMIN TALLER - SOLO SU TALLER
# =========================

@router.get("/mis-tecnicos", response_model=List[TecnicoResponse])
def listar_mis_tecnicos(
    usuario: Usuario = Depends(get_current_usuario),
    db: Session = Depends(get_db)
):
    if usuario.id_rol != 2:
        raise HTTPException(status_code=403, detail="No autorizado")

    taller = get_taller_admin(usuario, db)
    return db.query(Tecnico).filter(Tecnico.id_taller == taller.codigo).all()


@router.post("/mis-tecnicos", response_model=TecnicoResponse, status_code=201)
def crear_mi_tecnico(
    datos: TecnicoCreateAdminTaller,
    usuario: Usuario = Depends(get_current_usuario),
    db: Session = Depends(get_db),
    request: Request = None
):
    if usuario.id_rol != 2:
        raise HTTPException(status_code=403, detail="No autorizado")

    taller = get_taller_admin(usuario, db)

    existe_codigo = db.query(Tecnico).filter(Tecnico.codigo == datos.codigo).first()
    if existe_codigo:
        raise HTTPException(status_code=400, detail="El CI ya está registrado")

    email_ci = datos.codigo.strip()

    existe_email = db.query(Tecnico).filter(Tecnico.email == email_ci).first()
    if existe_email:
        raise HTTPException(status_code=400, detail="El acceso del técnico ya está registrado")

    nuevo_tecnico = Tecnico(
        codigo=datos.codigo.strip(),
        nombre=datos.nombre.strip(),
        email=email_ci,
        password=hash_password(email_ci),
        telefono=datos.telefono.strip(),
        disponibilidad=datos.disponibilidad,
        latitud=float(taller.latitud),
        longitud=float(taller.longitud),
        id_taller=taller.codigo,
        id_rol=3
    )

    db.add(nuevo_tecnico)
    db.commit()
    db.refresh(nuevo_tecnico)
    registrar_bitacora(
        db,
        usuario.codigo,
        "Crear Tecnico",
        "Tecnicos",
        f"Se creo el tecnico{nuevo_tecnico.nombre} con Ci{ nuevo_tecnico.codigo} en el Taller{taller.codigo}",
        request.client.host if request.client else "None",  codigo_tecnico = nuevo_tecnico.codigo, id_taller = taller.codigo
    )
    return nuevo_tecnico


@router.patch("/mis-tecnicos/{codigo}", response_model=TecnicoResponse)
def actualizar_mi_tecnico(
    codigo: str,
    datos: TecnicoUpdate,
    usuario: Usuario = Depends(get_current_usuario),
    db: Session = Depends(get_db),
    request: Request = None
):
    if usuario.id_rol != 2:
        raise HTTPException(status_code=403, detail="No autorizado")

    taller = get_taller_admin(usuario, db)

    tecnico = db.query(Tecnico).filter(
        Tecnico.codigo == codigo,
        Tecnico.id_taller == taller.codigo
    ).first()

    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado en tu taller")

    datos_dict = datos.model_dump(exclude_unset=True)
    datos_dict.pop("id_taller", None)

    for campo, valor in datos_dict.items():
        setattr(tecnico, campo, float(valor) if campo in ["latitud", "longitud"] else valor)

    db.commit()
    db.refresh(tecnico)
    if "disponibilidad" in datos_dict and disponibilidad_anterior != tecnico.disponibilidad:
        registrar_bitacora(
            db,
            usuario.codigo,
            "CAMBIAR_DISPONIBILIDAD",
            "TECNICOS",
            f"Se cambió la disponibilidad del técnico {tecnico.codigo} a {'Disponible' if tecnico.disponibilidad else 'Ocupado'}",
            request.client.host if request.client else None
        )
    else:
        registrar_bitacora(
            db,
            usuario.codigo,
            "EDITAR_TECNICO",
            "TECNICOS",
            f"Se actualizó el técnico {tecnico.nombre} con CI {tecnico.codigo}",
            request.client.host if request.client else None,
            codigo_tecnico=tecnico.codigo,
            id_taller=taller.codigo
        )
    return tecnico


@router.delete("/mis-tecnicos/{codigo}")
def eliminar_mi_tecnico(
    codigo: str,
    usuario: Usuario = Depends(get_current_usuario),
    db: Session = Depends(get_db),
    request: Request = None
):
    if usuario.id_rol != 2:
        raise HTTPException(status_code=403, detail="No autorizado")

    taller = get_taller_admin(usuario, db)

    tecnico = db.query(Tecnico).filter(
        Tecnico.codigo == codigo,
        Tecnico.id_taller == taller.codigo
    ).first()

    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado en tu taller")

    db.delete(tecnico)
    db.commit()
    registrar_bitacora(
        db, usuario.codigo, "Eliminar Tecnico", "Tecnicos", f"Se elimino el tecnico {tecnico.nombre} con CI {tecnico.codigo}",
        request.client.host if request.client else "None",
        codigo_tecnico=tecnico.codigo,
        id_taller=taller.codigo
    )
    return {"mensaje": "Técnico eliminado"}


# =========================
# ADMIN PLATAFORMA - GLOBAL
# =========================

@router.post("/crear", response_model=TecnicoResponse, status_code=201)
def crear_tecnico(datos: TecnicoCreate, db: Session = Depends(get_db)):
    existe_codigo = db.query(Tecnico).filter(Tecnico.codigo == datos.codigo).first()
    if existe_codigo:
        raise HTTPException(status_code=400, detail="El CI ya está registrado")

    email_ci = datos.codigo.strip()

    existe_email = db.query(Tecnico).filter(Tecnico.email == email_ci).first()
    if existe_email:
        raise HTTPException(status_code=400, detail="El acceso del técnico ya está registrado")

    taller = db.query(Taller).filter(Taller.codigo == datos.id_taller).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")

    nuevo_tecnico = Tecnico(
        codigo=datos.codigo.strip(),
        nombre=datos.nombre.strip(),
        email=email_ci,
        password=hash_password(email_ci),
        telefono=datos.telefono.strip(),
        disponibilidad=datos.disponibilidad,
        latitud=float(datos.latitud),
        longitud=float(datos.longitud),
        id_taller=datos.id_taller,
        id_rol=3
    )

    db.add(nuevo_tecnico)
    db.commit()
    db.refresh(nuevo_tecnico)
    return nuevo_tecnico


@router.get("/taller/{id_taller}", response_model=List[TecnicoResponse])
def listar_por_taller(id_taller: int, db: Session = Depends(get_db)):
    return db.query(Tecnico).filter(Tecnico.id_taller == id_taller).all()


@router.get("/{codigo}", response_model=TecnicoResponse)
def obtener_tecnico(codigo: str, db: Session = Depends(get_db)):
    tecnico = db.query(Tecnico).filter(Tecnico.codigo == codigo).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    return tecnico


@router.patch("/{codigo}", response_model=TecnicoResponse)
def actualizar_tecnico(codigo: str, datos: TecnicoUpdate, db: Session = Depends(get_db)):
    tecnico = db.query(Tecnico).filter(Tecnico.codigo == codigo).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(tecnico, campo, float(valor) if campo in ["latitud", "longitud"] else valor)

    db.commit()
    db.refresh(tecnico)
    return tecnico


@router.delete("/{codigo}")
def eliminar_tecnico(codigo: str, db: Session = Depends(get_db)):
    tecnico = db.query(Tecnico).filter(Tecnico.codigo == codigo).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    db.delete(tecnico)
    db.commit()
    return {"mensaje": "Técnico eliminado"}
    db.commit()
    return {"mensaje": "Técnico eliminado"} 