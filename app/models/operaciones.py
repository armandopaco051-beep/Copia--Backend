from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, Numeric, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Incidente(Base):
    __tablename__ = "incidente"
    __table_args__ = {"schema": "operaciones"}

    codigo = Column(Integer, primary_key=True, index=True)
    descripcion = Column(Text, nullable=False)
    latitud = Column(Numeric(10, 7), nullable=False)
    longitud = Column(Numeric(10, 7), nullable=False)
    fecha_reporte = Column(TIMESTAMP, nullable=False)
    fecha_cierre = Column(TIMESTAMP, nullable=True)
    id_prioridad = Column(Integer, ForeignKey("catalogo.prioridad.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    id_categoria_problema = Column(Integer, ForeignKey("catalogo.categoria_problema.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    id_estado_incidente = Column(Integer, ForeignKey("catalogo.estado_incidente.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    id_vehiculo = Column(Integer, ForeignKey("clientes.vehiculo.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    codigo_usuario = Column(String(100), ForeignKey("seguridad.usuario.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    historial = relationship("HistorialEstado", back_populates="incidente")
    asignaciones = relationship("Asignacion", back_populates="incidente")


class HistorialEstado(Base):
    __tablename__ = "historial_estado"
    __table_args__ = {"schema": "operaciones"}

    codigo = Column(Integer, primary_key=True, index=True)
    fecha_cambio = Column(TIMESTAMP, nullable=False)
    id_incidente = Column(Integer, ForeignKey("operaciones.incidente.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    incidente = relationship("Incidente", back_populates="historial")


class Asignacion(Base):
    __tablename__ = "asignacion"
    __table_args__ = {"schema": "operaciones"}

    id = Column(Integer, primary_key=True, index=True)
    fecha_asignacion = Column(TIMESTAMP, nullable=False)
    fecha_aceptacion = Column(TIMESTAMP, nullable=False)
    tiempo = Column(String(50), nullable=False)
    observacion = Column(Text, nullable=True)
    id_incidente = Column(Integer, ForeignKey("operaciones.incidente.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    id_tecnico = Column(Integer, ForeignKey("talleres.tecnico.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    id_taller = Column(Integer, ForeignKey("talleres.taller.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    id_estado_asignacion = Column(Integer, ForeignKey("catalogo.estado_asignacion.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    incidente = relationship("Incidente", back_populates="asignaciones")