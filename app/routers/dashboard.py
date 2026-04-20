from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.operaciones import Incidente, Asignacion
from app.models.talleres import Taller, Tecnico
from app.models.seguridad import Usuario

router  = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/admin-plataforma")
def dashboard_admin(db: Session = Depends(get_db)):
    """Dashboard para Admin Plataforma"""
    total_incidentes = db.query(Incidente).count()
    pendientes = db.query(Incidente).filter(
        Incidente.id_estado_incidente == 1).count()
    en_proceso = db.query(Incidente).filter(
        Incidente.id_estado_incidente == 2).count()
    atendidos = db.query(Incidente).filter(
        Incidente.id_estado_incidente == 3).count()
    total_talleres = db.query(Taller).filter(Taller.activo == True).count()
    tecnicos_disponibles = db.query(Tecnico).filter(
        Tecnico.disponibilidad == True).count()
    total_usuarios = db.query(Usuario).count()

    # Últimos incidentes
    ultimos = db.query(Incidente).order_by(
        Incidente.fecha_reporte.desc()).limit(10).all()

    return {
        "stats": {
            "total_incidentes": total_incidentes,
            "pendientes": pendientes,
            "en_proceso": en_proceso,
            "atendidos": atendidos,
            "total_talleres": total_talleres,
            "tecnicos_disponibles": tecnicos_disponibles,
            "total_usuarios": total_usuarios
        },
        "ultimos_incidentes": [{
            "codigo": i.codigo,
            "descripcion": i.descripcion,
            "id_categoria": i.id_categoria_problema,
            "id_prioridad": i.id_prioridad,
            "id_estado": i.id_estado_incidente,
            "fecha_reporte": i.fecha_reporte,
            "latitud": float(i.latitud),
            "longitud": float(i.longitud)
        } for i in ultimos]
    }

@router.get("/admin-taller/{id_taller}")
def dashboard_taller(id_taller: int, db: Session = Depends(get_db)):
    """CU-16: Dashboard para Admin Taller"""
    asignaciones = db.query(Asignacion).filter(
        Asignacion.id_taller == id_taller).all()

    ids_incidentes = [a.id_incidente for a in asignaciones]

    total = len(ids_incidentes)
    pendientes = db.query(Asignacion).filter(
        Asignacion.id_taller == id_taller,
        Asignacion.id_estado_asignacion == 1).count()
    aceptadas = db.query(Asignacion).filter(
        Asignacion.id_taller == id_taller,
        Asignacion.id_estado_asignacion == 2).count()
    completadas = db.query(Asignacion).filter(
        Asignacion.id_taller == id_taller,
        Asignacion.id_estado_asignacion == 5).count()

    tecnicos = db.query(Tecnico).filter(
        Tecnico.id_taller == id_taller).all()
    disponibles = sum(1 for t in tecnicos if t.disponibilidad)

    # Solicitudes pendientes con detalle
    asig_pendientes = db.query(Asignacion).filter(
        Asignacion.id_taller == id_taller,
        Asignacion.id_estado_asignacion == 1
    ).order_by(Asignacion.fecha_asignacion.desc()).limit(20).all()

    solicitudes = []
    for a in asig_pendientes:
        inc = db.query(Incidente).filter(
            Incidente.codigo == a.id_incidente).first()
        if inc:
            solicitudes.append({
                "id_asignacion": a.id,
                "id_incidente": inc.codigo,
                "descripcion": inc.descripcion,
                "id_categoria": inc.id_categoria_problema,
                "id_prioridad": inc.id_prioridad,
                "latitud": float(inc.latitud),
                "longitud": float(inc.longitud),
                "fecha": inc.fecha_reporte,
                "id_estado_asignacion": a.id_estado_asignacion
            })

    return {
        "stats": {
            "total_solicitudes": total,
            "pendientes": pendientes,
            "aceptadas": aceptadas,
            "completadas": completadas,
            "total_tecnicos": len(tecnicos),
            "tecnicos_disponibles": disponibles
        },
        "solicitudes_pendientes": solicitudes
    }