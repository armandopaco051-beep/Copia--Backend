from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models.operaciones import Incidente, Asignacion
from app.models.talleres import Taller, Tecnico
from app.services.auth_service import registrar_bitacora
import math
from app.schemas.asignacion import ResponderAsignacion, AsignacionCreate, AsignarTecnicoRequest

from app.models.seguridad import Usuario
router =  APIRouter(prefix="/asignacion", tags=["Asignacion"])

def calcular_distancia(lat1, lon1, lat2, lon2) -> float:
    """Distancia en km con fórmula de Haversine"""
    R = 6371
    d_lat = math.radians(float(lat2) - float(lat1))
    d_lon = math.radians(float(lon2) - float(lon1))
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(float(lat1))) *
         math.cos(math.radians(float(lat2))) *
         math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
# ✅ CAMBIO: busca el siguiente taller más cercano que todavía NO recibió ese incidente
def asignar_siguiente_taller(db: Session, incidente: Incidente):
    """
    Busca el taller más cercano disponible que aún no haya recibido
    este incidente. Crea una asignación pendiente para ese taller.
    """
 # evitar crear otra asignación si ya hay una pendiente/aceptada/asignada
    asignacion_activa = db.query(Asignacion).filter(
        Asignacion.id_incidente == incidente.codigo,
        Asignacion.id_estado_asignacion.in_([1, 2, 4, 5])
    ).first()

    if asignacion_activa:
        return asignacion_activa

    # talleres que ya recibieron este incidente
    talleres_ya_intentados = db.query(Asignacion.id_taller).filter(
        Asignacion.id_incidente == incidente.codigo
    ).all()

    ids_excluidos = [t[0] for t in talleres_ya_intentados]

    # buscar talleres activos, aprobados y con ubicación
    query = db.query(Taller).filter(
        Taller.activo == True,
        Taller.latitud.isnot(None),
        Taller.longitud.isnot(None)
    )

    #  si tu tabla tiene estado_registro, usamos solo aprobados
    query = query.filter(Taller.estado_registro == "aprobado")

    if ids_excluidos:
        query = query.filter(~Taller.codigo.in_(ids_excluidos))

    talleres = query.all()

    if not talleres:
        return None

    # ordenar por distancia al incidente
    talleres_ordenados = sorted(
        talleres,
        key=lambda t: calcular_distancia(
            incidente.latitud,
            incidente.longitud,
            t.latitud,
            t.longitud
        )
    )

    taller_elegido = talleres_ordenados[0]

    distancia = calcular_distancia(
        incidente.latitud,
        incidente.longitud,
        taller_elegido.latitud,
        taller_elegido.longitud
    )

    # crear solicitud pendiente para el taller más cercano
    nueva_asignacion = Asignacion(
        fecha_asignacion=datetime.now(),
        fecha_aceptacion=None,
        tiempo=str(round(distancia, 2)),
        observacion="Solicitud pendiente de aceptación por el taller",
        id_incidente=incidente.codigo,
        id_tecnico=None,              # ✅ Todavía no hay técnico
        id_taller=taller_elegido.codigo,
        id_estado_asignacion=1        # ✅ 1 = Pendiente
    )

    db.add(nueva_asignacion)
    db.flush()

    return nueva_asignacion

@router.get("/candidatos/{id_incidente}")
def obtener_candidatos(id_incidente: int ,  db: Session = Depends(get_db)): 
    #Cu17 motor de asignacion inteligente retorna lista de tecnicos candidatos
    incidente = db.query(Incidente).filter(Incidente.codigo == id_incidente).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    talleres_activos = db.query(Taller).filter(Taller.activo == True).all()
    candidatos=[] 
    for taller in talleres_activos: 
        #tecnicos disponible
        tecnicos_disponible = db.query(Tecnico).filter(Tecnico.id_taller == taller.codigo, Tecnico.disponibilidad == True).all()
        if not tecnicos_disponible: 
            continue 
        #calcular las distancia 
        distancia  = calcular_distancia(
            incidente.latitud, incidente.longitud, taller.latitud, taller.longitud 
        )
        #Score menor distancia = mayor Score 
        #prioridad alta de suma de puntos
        score_distancia = max(0,100 - distancia * 5 )
        bonus_prioridad = 20 if incidente.id_prioridad == 1 else 0
        bonus_tecnicos = min (20, len(tecnicos_disponible)*5)
        score_total = score_distancia + bonus_prioridad + bonus_tecnicos
        candidatos.append({
            "taller": { 
                "codigo" : taller.codigo,
                "nombre": taller.nombre,
                "telefono" : taller.telefono,
                "direccion" : taller.direccion
                
            },
            "distancia_km" : round(distancia,2),
            "tecnicos_disponible" : len(tecnicos_disponible),
            "tecnico":[{
                "codigo" : t.codigo,
                "telefono" : t.telefono,
                "disponibilidad" : t.disponibilidad
            } for t in tecnicos_disponible],
            "score": round(score_total,1),
            "recomendado" : False 
        })
        #ordenar por score 
        #que hace la linea 73 ? respuesta : ordena la lista de candidatos por score en orden descendente
        
    candidatos.sort(key = lambda x: x["score"], reverse=True)
    #marca el mejor candidato
    if candidatos : 
        candidatos[0]["recomendado"] = True
    return {
    "id_incidente":  id_incidente,
    "total_candidatos" : len(candidatos), 
    "candidatos": candidatos[:5] #top 5 significa ? respuesta : los primeros 5 candidatos de la lista ordenada por score
    
    }
@router.post("/auto/{id_incidente}", status_code=201)
def crear_asignacion_automatica(
    id_incidente: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Crea una asignación automática para que el taller más cercano
    reciba la solicitud del incidente.
    """

    # 1. Buscar incidente
    incidente = db.query(Incidente).filter(
        Incidente.codigo == id_incidente
    ).first()

    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    # 2. Evitar asignaciones duplicadas para el mismo incidente
    asignacion_existente = db.query(Asignacion).filter(
        Asignacion.id_incidente == id_incidente
    ).first()

    if asignacion_existente:
        return {
            "mensaje": "El incidente ya tiene una asignación",
            "id_asignacion": asignacion_existente.id,
            "id_taller": asignacion_existente.id_taller,
            "id_estado_asignacion": asignacion_existente.id_estado_asignacion
        }

    # 3. Buscar talleres activos con ubicación
    talleres = db.query(Taller).filter(
        Taller.activo == True,
        Taller.latitud.isnot(None),
        Taller.longitud.isnot(None)
    ).all()

    if not talleres:
        raise HTTPException(
            status_code=404,
            detail="No hay talleres activos disponibles"
        )

    candidatos = []

    # 4. Calcular distancia y verificar técnicos disponibles
    for taller in talleres:
        tecnicos_disponibles = db.query(Tecnico).filter(
            Tecnico.id_taller == taller.codigo,
            Tecnico.disponibilidad == True
        ).all()

        # Si quieres que solo reciban talleres con técnicos disponibles,
        # deja este continue. Si quieres que cualquier taller activo reciba,
        # puedes quitar este bloque.
        if not tecnicos_disponibles:
            continue

        distancia = calcular_distancia(
            incidente.latitud,
            incidente.longitud,
            taller.latitud,
            taller.longitud
        )

        candidatos.append({
            "taller": taller,
            "distancia": distancia,
            "tecnicos_disponibles": len(tecnicos_disponibles)
        })

    if not candidatos:
        raise HTTPException(
            status_code=404,
            detail="No hay talleres con técnicos disponibles"
        )

    # 5. Elegir el taller más cercano
    candidatos.sort(key=lambda x: x["distancia"])
    mejor = candidatos[0]
    taller_elegido = mejor["taller"]

    # 6. Crear asignación PENDIENTE para el taller
    nueva = Asignacion(
        fecha_asignacion=datetime.now(),
        fecha_aceptacion=None,
        tiempo=round(mejor["distancia"] * 3),  # estimación simple en minutos
        observacion="Asignación automática pendiente de aceptación por el taller",
        id_incidente=incidente.codigo,
        id_tecnico=None,  # todavía no se asigna técnico
        id_taller=taller_elegido.codigo,
        id_estado_asignacion=1  # pendiente
    )

    db.add(nueva)

    # 7. Cambiar estado del incidente a "en revisión" o "en proceso"
    incidente.id_estado_incidente = 2

    registrar_bitacora(
        db=db,
        codigo_usuario=incidente.codigo_usuario,
        accion="ASIGNACION_AUTOMATICA_TALLER",
        modulo="ASIGNACION",
        descripcion=f"Incidente {incidente.codigo} enviado al taller {taller_elegido.codigo}",
        ip_address=request.client.host if request.client else None,
        id_taller=taller_elegido.codigo
    )

    db.commit()
    db.refresh(nueva)

    return {
        "mensaje": "Incidente enviado al taller más cercano",
        "id_asignacion": nueva.id,
        "id_incidente": incidente.codigo,
        "id_taller": taller_elegido.codigo,
        "nombre_taller": taller_elegido.nombre,
        "distancia_km": round(mejor["distancia"], 2),
        "id_estado_asignacion": nueva.id_estado_asignacion
    }

@router.post("", status_code=201)
def crear_asignacion(
    datos: AsignacionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """CU-19: Asignar técnico a orden de trabajo"""
    incidente = db.query(Incidente).filter(
        Incidente.codigo == datos.id_incidente).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    nueva = Asignacion(
        fecha_asignacion=datetime.now(),
        fecha_aceptacion=datetime.now(),
        tiempo=datos.tiempo_estimado,
        observacion=datos.observacion,
        id_incidente=datos.id_incidente,
        id_tecnico=datos.id_tecnico,
        id_taller=datos.id_taller,
        id_estado_asignacion=1  # pendiente
    )
    db.add(nueva)

    # Actualizar estado del incidente a "en proceso"
    incidente.id_estado_incidente = 2

    # Marcar técnico como no disponible
    tecnico = db.query(Tecnico).filter(
        Tecnico.codigo == datos.id_tecnico).first()
    if tecnico:
        tecnico.disponibilidad = False
    registrar_bitacora(
        db=db,
        codigo_usuario=incidente.codigo_usuario,
        accion="ASIGNACION_AUTOMATICA",
        modulo="ASIGNACION",
        descripcion=f"Incidente {incidente.codigo} asignado automáticamente al taller {datos.id_taller}",
        ip_address=request.client.host if request.client else None,
        id_taller=datos.id_taller
    )
    db.commit()
    db.refresh(nueva)


    return {
        "id_asignacion": nueva.id,
        "mensaje": "Técnico asignado correctamente",
        "estado": "pendiente"
    }


@router.put("/{id_asignacion}/aceptar")
def aceptar_asignacion(
    id_asignacion: int,
    db: Session = Depends(get_db)
):
    asignacion = db.query(Asignacion).filter(
        Asignacion.id == id_asignacion
    ).first()

    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    if asignacion.id_estado_asignacion != 1:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede aceptar una solicitud pendiente"
        )

    # ✅ CAMBIO:
    # El taller acepta, pero todavía NO se asigna técnico.
    asignacion.id_estado_asignacion = 2  # 2 = Aceptada
    asignacion.fecha_aceptacion = datetime.now()
    asignacion.observacion = "Solicitud aceptada por el taller"

    db.commit()
    db.refresh(asignacion)

    return {
        "mensaje": "Solicitud aceptada correctamente",
        "id_asignacion": asignacion.id,
        "id_incidente": asignacion.id_incidente,
        "id_taller": asignacion.id_taller,
        "estado": asignacion.id_estado_asignacion
    }
@router.put("/{id_asignacion}/rechazar")
def rechazar_asignacion(
    id_asignacion: int,
    payload: dict,
    db: Session = Depends(get_db)
):
    asignacion = db.query(Asignacion).filter(
        Asignacion.id == id_asignacion
    ).first()

    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    if asignacion.id_estado_asignacion != 1:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede rechazar una solicitud pendiente"
        )

    observacion = payload.get(
        "observacion",
        "Solicitud rechazada por el taller"
    )

    # ✅ CAMBIO: marcar la asignación actual como rechazada
    asignacion.id_estado_asignacion = 3  # 3 = Rechazada
    asignacion.observacion = observacion

    incidente = db.query(Incidente).filter(
        Incidente.codigo == asignacion.id_incidente
    ).first()

    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    # ✅ CAMBIO:
    # Buscar siguiente taller más cercano que aún no haya recibido este incidente.
    nueva_asignacion = asignar_siguiente_taller(db, incidente)

    if not nueva_asignacion:
        # ✅ CAMBIO: no hay más talleres disponibles
        db.commit()

        return {
            "mensaje": "Solicitud rechazada. No hay más talleres disponibles.",
            "sin_taller_disponible": True,
            "id_incidente": incidente.codigo
        }

    db.commit()
    db.refresh(nueva_asignacion)

    return {
        "mensaje": "Solicitud rechazada. Se envió al siguiente taller cercano.",
        "sin_taller_disponible": False,
        "nueva_asignacion": {
            "id": nueva_asignacion.id,
            "id_incidente": nueva_asignacion.id_incidente,
            "id_taller": nueva_asignacion.id_taller,
            "id_estado_asignacion": nueva_asignacion.id_estado_asignacion
        }
    }

@router.get("/taller/{id_taller}")
def asignaciones_del_taller(
    id_taller: int,
    db: Session = Depends(get_db)
):
    """Lista las asignaciones activas de un taller"""

    # ❌ ANTES:
    # asignaciones = db.query(Asignacion).filter(
    #     Asignacion.id_taller == id_taller
    # ).order_by(Asignacion.fecha_asignacion.desc()).all()

    # ✅ CAMBIO:
    # Mostramos solo solicitudes activas del taller:
    # 1 pendiente, 2 aceptada, 4 asignada a técnico, 5 en camino
    asignaciones = db.query(Asignacion).filter(
        Asignacion.id_taller == id_taller,
        Asignacion.id_estado_asignacion.in_([1, 2, 4, 5])
    ).order_by(Asignacion.fecha_asignacion.desc()).all()

    resultado = []

    for a in asignaciones:
        inc = db.query(Incidente).filter(
            Incidente.codigo == a.id_incidente
        ).first()

        usuario = None

        # ✅ CAMBIO: buscamos el cliente que reportó el incidente
        if inc:
            usuario = db.query(Usuario).filter(
                Usuario.codigo == inc.codigo_usuario
            ).first()

        resultado.append({
            "id": a.id,
            "id_incidente": a.id_incidente,
            "id_tecnico": a.id_tecnico,
            "id_estado_asignacion": a.id_estado_asignacion,
            "fecha_asignacion": a.fecha_asignacion,
            "fecha_aceptacion": a.fecha_aceptacion,
            "tiempo": a.tiempo,
            "observacion": a.observacion,
            "incidente": {
                "descripcion": inc.descripcion if inc else "",
                "latitud": float(inc.latitud) if inc else 0,
                "longitud": float(inc.longitud) if inc else 0,
                "id_categoria": inc.id_categoria_problema if inc else 0,
                "id_prioridad": inc.id_prioridad if inc else 0,

                # ✅ CAMBIO: datos del cliente para el modal de detalle
                "usuario": {
                    "codigo": usuario.codigo if usuario else "",
                    "nombre": usuario.nombre if usuario else "",
                    "apellido": usuario.apellido if usuario else "",
                    "telefono": usuario.telefono if usuario else "",
                    "email": usuario.email if usuario else "",
                }
            } if inc else {}
        })

    return resultado

@router.put("/{id_asignacion}/tecnico/{codigo_tecnico}")
def asignar_tecnico_a_asignacion(
    id_asignacion: int,
    datos: AsignarTecnicoRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    asignacion = db.query(Asignacion).filter(Asignacion.id == id_asignacion).first()
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    if asignacion.id_estado_asignacion != 2:
        raise HTTPException(
            status_code=400,
            detail="Primero el taller debe aceptar la asignación"
        )

    tecnico = db.query(Tecnico).filter(
        Tecnico.codigo == datos.codigo_tecnico,
        Tecnico.id_taller == asignacion.id_taller,
        Tecnico.disponibilidad == True
    ).first()

    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado en este taller")

    if not tecnico.disponibilidad:
        raise HTTPException(status_code=400, detail="El técnico no está disponible")

    asignacion.id_tecnico = tecnico.codigo
    asignacion.id_estado_asignacion = 4  # asignada_tecnico
    asignacion.observacion = datos.observacion

    tecnico.disponibilidad = False

    registrar_bitacora(
        db=db,
        codigo_usuario=None,
        codigo_tecnico=tecnico.codigo,
        accion="ASIGNAR_TECNICO",
        modulo="ASIGNACION",
        descripcion=f"Se asignó el técnico {tecnico.codigo} a la asignación {asignacion.id}",
        ip_address=request.client.host if request.client else None,
        id_taller=asignacion.id_taller
    )

    db.commit()

    return {
        "mensaje": "Técnico asignado correctamente",
        "id_asignacion": asignacion.id,
        "id_tecnico": tecnico.codigo
    }
@router.put("/{id_asignacion}/iniciar-ruta")
def iniciar_ruta(
    id_asignacion: int ,
    request : Request,
    db: Session= Depends(get_db)
): 
    asignacion = db.query(Asignacion).filter(Asignacion.id == id_asignacion).first() 
    if not asignacion: 
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    if asignacion.id_estado_asignacion != 4:
        raise HTTPException(status_code=400, detail="La asignación no está en estado 'asignada_tecnico'")
    
    asignacion.id_estado_asignacion = 5  # en_ruta
    asignacion.observacion = "Tecnico en camino al Cliente";

    incidente = db.query(Incidente).filter(Incidente.codigo == asignacion.id_incidente).first()

    if incidente: 
        #ajusta este numero segun tu catologo de estado de incidente
        incidente.id_estado_incidente=2

    registrar_bitacora(
        db=db,
        codigo_usuario=None,
        codigo_tecnico=asignacion.id_tecnico,
        accion="INICIAR_RUTA",
        modulo="ASIGNACION",
        descripcion=f"Se inició la ruta para la asignación {asignacion.id}",
        ip_address=request.client.host if request.client else None,
        id_taller=asignacion.id_taller
    )

    db.commit()
    db.refresh(asignacion)

    return {
        "mensaje": "Ruta iniciada correctamente",
        "id_asignacion": asignacion.id
    }

@router.put("/{id_asignacion}/finalizar")
def finalizar_servicio(
    id_asignacion: int,
    request: Request,
    db: Session = Depends(get_db)
):
    asignacion = db.query(Asignacion).filter(
        Asignacion.id == id_asignacion
    ).first()

    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    if asignacion.id_estado_asignacion not in [4, 5]:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede finalizar una asignación activa"
        )

    tecnico = db.query(Tecnico).filter(
        Tecnico.codigo == asignacion.id_tecnico
    ).first()

    incidente = db.query(Incidente).filter(
        Incidente.codigo == asignacion.id_incidente
    ).first()

    asignacion.id_estado_asignacion = 6
    asignacion.observacion = "Servicio finalizado por el técnico"

    if tecnico:
        tecnico.disponibilidad = True

    if incidente:
        # Ajusta este número según tu catálogo de estado_incidente
        incidente.id_estado_incidente = 4
        incidente.fecha_cierre = datetime.now()

    registrar_bitacora(
        db=db,
        codigo_usuario=None,
        codigo_tecnico=asignacion.id_tecnico,
        id_taller=asignacion.id_taller,
        accion="FINALIZAR_SERVICIO",
        modulo="ASIGNACION",
        descripcion=f"El técnico finalizó la asignación {asignacion.id}",
        ip_address=request.client.host if request.client else None
    )

    db.commit()
    db.refresh(asignacion)

    return {
        "mensaje": "Servicio finalizado correctamente",
        "id_asignacion": asignacion.id,
        "id_estado_asignacion": asignacion.id_estado_asignacion
    }