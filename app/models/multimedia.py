from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func 
from app.database import Base


class Evidencia(Base): 
    __tablename__ = "evidencia"
    __table_args_ = {"schema": "multimedia"}

    codigo  = Column(Integer, primary_key=True, index=True)
    fecha_subida = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    transcripcion = Column(String, nullable=True)
    url_archivo = Column(String(500), nullable=False)
    id_tipo_evidencia = Column(Integer, ForeignKey("catalogo.tipo_evidencia.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    id_incidente  = Column(Integer, ForeignKey("operaciones.incidente.codigo", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    