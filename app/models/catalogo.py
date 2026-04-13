from sqlalchemy import Column, Integer, String
from app.database import Base


class Prioridad(Base):
    __tablename__ = "prioridad"
    __table_args__ = {"schema": "catalogo"}

    codigo = Column(Integer, primary_key=True, index=True)
    nivel = Column(String(100), nullable=False)


class CategoriaProblema(Base):
    __tablename__ = "categoria_problema"
    __table_args__ = {"schema": "catalogo"}

    codigo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)


class EstadoIncidente(Base):
    __tablename__ = "estado_incidente"
    __table_args__ = {"schema": "catalogo"}

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)


class TipoEvidencia(Base):
    __tablename__ = "tipo_evidencia"
    __table_args__ = {"schema": "catalogo"}

    codigo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)


class EstadoAsignacion(Base):
    __tablename__ = "estado_asignacion"
    __table_args__ = {"schema": "catalogo"}

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)