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
from app.schemas.asignacion import ResponderAsignacion, AsignacionCreate
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

@router.get("/candidatos/{id_incidente}")
def obtener_candidatos(id_incidente: int ,  db: Session = Depends(get_db)): 
    #Cu17 motor de asignacion inteligente retorna lista de tecnicos candidatos
    incidente = db.query(Incidente).filter(Incidente.codigo == id_incidente).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    talleres_activos = db.query(Taller).filter(Taller.estado == "activo").all()
    candidatos=[] 
    for taller in talleres_activos: 
        #tecnicos disponible
        tecnicos_disponible = db.query(Tecnico).filter(Tecnico.id_taller == taller.codigo, Tecnico.disponibilidad == True).all()
        if not tecnicos_disponible: 
            continue 
        #calcular las distancia 
        distancia  = calcular_distancia(
            incidente.latitud, incidente.longitud, taller.latitud, taller.longitud 
            if hasattr(taller,'latitud')else taller.latitud,taller.longitud
        )
        #Score menor distancia = mayor Score 
        #prioridad alta de suma de puntos
        score_distancia = max(0,100 - distancia * 5 )
        bonus_prioridad = 20 if incidente.prioridad == 1 else 0
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

    db.commit()
    db.refresh(nueva)

    return {
        "id_asignacion": nueva.id,
        "mensaje": "Técnico asignado correctamente",
        "estado": "pendiente"
    }


@router.put("/{id_asignacion}/responder")
def responder_asignacion(
    id_asignacion: int,
    datos: ResponderAsignacion,
    request: Request,
    db: Session = Depends(get_db)
):
    """CU-18: Aceptar o rechazar asignación"""
    asignacion = db.query(Asignacion).filter(
        Asignacion.id == id_asignacion).first()
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    if datos.aceptada:
        asignacion.id_estado_asignacion = 2  # aceptada
        asignacion.observacion = datos.observacion
    else:
        asignacion.id_estado_asignacion = 3  # rechazada
        # Liberar técnico
        tecnico = db.query(Tecnico).filter(
            Tecnico.codigo == asignacion.id_tecnico).first()
        if tecnico:
            tecnico.disponibilidad = True
        # Volver incidente a pendiente
        incidente = db.query(Incidente).filter(
            Incidente.codigo == asignacion.id_incidente).first()
        if incidente:
            incidente.id_estado_incidente = 1

    db.commit()

    return {
        "mensaje": "Aceptada" if datos.aceptada else "Rechazada",
        "id_estado": asignacion.id_estado_asignacion
    }


@router.get("/taller/{id_taller}")
def asignaciones_del_taller(
    id_taller: int,
    db: Session = Depends(get_db)
):
    """Lista todas las asignaciones de un taller"""
    asignaciones = db.query(Asignacion).filter(
        Asignacion.id_taller == id_taller
    ).order_by(Asignacion.fecha_asignacion.desc()).all()

    resultado = []
    for a in asignaciones:
        inc = db.query(Incidente).filter(
            Incidente.codigo == a.id_incidente).first()
        resultado.append({
            "id": a.id,
            "id_incidente": a.id_incidente,
            "id_tecnico": a.id_tecnico,
            "id_estado_asignacion": a.id_estado_asignacion,
            "fecha_asignacion": a.fecha_asignacion,
            "tiempo": a.tiempo,
            "observacion": a.observacion,
            "incidente": {
                "descripcion": inc.descripcion if inc else "",
                "latitud": float(inc.latitud) if inc else 0,
                "longitud": float(inc.longitud) if inc else 0,
                "id_categoria": inc.id_categoria_problema if inc else 0,
                "id_prioridad": inc.id_prioridad if inc else 0,
            } if inc else {}
        })
    return resultado